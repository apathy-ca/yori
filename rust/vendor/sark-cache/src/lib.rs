//! SARK Cache - Lock-free in-memory cache for YORI
//!
//! This is a minimal vendored implementation of sark-cache for the YORI project.
//! It provides a simple TTL-based cache using DashMap for lock-free concurrent access.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::time;

/// Cache entry with TTL
#[derive(Debug, Clone)]
struct CacheEntry<V> {
    value: V,
    expires_at: Instant,
}

/// Lock-free in-memory cache with TTL support
pub struct Cache<K, V>
where
    K: Eq + std::hash::Hash + Clone,
    V: Clone,
{
    map: Arc<DashMap<K, CacheEntry<V>>>,
    default_ttl: Duration,
}

impl<K, V> Cache<K, V>
where
    K: Eq + std::hash::Hash + Clone + Send + Sync + 'static,
    V: Clone + Send + Sync + 'static,
{
    /// Create a new cache with a default TTL
    pub fn new(default_ttl: Duration) -> Self {
        let cache = Cache {
            map: Arc::new(DashMap::new()),
            default_ttl,
        };

        // Start background cleanup task
        let map_clone = cache.map.clone();
        tokio::spawn(async move {
            let mut interval = time::interval(Duration::from_secs(60));
            loop {
                interval.tick().await;
                Self::cleanup_expired(&map_clone);
            }
        });

        cache
    }

    /// Insert a value with the default TTL
    pub fn insert(&self, key: K, value: V) {
        self.insert_with_ttl(key, value, self.default_ttl);
    }

    /// Insert a value with a custom TTL
    pub fn insert_with_ttl(&self, key: K, value: V, ttl: Duration) {
        let entry = CacheEntry {
            value,
            expires_at: Instant::now() + ttl,
        };
        self.map.insert(key, entry);
    }

    /// Get a value from the cache (if not expired)
    pub fn get(&self, key: &K) -> Option<V> {
        self.map.get(key).and_then(|entry| {
            if entry.expires_at > Instant::now() {
                Some(entry.value.clone())
            } else {
                // Entry expired, remove it
                drop(entry);
                self.map.remove(key);
                None
            }
        })
    }

    /// Remove a value from the cache
    pub fn remove(&self, key: &K) -> Option<V> {
        self.map.remove(key).map(|(_, entry)| entry.value)
    }

    /// Clear all entries from the cache
    pub fn clear(&self) {
        self.map.clear();
    }

    /// Get the number of entries in the cache (including expired)
    pub fn len(&self) -> usize {
        self.map.len()
    }

    /// Check if the cache is empty
    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }

    /// Remove all expired entries
    fn cleanup_expired(map: &DashMap<K, CacheEntry<V>>) {
        let now = Instant::now();
        map.retain(|_, entry| entry.expires_at > now);
        tracing::debug!("Cache cleanup completed, {} entries remain", map.len());
    }
}

impl<K, V> Clone for Cache<K, V>
where
    K: Eq + std::hash::Hash + Clone,
    V: Clone,
{
    fn clone(&self) -> Self {
        Cache {
            map: self.map.clone(),
            default_ttl: self.default_ttl,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_insert_get() {
        let cache = Cache::new(Duration::from_secs(10));
        cache.insert("key1", "value1");
        assert_eq!(cache.get(&"key1"), Some("value1"));
    }

    #[test]
    fn test_cache_expiration() {
        let cache = Cache::new(Duration::from_millis(10));
        cache.insert("key1", "value1");
        std::thread::sleep(Duration::from_millis(20));
        assert_eq!(cache.get(&"key1"), None);
    }

    #[test]
    fn test_cache_remove() {
        let cache = Cache::new(Duration::from_secs(10));
        cache.insert("key1", "value1");
        assert_eq!(cache.remove(&"key1"), Some("value1"));
        assert_eq!(cache.get(&"key1"), None);
    }
}
