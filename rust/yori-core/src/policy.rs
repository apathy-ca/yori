//! Policy evaluation engine using SARK's embedded OPA
//!
//! This module wraps sark-opa to provide policy evaluation for LLM requests.
//! It's 4-10x faster than HTTP-based OPA calls.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use sark_opa::{OPAEngine, Value};
use std::path::PathBuf;
use std::sync::Arc;

/// Compatibility struct to match old API expectations
struct PolicyResult {
    allow: bool,
    policy: String,
    reason: String,
    mode: String,
    metadata: Option<serde_json::Value>,
}

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
    engine: Arc<std::sync::Mutex<OPAEngine>>,
    policy_dir: PathBuf,
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
        let engine = OPAEngine::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create OPA engine: {}", e)))?;

        Ok(PolicyEngine {
            engine: Arc::new(std::sync::Mutex::new(engine)),
            policy_dir: PathBuf::from(policy_dir),
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
        // Convert Python dict to regorus Value using pythonize
        let input_value: Value = pythonize::depythonize_bound(input_data.as_any().clone())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid input data: {}", e)))?;

        // Evaluate using sark-opa engine (stub for now - returns default allow)
        let result = self.evaluate_internal(&input_value)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Policy evaluation failed: {}", e)))?;

        // Convert result back to Python dict
        let result_dict = PyDict::new_bound(py);
        result_dict.set_item("allow", result.allow)?;
        result_dict.set_item("policy", result.policy)?;
        result_dict.set_item("reason", result.reason)?;
        result_dict.set_item("mode", result.mode)?;

        if let Some(metadata) = result.metadata {
            let metadata_str = serde_json::to_string(&metadata).unwrap();
            let metadata_py = py.import_bound("json")?.getattr("loads")?.call1((metadata_str,))?;
            result_dict.set_item("metadata", metadata_py)?;
        }

        Ok(result_dict.into())
    }

    /// Load or reload policy files from disk
    ///
    /// # Returns
    ///
    /// Number of policies loaded
    fn load_policies(&self) -> PyResult<usize> {
        // Stub implementation - returns 0 for now
        // Real implementation would scan policy_dir for .rego files and load them
        Ok(0)
    }

    /// Get list of loaded policy names
    ///
    /// # Returns
    ///
    /// List of policy names (without .rego extension)
    fn list_policies(&self, py: Python) -> PyResult<PyObject> {
        let engine = self.engine.lock().unwrap();
        let policy_names = engine.loaded_policies();

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
    fn test_policy(&self, py: Python, _policy_name: String, input_data: Bound<'_, PyDict>) -> PyResult<PyObject> {
        // Test policy is the same as evaluate but we mark it as test mode
        let input_value: Value = pythonize::depythonize_bound(input_data.as_any().clone())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid input data: {}", e)))?;

        let result = self.evaluate_internal(&input_value)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Policy test failed: {}", e)))?;

        let result_dict = PyDict::new_bound(py);
        result_dict.set_item("allow", result.allow)?;
        result_dict.set_item("policy", result.policy)?;
        result_dict.set_item("reason", result.reason)?;
        result_dict.set_item("mode", "test")?;  // Mark as test mode

        Ok(result_dict.into())
    }
}

impl PolicyEngine {
    /// Internal evaluation logic
    fn evaluate_internal(&self, _input: &Value) -> Result<PolicyResult, String> {
        // For now, return a default "allow" result since no policies are loaded
        // In production, this would evaluate against loaded OPA policies
        Ok(PolicyResult {
            allow: true,
            policy: "default".to_string(),
            reason: "No policies loaded - observe mode".to_string(),
            mode: "observe".to_string(),
            metadata: None,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::Python;
    use pyo3::types::PyDict;

    #[test]
    fn test_policy_engine_creation() {
        let engine = PolicyEngine::new("/tmp/policies".to_string());
        assert!(engine.is_ok());
    }

    #[test]
    fn test_policy_engine_with_valid_path() {
        let engine = PolicyEngine::new("/usr/local/etc/yori/policies".to_string());
        assert!(engine.is_ok());
        let eng = engine.unwrap();
        assert_eq!(eng.policy_dir, std::path::PathBuf::from("/usr/local/etc/yori/policies"));
    }

    #[test]
    fn test_evaluate_returns_valid_dict() {
        Python::with_gil(|py| {
            let engine = PolicyEngine::new("/tmp/policies".to_string()).unwrap();
            let input_data = PyDict::new_bound(py);
            input_data.set_item("user", "alice").unwrap();
            input_data.set_item("endpoint", "api.openai.com").unwrap();

            let result = engine.evaluate(py, input_data).unwrap();
            let result_dict: &Bound<'_, PyDict> = result.downcast_bound(py).unwrap();

            assert!(result_dict.contains("allow").unwrap());
            assert!(result_dict.contains("policy").unwrap());
            assert!(result_dict.contains("reason").unwrap());
            assert!(result_dict.contains("mode").unwrap());
        });
    }

    #[test]
    fn test_evaluate_stub_allows_all() {
        Python::with_gil(|py| {
            let engine = PolicyEngine::new("/tmp/policies".to_string()).unwrap();
            let input_data = PyDict::new_bound(py);

            let result = engine.evaluate(py, input_data).unwrap();
            let result_dict: &Bound<'_, PyDict> = result.downcast_bound(py).unwrap();

            let allow: bool = result_dict.get_item("allow").unwrap().unwrap().extract().unwrap();
            assert!(allow); // Stub implementation allows all
        });
    }

    #[test]
    fn test_load_policies_returns_count() {
        let engine = PolicyEngine::new("/tmp/policies".to_string()).unwrap();
        let count = engine.load_policies().unwrap();
        assert_eq!(count, 0); // Stub returns 0
    }

    #[test]
    fn test_list_policies_returns_list() {
        Python::with_gil(|py| {
            let engine = PolicyEngine::new("/tmp/policies".to_string()).unwrap();
            let policies = engine.list_policies(py).unwrap();
            let list: &Bound<'_, pyo3::types::PyList> = policies.downcast_bound(py).unwrap();
            assert_eq!(list.len(), 0); // Stub returns empty list
        });
    }
}
