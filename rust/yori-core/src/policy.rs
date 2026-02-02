//! Policy evaluation engine using GRID Core's embedded OPA
//!
//! This module wraps grid-opa to provide policy evaluation for LLM requests.
//! It's 4-10x faster than HTTP-based OPA calls.

use grid_opa::engine::OPAEngine;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;

/// Policy evaluation engine for LLM governance
///
/// This wraps GRID Core's embedded OPA engine for high-performance policy evaluation
/// on resource-constrained home router hardware.
///
/// # Example (Python)
///
/// ```python
/// import yori_core
///
/// engine = yori_core.PolicyEngine("/usr/local/etc/yori/policies")
/// engine.load_policies()
///
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
    inner: Mutex<OPAEngine>,
    policy_dir: PathBuf,
    loaded_policies: Mutex<Vec<String>>,
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
        let engine = OPAEngine::new().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to create OPA engine: {}",
                e
            ))
        })?;

        Ok(PolicyEngine {
            inner: Mutex::new(engine),
            policy_dir: PathBuf::from(policy_dir),
            loaded_policies: Mutex::new(Vec::new()),
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
    fn evaluate(&self, py: Python, input_data: Bound<'_, PyDict>) -> PyResult<PyObject> {
        // Convert Python dict to JSON for OPA
        let json_module = py.import_bound("json")?;
        let json_str: String = json_module
            .call_method1("dumps", (input_data,))?
            .extract()?;

        let engine = self.inner.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        // Evaluate against the authorization policy
        let eval_result = engine.evaluate("data.authorization.allow", &json_str);

        let result = PyDict::new_bound(py);

        match eval_result {
            Ok(value) => {
                // Parse the result - OPA returns a Value
                let allow = value.as_bool().unwrap_or(false);
                result.set_item("allow", allow)?;
                result.set_item("policy", "authorization")?;
                result.set_item(
                    "reason",
                    if allow {
                        "Policy evaluation passed"
                    } else {
                        "Policy evaluation denied"
                    },
                )?;
            }
            Err(e) => {
                // If evaluation fails, deny by default
                result.set_item("allow", false)?;
                result.set_item("policy", "error")?;
                result.set_item("reason", format!("Policy evaluation error: {}", e))?;
            }
        }

        Ok(result.into())
    }

    /// Load or reload policy files from disk
    ///
    /// # Returns
    ///
    /// Number of policies loaded
    fn load_policies(&self) -> PyResult<usize> {
        let mut engine = self.inner.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        let mut loaded = self.loaded_policies.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        // Clear existing policies
        engine.clear_policies();
        loaded.clear();

        // Check if directory exists
        if !self.policy_dir.exists() {
            return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
                format!("Policy directory not found: {:?}", self.policy_dir),
            ));
        }

        // Load all .rego files
        let entries = fs::read_dir(&self.policy_dir).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                "Failed to read policy directory: {}",
                e
            ))
        })?;

        let mut count = 0;
        for entry in entries {
            let entry = entry.map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                    "Failed to read directory entry: {}",
                    e
                ))
            })?;

            let path = entry.path();
            if path.extension().map_or(false, |ext| ext == "rego") {
                let policy_name = path
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("unknown")
                    .to_string();

                let policy_code = fs::read_to_string(&path).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
                        "Failed to read policy file {:?}: {}",
                        path, e
                    ))
                })?;

                engine
                    .load_policy(policy_name.clone(), policy_code)
                    .map_err(|e| {
                        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                            "Failed to load policy '{}': {}",
                            policy_name, e
                        ))
                    })?;

                loaded.push(policy_name);
                count += 1;
            }
        }

        Ok(count)
    }

    /// Load a single policy from a string
    ///
    /// # Arguments
    ///
    /// * `name` - Policy name
    /// * `code` - Rego policy code
    fn load_policy_string(&self, name: String, code: String) -> PyResult<()> {
        let mut engine = self.inner.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        let mut loaded = self.loaded_policies.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        engine.load_policy(name.clone(), code).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to load policy '{}': {}",
                name, e
            ))
        })?;

        if !loaded.contains(&name) {
            loaded.push(name);
        }

        Ok(())
    }

    /// Get list of loaded policy names
    ///
    /// # Returns
    ///
    /// List of policy names (without .rego extension)
    fn list_policies(&self, py: Python) -> PyResult<PyObject> {
        let loaded = self.loaded_policies.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        let policies = PyList::new_bound(py, loaded.iter());
        Ok(policies.into())
    }

    /// Clear all loaded policies
    fn clear_policies(&self) -> PyResult<()> {
        let mut engine = self.inner.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        let mut loaded = self.loaded_policies.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;

        engine.clear_policies();
        loaded.clear();

        Ok(())
    }

    /// Get the policy directory path
    fn policy_dir(&self) -> PyResult<String> {
        Ok(self.policy_dir.to_string_lossy().to_string())
    }

    /// Get the number of loaded policies
    fn policy_count(&self) -> PyResult<usize> {
        let loaded = self.loaded_policies.lock().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Lock error: {}", e))
        })?;
        Ok(loaded.len())
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
