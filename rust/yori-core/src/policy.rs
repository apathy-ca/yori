//! Policy evaluation engine using SARK's embedded OPA
//!
//! This module wraps sark-opa to provide policy evaluation for LLM requests.
//! It's 4-10x faster than HTTP-based OPA calls.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::path::PathBuf;

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
    // TODO: Replace with actual sark-opa engine once integrated
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
        Ok(PolicyEngine {
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
    fn evaluate(&self, py: Python, _input_data: Bound<'_, PyDict>) -> PyResult<PyObject> {
        // TODO: Implement actual OPA evaluation with sark-opa
        // For now, return a stub that allows all requests (observe mode)

        let result = PyDict::new_bound(py);
        result.set_item("allow", true)?;
        result.set_item("policy", "stub_default")?;
        result.set_item("reason", "Stub policy engine - all requests allowed")?;
        result.set_item("mode", "observe")?;

        Ok(result.into())
    }

    /// Load or reload policy files from disk
    ///
    /// # Returns
    ///
    /// Number of policies loaded
    fn load_policies(&self) -> PyResult<usize> {
        // TODO: Implement policy loading from .rego files
        // This should scan policy_dir and load all .rego files into OPA
        Ok(0)
    }

    /// Get list of loaded policy names
    ///
    /// # Returns
    ///
    /// List of policy names (without .rego extension)
    fn list_policies(&self, py: Python) -> PyResult<PyObject> {
        // TODO: Return actual loaded policies
        let policies = PyList::empty_bound(py);
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
    fn test_policy(&self, py: Python, policy_name: String, _input_data: Bound<'_, PyDict>) -> PyResult<PyObject> {
        // TODO: Implement policy testing
        let result = PyDict::new_bound(py);
        result.set_item("allow", true)?;
        result.set_item("policy", policy_name)?;
        result.set_item("reason", "Test mode")?;

        Ok(result.into())
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
    fn test_policy_engine_with_relative_path() {
        let engine = PolicyEngine::new("./policies".to_string());
        assert!(engine.is_ok());
    }

    #[test]
    fn test_policy_engine_with_empty_path() {
        let engine = PolicyEngine::new("".to_string());
        assert!(engine.is_ok());
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
    fn test_evaluate_stub_returns_observe_mode() {
        Python::with_gil(|py| {
            let engine = PolicyEngine::new("/tmp/policies".to_string()).unwrap();
            let input_data = PyDict::new_bound(py);

            let result = engine.evaluate(py, input_data).unwrap();
            let result_dict: &Bound<'_, PyDict> = result.downcast_bound(py).unwrap();

            let mode: String = result_dict.get_item("mode").unwrap().unwrap().extract().unwrap();
            assert_eq!(mode, "observe");
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

    #[test]
    fn test_test_policy_returns_dict() {
        Python::with_gil(|py| {
            let engine = PolicyEngine::new("/tmp/policies".to_string()).unwrap();
            let input_data = PyDict::new_bound(py);
            let policy_name = "test_policy".to_string();

            let result = engine.test_policy(py, policy_name.clone(), input_data).unwrap();
            let result_dict: &Bound<'_, PyDict> = result.downcast_bound(py).unwrap();

            assert!(result_dict.contains("allow").unwrap());
            assert!(result_dict.contains("policy").unwrap());

            let returned_policy: String = result_dict.get_item("policy").unwrap().unwrap().extract().unwrap();
            assert_eq!(returned_policy, policy_name);
        });
    }

    #[test]
    fn test_policy_engine_multiple_instances() {
        let engine1 = PolicyEngine::new("/tmp/policies1".to_string()).unwrap();
        let engine2 = PolicyEngine::new("/tmp/policies2".to_string()).unwrap();

        assert_eq!(engine1.policy_dir, std::path::PathBuf::from("/tmp/policies1"));
        assert_eq!(engine2.policy_dir, std::path::PathBuf::from("/tmp/policies2"));
    }

    #[test]
    fn test_evaluate_with_complex_input() {
        Python::with_gil(|py| {
            let engine = PolicyEngine::new("/tmp/policies".to_string()).unwrap();
            let input_data = PyDict::new_bound(py);

            // Add multiple fields
            input_data.set_item("user", "alice").unwrap();
            input_data.set_item("endpoint", "api.openai.com").unwrap();
            input_data.set_item("method", "POST").unwrap();
            input_data.set_item("path", "/v1/chat/completions").unwrap();
            input_data.set_item("time", "2024-01-15T14:30:00Z").unwrap();

            let result = engine.evaluate(py, input_data).unwrap();
            assert!(result.is_truthy(py).unwrap());
        });
    }
}
