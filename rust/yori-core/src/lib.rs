//! YORI Core - Rust components for home LLM governance
//!
//! This library provides high-performance components for the YORI home gateway,
//! leveraging battle-tested code from SARK (enterprise LLM governance).
//!
//! # Architecture
//!
//! ```text
//! Python (FastAPI) ─── PyO3 bindings ───► yori-core (Rust)
//!                                             │
//!                                             ├─► sark-opa (policy engine)
//!                                             ├─► sark-cache (in-memory cache)
//!                                             └─► HTTP proxy logic
//! ```
//!
//! # Features
//!
//! - **Policy Evaluation**: Embedded OPA engine (4-10x faster than HTTP)
//! - **Caching**: Lock-free in-memory cache (no Redis needed)
//! - **Proxy**: Transparent HTTP/HTTPS proxy for LLM traffic
//!
//! # Usage from Python
//!
//! ```python
//! import yori_core
//!
//! # Initialize policy engine
//! policy = yori_core.PolicyEngine("/etc/yori/policies")
//!
//! # Evaluate a request
//! result = policy.evaluate({
//!     "user": "alice",
//!     "endpoint": "api.openai.com",
//!     "time": "20:00"
//! })
//!
//! if result["allow"]:
//!     # Forward request
//!     pass
//! else:
//!     # Block with reason
//!     print(f"Blocked: {result['reason']}")
//! ```

use pyo3::prelude::*;

mod audit;
mod cache;
mod policy;
mod proxy;

pub use audit::{AuditEvent, AuditEventType, AuditLogger, PolicyDecision};
pub use cache::Cache;
pub use policy::PolicyEngine;
pub use proxy::{ProxyConfig, ProxyMode, ProxyServer, RequestContext, ResponseContext};

/// Initialize the YORI core module for Python.
///
/// This function is called automatically when the module is imported from Python.
#[pymodule]
fn yori_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register PolicyEngine class
    m.add_class::<PolicyEngine>()?;

    // Register Cache class
    m.add_class::<Cache>()?;

    // Add version info
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add("__author__", "James Henry <jamesrahenry@henrynet.ca>")?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_module_initialization() {
        // Basic smoke test
        assert_eq!(env!("CARGO_PKG_NAME"), "yori-core");
    }
}
