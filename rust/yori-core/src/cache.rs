//! In-memory cache using GRID Core's lock-free cache implementation
//!
//! This module wraps grid-cache to provide fast, thread-safe caching
//! without requiring Redis on resource-constrained home routers.

use grid_cache::lru_ttl::LRUTTLCache;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// High-performance in-memory cache
///
/// This wraps GRID Core's lock-free cache implementation, eliminating the need
/// for external Redis/Valkey instances on home router hardware.
///
/// # Example (Python)
///
/// ```python
/// import yori_core
///
/// cache = yori_core.Cache(max_entries=10000, ttl_seconds=3600)
///
/// # Cache policy evaluation results
/// cache.set("policy:alice:openai", '{"allow": true, "reason": "approved"}')
///
/// # Retrieve cached result
/// result = cache.get("policy:alice:openai")
/// if result is not None:
///     # Use cached decision (avoids re-evaluation)
///     pass
/// ```
#[pyclass]
pub struct Cache {
    inner: LRUTTLCache,
}

#[pymethods]
impl Cache {
    /// Create a new cache instance
    ///
    /// # Arguments
    ///
    /// * `max_entries` - Maximum number of entries (default: 10000)
    /// * `ttl_seconds` - Time-to-live for entries in seconds (default: 3600)
    ///
    /// # Returns
    ///
    /// A new Cache instance
    #[new]
    #[pyo3(signature = (max_entries=10000, ttl_seconds=3600))]
    fn new(max_entries: usize, ttl_seconds: u64) -> PyResult<Self> {
        if max_entries == 0 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "max_entries must be greater than 0",
            ));
        }
        if ttl_seconds == 0 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "ttl_seconds must be greater than 0",
            ));
        }
        Ok(Cache {
            inner: LRUTTLCache::new(max_entries, ttl_seconds),
        })
    }

    /// Store a value in the cache
    ///
    /// # Arguments
    ///
    /// * `key` - Cache key (string)
    /// * `value` - Value to store (string - use JSON for complex objects)
    ///
    /// # Returns
    ///
    /// True if stored successfully
    fn set(&self, key: String, value: String) -> PyResult<bool> {
        match self.inner.set(key, value) {
            Ok(()) => Ok(true),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Cache set failed: {}", e),
            )),
        }
    }

    /// Retrieve a value from the cache
    ///
    /// # Arguments
    ///
    /// * `key` - Cache key (string)
    ///
    /// # Returns
    ///
    /// Cached value if found and not expired, None otherwise
    fn get(&self, _py: Python, key: String) -> PyResult<Option<String>> {
        Ok(self.inner.get(&key))
    }

    /// Delete a value from the cache
    ///
    /// # Arguments
    ///
    /// * `key` - Cache key (string)
    ///
    /// # Returns
    ///
    /// True if entry existed and was deleted
    fn delete(&self, key: String) -> PyResult<bool> {
        Ok(self.inner.delete(&key))
    }

    /// Clear all entries from the cache
    ///
    /// # Returns
    ///
    /// Number of entries removed
    fn clear(&self) -> PyResult<usize> {
        Ok(self.inner.clear())
    }

    /// Get cache statistics
    ///
    /// # Returns
    ///
    /// Dictionary with cache stats:
    /// - `entries` (int): Current number of entries
    /// - `max_size` (int): Maximum number of entries
    fn stats(&self, py: Python) -> PyResult<PyObject> {
        let stats = PyDict::new_bound(py);
        stats.set_item("entries", self.inner.len())?;
        stats.set_item("max_size", self.inner.max_size())?;

        Ok(stats.into())
    }

    /// Check if a key exists in the cache
    ///
    /// # Arguments
    ///
    /// * `key` - Cache key to check
    ///
    /// # Returns
    ///
    /// True if key exists and is not expired
    fn contains(&self, key: String) -> PyResult<bool> {
        Ok(self.inner.get(&key).is_some())
    }

    /// Get current number of entries
    fn len(&self) -> PyResult<usize> {
        Ok(self.inner.len())
    }

    /// Check if cache is empty
    fn is_empty(&self) -> PyResult<bool> {
        Ok(self.inner.len() == 0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_creation() {
        let cache = Cache::new(1000, 300);
        assert!(cache.is_ok());
    }

    #[test]
    fn test_cache_invalid_params() {
        let cache = Cache::new(0, 300);
        assert!(cache.is_err());

        let cache = Cache::new(1000, 0);
        assert!(cache.is_err());
    }
}
