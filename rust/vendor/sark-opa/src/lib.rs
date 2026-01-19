//! SARK OPA - Embedded Open Policy Agent for YORI
//!
//! This is a minimal vendored implementation of sark-opa for the YORI project.
//! It wraps the opa-wasm crate to provide policy evaluation capabilities.

use anyhow::{Context, Result};
use opa_wasm::{Policy, Runtime};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::Path;
use std::sync::Arc;
use tokio::fs;

/// Policy evaluation result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyResult {
    /// Whether the request is allowed
    pub allow: bool,
    /// Policy name that made the decision
    pub policy: String,
    /// Human-readable reason for the decision
    pub reason: String,
    /// Policy mode (observe, advisory, enforce)
    pub mode: String,
    /// Optional metadata from policy
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Value>,
}

/// OPA policy engine that can evaluate Rego policies compiled to WebAssembly
pub struct OpaEngine {
    policies: Vec<LoadedPolicy>,
}

struct LoadedPolicy {
    name: String,
    runtime: Runtime,
}

impl OpaEngine {
    /// Create a new OPA engine (empty, no policies loaded)
    pub fn new() -> Self {
        OpaEngine {
            policies: Vec::new(),
        }
    }

    /// Load a policy from a .wasm file
    ///
    /// Note: Rego policies must be compiled to WebAssembly first using:
    /// `opa build -t wasm -e <entrypoint> policy.rego`
    pub async fn load_policy_from_wasm(&mut self, name: String, wasm_path: &Path) -> Result<()> {
        let wasm_bytes = fs::read(wasm_path)
            .await
            .with_context(|| format!("Failed to read WASM policy: {}", wasm_path.display()))?;

        let policy = Policy::from_wasm(&wasm_bytes)
            .with_context(|| format!("Failed to parse WASM policy: {}", name))?;

        let runtime = Runtime::new(Arc::new(policy));

        self.policies.push(LoadedPolicy { name, runtime });

        tracing::info!("Loaded policy: {}", self.policies.last().unwrap().name);
        Ok(())
    }

    /// Load a policy from raw Rego source (requires compilation step)
    ///
    /// For now, this is a placeholder. In production, you'd compile Rego to WASM
    /// using the OPA CLI or a Rego compiler.
    pub fn load_policy_from_rego(&mut self, _name: String, _rego_source: &str) -> Result<()> {
        anyhow::bail!("Rego compilation not yet implemented. Please compile to WASM first using: opa build -t wasm -e <entrypoint> policy.rego");
    }

    /// Evaluate input against all loaded policies
    ///
    /// Returns the first policy that produces a decision (allow or deny).
    /// If no policies produce a decision, defaults to allow in observe mode.
    pub fn evaluate(&self, input: &Value) -> Result<PolicyResult> {
        // If no policies loaded, default to allow (observe mode)
        if self.policies.is_empty() {
            return Ok(PolicyResult {
                allow: true,
                policy: "default".to_string(),
                reason: "No policies loaded - observe mode".to_string(),
                mode: "observe".to_string(),
                metadata: None,
            });
        }

        // Evaluate each policy
        for loaded in &self.policies {
            match loaded.runtime.evaluate(input) {
                Ok(result) => {
                    // Try to extract decision from result
                    if let Some(allow) = result.get("allow").and_then(|v| v.as_bool()) {
                        let reason = result
                            .get("reason")
                            .and_then(|v| v.as_str())
                            .unwrap_or("Policy decision")
                            .to_string();

                        let mode = result
                            .get("mode")
                            .and_then(|v| v.as_str())
                            .unwrap_or("enforce")
                            .to_string();

                        return Ok(PolicyResult {
                            allow,
                            policy: loaded.name.clone(),
                            reason,
                            mode,
                            metadata: result.get("metadata").cloned(),
                        });
                    }
                }
                Err(e) => {
                    tracing::warn!("Policy evaluation error in {}: {}", loaded.name, e);
                    continue;
                }
            }
        }

        // Default to allow if no policy made a decision
        Ok(PolicyResult {
            allow: true,
            policy: "default".to_string(),
            reason: "No policy decision - defaulting to allow".to_string(),
            mode: "observe".to_string(),
            metadata: None,
        })
    }

    /// Get list of loaded policy names
    pub fn list_policies(&self) -> Vec<String> {
        self.policies.iter().map(|p| p.name.clone()).collect()
    }

    /// Get number of loaded policies
    pub fn policy_count(&self) -> usize {
        self.policies.len()
    }
}

impl Default for OpaEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_engine() {
        let engine = OpaEngine::new();
        assert_eq!(engine.policy_count(), 0);
    }

    #[test]
    fn test_evaluate_no_policies() {
        let engine = OpaEngine::new();
        let input = serde_json::json!({"user": "alice"});
        let result = engine.evaluate(&input).unwrap();
        assert!(result.allow);
        assert_eq!(result.mode, "observe");
    }
}
