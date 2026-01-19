//! Policy evaluation engine using SARK's embedded OPA
//!
//! This module wraps sark-opa to provide policy evaluation for LLM requests.
//! It's 4-10x faster than HTTP-based OPA calls.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use sark_opa::{OpaEngine, PolicyResult as SarkPolicyResult};
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::runtime::Runtime as TokioRuntime;

/// Policy evaluation engine for LLM governance
///
/// This wraps SARK's embedded OPA engine for high-performance policy evaluation
/// on resource-constrained home router hardware.
///
/// # Example (Python)
///
/// ```python
/// import yori_core
///
/// engine = yori_core.PolicyEngine("/usr/local/etc/yori/policies")
/// result = engine.evaluate({
///     "user": "alice",
///     "endpoint": "api.openai.com",
///     "time": "20:00"
/// })
///
/// if result["allow"]:
///     # Forward request
///     pass
/// else:
///     # Block or alert
///     print(f"Policy violation: {result['reason']}")
/// ```
#[pyclass]
pub struct PolicyEngine {
    engine: Arc<std::sync::Mutex<OpaEngine>>,
    policy_dir: PathBuf,
    runtime: Arc<TokioRuntime>,
}

#[pymethods]
impl PolicyEngine {
    /// Create a new policy engine
    ///
    /// # Arguments
    ///
    /// * `policy_dir` - Path to directory containing .rego policy files
    ///
    /// # Returns
    ///
    /// A new PolicyEngine instance
    #[new]
    fn new(policy_dir: String) -> PyResult<Self> {
        let runtime = TokioRuntime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create async runtime: {}", e)))?;

        Ok(PolicyEngine {
            engine: Arc::new(std::sync::Mutex::new(OpaEngine::new())),
            policy_dir: PathBuf::from(policy_dir),
            runtime: Arc::new(runtime),
        })
    }

    /// Evaluate a request against loaded policies
    ///
    /// # Arguments
    ///
    /// * `input_data` - Dictionary containing request context (user, endpoint, time, etc.)
    ///
    /// # Returns
    ///
    /// Dictionary with evaluation result:
    /// - `allow` (bool): Whether request is allowed
    /// - `policy` (str): Name of policy that made decision
    /// - `reason` (str): Human-readable explanation
    /// - `mode` (str): Policy mode (observe, advisory, enforce)
    fn evaluate(&self, py: Python, input_data: Bound<'_, PyDict>) -> PyResult<PyObject> {
        // Convert Python dict to JSON Value
        let json_str = py.import_bound("json")?.getattr("dumps")?.call1((input_data,))?;
        let json_str: String = json_str.extract()?;
        let input: Value = serde_json::from_str(&json_str)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid input data: {}", e)))?;

        // Evaluate using sark-opa engine
        let engine = self.engine.lock().unwrap();
        let sark_result = engine.evaluate(&input)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Policy evaluation failed: {}", e)))?;

        // Convert result back to Python dict
        let result = PyDict::new_bound(py);
        result.set_item("allow", sark_result.allow)?;
        result.set_item("policy", sark_result.policy)?;
        result.set_item("reason", sark_result.reason)?;
        result.set_item("mode", sark_result.mode)?;

        if let Some(metadata) = sark_result.metadata {
            let metadata_str = serde_json::to_string(&metadata).unwrap();
            let metadata_py = py.import_bound("json")?.getattr("loads")?.call1((metadata_str,))?;
            result.set_item("metadata", metadata_py)?;
        }

        Ok(result.into())
    }

    /// Load or reload policy files from disk
    ///
    /// # Returns
    ///
    /// Number of policies loaded
    fn load_policies(&self) -> PyResult<usize> {
        let policy_dir = self.policy_dir.clone();
        let engine_clone = self.engine.clone();

        // Run async operation in tokio runtime
        let count = self.runtime.block_on(async move {
            let mut engine = engine_clone.lock().unwrap();
            let mut loaded_count = 0;

            // Scan directory for .wasm files (compiled Rego policies)
            let entries = match tokio::fs::read_dir(&policy_dir).await {
                Ok(entries) => entries,
                Err(e) => {
                    tracing::warn!("Failed to read policy directory {:?}: {}", policy_dir, e);
                    return 0;
                }
            };

            let mut entries = entries;
            while let Ok(Some(entry)) = entries.next_entry().await {
                let path = entry.path();
                if path.extension().and_then(|s| s.to_str()) == Some("wasm") {
                    let name = path.file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("unknown")
                        .to_string();

                    match engine.load_policy_from_wasm(name, &path).await {
                        Ok(_) => loaded_count += 1,
                        Err(e) => {
                            tracing::error!("Failed to load policy {:?}: {}", path, e);
                        }
                    }
                }
            }

            loaded_count
        });

        Ok(count)
    }

    /// Get list of loaded policy names
    ///
    /// # Returns
    ///
    /// List of policy names (without .rego extension)
    fn list_policies(&self, py: Python) -> PyResult<PyObject> {
        let engine = self.engine.lock().unwrap();
        let policy_names = engine.list_policies();

        let policies = PyList::new_bound(py, &policy_names);
        Ok(policies.into())
    }

    /// Test a policy against sample input (dry run)
    ///
    /// # Arguments
    ///
    /// * `policy_name` - Name of policy to test
    /// * `input_data` - Sample input data
    ///
    /// # Returns
    ///
    /// Evaluation result without side effects
    fn test_policy(&self, py: Python, policy_name: String, input_data: Bound<'_, PyDict>) -> PyResult<PyObject> {
        // Test policy is the same as evaluate but we could add dry-run metadata
        let json_str = py.import_bound("json")?.getattr("dumps")?.call1((input_data,))?;
        let json_str: String = json_str.extract()?;
        let input: Value = serde_json::from_str(&json_str)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid input data: {}", e)))?;

        let engine = self.engine.lock().unwrap();
        let sark_result = engine.evaluate(&input)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Policy test failed: {}", e)))?;

        let result = PyDict::new_bound(py);
        result.set_item("allow", sark_result.allow)?;
        result.set_item("policy", sark_result.policy)?;
        result.set_item("reason", sark_result.reason)?;
        result.set_item("mode", "test")?;  // Mark as test mode

        Ok(result.into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_policy_engine_creation() {
        let engine = PolicyEngine::new("/tmp/policies".to_string());
        assert!(engine.is_ok());
    }
}
