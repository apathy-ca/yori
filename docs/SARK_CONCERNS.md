# SARK Integration Concerns and Findings

**Date:** 2026-02-01
**Context:** YORI v0.3.0 development, SARK dependency analysis
**Status:** Requires attention before YORI can leverage SARK's Rust components

---

## Executive Summary

YORI's Rust components (`yori-core`) contain **stub implementations** that do not actually use SARK's working code. This was initially acceptable for v0.2.0 development, but creates a false impression that SARK itself is incomplete.

**Key Finding:** SARK's Rust implementations are **fully functional**. YORI's wrappers simply don't call them.

---

## The Misunderstanding

### What YORI's Code Says

```rust
// yori-core/src/policy.rs
pub fn evaluate(&self, ...) -> PyResult<...> {
    // TODO: Replace with actual sark-opa evaluation
    // For now, return a stub that allows all requests
    result.insert("allow", true);
    result.insert("policy", "stub_default");
    Ok(result)
}
```

### What This Implies (Incorrectly)

The TODO comment suggests SARK integration is pending, which could be interpreted as SARK not being ready.

### The Reality

SARK has **complete, tested implementations**:

| SARK Component | Status | Lines | Tests |
|----------------|--------|-------|-------|
| `sark-opa/src/engine.rs` | ✅ Complete | 455 | 15 tests |
| `sark-cache/src/lru_ttl.rs` | ✅ Complete | 321 | 8 tests |
| PyO3 bindings | ✅ Complete | 200+ | Integration tested |

---

## SARK's Actual Implementation

### sark-opa (OPA Policy Engine)

**File:** `/home/exedev/sark/rust/sark-opa/src/engine.rs`

```rust
pub struct OPAEngine {
    engine: RegorusEngine,  // Real Regorus engine
    policies: HashMap<String, String>,
}

impl OPAEngine {
    pub fn new() -> Result<Self> {
        let engine = RegorusEngine::new();  // Actually creates engine
        Ok(Self { engine, policies: HashMap::new() })
    }

    pub fn load_policy(&mut self, name: String, rego: String) -> Result<()> {
        // Actually compiles and loads the policy
        self.engine.add_policy(name.clone(), rego.clone())?;
        self.policies.insert(name, rego);
        Ok(())
    }

    pub fn evaluate(&mut self, query: &str, input: Value) -> Result<Value> {
        // Actually evaluates against Regorus
        self.engine.set_input(input);
        let results = self.engine.eval_query(query.to_string(), false)?;
        // ... extracts and returns real result
    }
}
```

**Features:**
- Full Rego policy compilation via Regorus
- Policy caching and hot-reload
- Thread-safe evaluation
- Comprehensive error handling
- 15 unit tests covering edge cases

### sark-cache (LRU+TTL Cache)

**File:** `/home/exedev/sark/rust/sark-cache/src/lru_ttl.rs`

```rust
pub struct LRUTTLCache {
    map: DashMap<String, CacheEntry>,  // Real concurrent hashmap
    max_size: usize,
    default_ttl: Duration,
    start_time: Instant,
}

impl LRUTTLCache {
    pub fn get(&self, key: &str) -> Option<String> {
        let entry = self.map.get(key)?;
        if entry.is_expired() {
            self.map.remove(key);
            return None;
        }
        entry.touch(self.now());
        Some(entry.value.clone())  // Actually returns cached value
    }

    pub fn set(&self, key: String, value: String, ttl: Option<u64>) -> Result<()> {
        // Actually stores with TTL and LRU eviction
        if self.map.len() >= self.max_size {
            self.evict_lru()?;
        }
        self.map.insert(key, CacheEntry::new(value, expires_at, now));
        Ok(())
    }
}
```

**Features:**
- Lock-free concurrent access via DashMap
- TTL-based expiration
- LRU eviction when at capacity
- Periodic cleanup of expired entries
- Thread-safe for concurrent reads/writes
- 8 unit tests including concurrency tests

---

## What YORI Should Do

### Option 1: Direct SARK Usage (Simplest)

Replace YORI's stubs with actual SARK calls:

```rust
// yori-core/src/policy.rs - CURRENT (stub)
pub fn evaluate(&self, input: HashMap<String, PyObject>) -> PyResult<...> {
    // TODO: Replace with actual sark-opa evaluation
    result.insert("allow", true);  // Fake!
}

// yori-core/src/policy.rs - SHOULD BE
use sark_opa::engine::OPAEngine;

pub struct PolicyEngine {
    engine: OPAEngine,  // Use SARK's engine
}

impl PolicyEngine {
    pub fn evaluate(&mut self, input: HashMap<String, PyObject>) -> PyResult<...> {
        let input_value = convert_to_regorus(input)?;
        let result = self.engine.evaluate("data.yori.decision", input_value)?;
        convert_from_regorus(result)
    }
}
```

### Option 2: Shared Crate (Planned)

A new shared repository is being created to house these components:

```
github.com/apathy-ca/sark-rust-core/
├── sark-opa/      # Policy engine
├── sark-cache/    # Caching
└── README.md      # Usage for both SARK and YORI
```

Both SARK and YORI will depend on this shared crate.

---

## YORI Stub Locations

Files that need updating when integrating SARK:

| File | Current State | Action Needed |
|------|---------------|---------------|
| `rust/yori-core/src/policy.rs` | Stub returning "allow all" | Use `sark_opa::OPAEngine` |
| `rust/yori-core/src/cache.rs` | Stub returning `None` | Use `sark_cache::LRUTTLCache` |
| `rust/yori-core/src/proxy.rs` | Stub with `sleep(1)` | Implement actual HTTP proxy |

### Estimated Effort

| Task | Effort | Notes |
|------|--------|-------|
| Replace policy stub | 1-2 hours | Type conversion is the main work |
| Replace cache stub | 1 hour | Straightforward mapping |
| Test integration | 2-4 hours | Ensure Python bindings still work |
| **Total** | **4-7 hours** | Could be done in a day |

---

## Why This Matters

### For YORI Users

Currently, YORI's Rust "acceleration" provides **zero benefit**:
- Policy evaluation: Returns "allow all" (no actual evaluation)
- Caching: Doesn't cache anything (always returns None)
- Performance: Same as not having Rust at all

### For SARK

The stub pattern in YORI creates a **false narrative** that SARK's implementations are incomplete or unavailable. This is incorrect and potentially harmful to SARK's reputation.

### For the Ecosystem

Having two projects with duplicated but divergent Rust code is wasteful. A shared crate would:
- Reduce maintenance burden
- Ensure bug fixes benefit both projects
- Provide a clear integration path

---

## Recommendations

1. **Short-term:** Document this clearly (this file)
2. **Medium-term:** Create shared `sark-rust-core` repository
3. **Long-term:** YORI integrates shared crate, removes stubs

---

## Contact

For questions about SARK's Rust implementations:
- SARK repo: `/home/exedev/sark`
- Key files: `rust/sark-opa/src/engine.rs`, `rust/sark-cache/src/lru_ttl.rs`
- Documentation: `docs/RUST_PYO3_INTEGRATION.md`, `docs/STANDALONE_CRATES.md`

---

## Appendix: SARK Documentation Created

New documentation added to SARK to help downstream projects:

1. **[RUST_PYO3_INTEGRATION.md](../../../sark/docs/RUST_PYO3_INTEGRATION.md)** - How to build and use PyO3 bindings
2. **[EMBEDDED_DEPLOYMENT.md](../../../sark/docs/EMBEDDED_DEPLOYMENT.md)** - Deploying on resource-constrained systems
3. **[STANDALONE_CRATES.md](../../../sark/docs/STANDALONE_CRATES.md)** - Using sark-opa/sark-cache independently
4. **[CROSS_COMPILATION.md](../../../sark/docs/CROSS_COMPILATION.md)** - Building for FreeBSD, ARM, etc.

These guides were created specifically to help YORI (and other projects) integrate SARK's Rust components correctly.
