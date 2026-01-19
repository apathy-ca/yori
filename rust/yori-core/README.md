# yori-core

**High-performance Rust components for YORI home LLM gateway**

This library provides the core functionality for YORI, leveraging battle-tested components from [SARK](https://github.com/apathy-ca/sark) (enterprise LLM governance) adapted for resource-constrained home router hardware.

## Architecture

```
Python (FastAPI) ─── PyO3 bindings ───► yori-core (Rust)
                                            │
                                            ├─► sark-opa (policy engine)
                                            ├─► sark-cache (in-memory cache)
                                            └─► HTTP proxy logic
```

## Features

- **Policy Evaluation**: Embedded OPA engine (4-10x faster than HTTP-based OPA)
- **Caching**: Lock-free in-memory cache (eliminates need for Redis)
- **Proxy**: Transparent HTTP/HTTPS proxy for LLM traffic interception
- **FreeBSD**: Cross-compiled for OPNsense routers (x86_64-unknown-freebsd)

## Usage from Python

### Installation

```bash
# Install from wheel (recommended)
pip install yori-core

# Or build from source
cd rust/yori-core
maturin develop --release
```

### Policy Evaluation

```python
import yori_core

# Initialize policy engine with directory of .rego files
engine = yori_core.PolicyEngine("/usr/local/etc/yori/policies")

# Evaluate a request
result = engine.evaluate({
    "user": "alice",
    "endpoint": "api.openai.com",
    "time": "20:00",
    "method": "POST",
    "path": "/v1/chat/completions"
})

if result["allow"]:
    # Request is allowed by policy
    print(f"Allowed by policy: {result['policy']}")
else:
    # Request blocked
    print(f"Blocked: {result['reason']}")

# Policy modes: observe (log only), advisory (log + alert), enforce (block)
print(f"Mode: {result['mode']}")
```

### Caching

```python
import yori_core

# Create cache (max 10k entries, 1 hour TTL)
cache = yori_core.Cache(max_entries=10000, ttl_seconds=3600)

# Cache policy evaluation results to avoid re-evaluation
cache_key = f"policy:{user}:{endpoint}:{time_window}"
cached_result = cache.get(cache_key)

if cached_result is None:
    # Cache miss - evaluate policy
    result = engine.evaluate(request_data)
    cache.set(cache_key, result)
else:
    # Cache hit - use cached decision
    result = cached_result

# Cache statistics
stats = cache.stats()
print(f"Hit rate: {stats['hit_rate']:.1f}%")
print(f"Entries: {stats['entries']}")
```

### API Reference

#### PolicyEngine

```python
class PolicyEngine:
    """OPA policy evaluation engine"""

    def __init__(self, policy_dir: str) -> None:
        """
        Create a new policy engine.

        Args:
            policy_dir: Path to directory containing .rego policy files
        """

    def evaluate(self, input_data: dict) -> dict:
        """
        Evaluate input against loaded policies.

        Args:
            input_data: Request context (user, endpoint, time, etc.)

        Returns:
            dict with keys:
                - allow (bool): Whether request is allowed
                - policy (str): Name of policy that made decision
                - reason (str): Human-readable explanation
                - mode (str): Policy mode (observe, advisory, enforce)
        """

    def load_policies(self) -> int:
        """
        Load or reload policy files from disk.

        Returns:
            Number of policies loaded
        """

    def list_policies(self) -> list[str]:
        """
        Get list of loaded policy names.

        Returns:
            List of policy names (without .rego extension)
        """

    def test_policy(self, policy_name: str, input_data: dict) -> dict:
        """
        Test a specific policy (dry run, no side effects).

        Args:
            policy_name: Name of policy to test
            input_data: Sample input data

        Returns:
            Evaluation result (same format as evaluate())
        """
```

#### Cache

```python
class Cache:
    """High-performance in-memory cache"""

    def __init__(self, max_entries: int = 10000, ttl_seconds: int = 3600) -> None:
        """
        Create a new cache instance.

        Args:
            max_entries: Maximum number of entries (default: 10000)
            ttl_seconds: Time-to-live in seconds (default: 3600)
        """

    def set(self, key: str, value: Any) -> bool:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to store (any picklable object)

        Returns:
            True if stored successfully
        """

    def get(self, key: str) -> Any | None:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """

    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""

    def clear(self) -> int:
        """Clear all entries. Returns number of entries removed."""

    def contains(self, key: str) -> bool:
        """Check if key exists and is not expired."""

    def stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            dict with keys:
                - entries (int): Current number of entries
                - hits (int): Number of cache hits
                - misses (int): Number of cache misses
                - hit_rate (float): Hit rate percentage (0-100)
        """

    def set_ttl(self, key: str, ttl_seconds: int) -> bool:
        """Update TTL for a specific key."""
```

## Building

### Prerequisites

- Rust 1.92+ (`rustup install 1.92`)
- Python 3.11+ with pip
- FreeBSD target: `rustup target add x86_64-unknown-freebsd`
- SARK repository cloned as sibling: `git clone https://github.com/apathy-ca/sark ../sark`

### Development Build

```bash
# Install build dependencies (Linux)
sudo apt-get install build-essential pkg-config libssl-dev

# Build and test
cargo build --workspace
cargo test --workspace

# Build for FreeBSD
./scripts/build-freebsd.sh --release
```

### Release Build

```bash
# Build optimized binary for FreeBSD
cargo build --release --target x86_64-unknown-freebsd

# Check binary size (target: <10MB)
ls -lh target/x86_64-unknown-freebsd/release/libyori_core.so
```

## Performance Targets

- **Build Time**: <3 minutes for FreeBSD release build
- **Binary Size**: <10MB (stripped, release mode)
- **Memory**: <100MB RSS for Rust components
- **Policy Evaluation**: <5ms per request (p95 latency)
- **Test Coverage**: >80% of Rust code

## Testing

```bash
# Run all tests
cargo test --workspace --verbose

# Test with coverage
cargo install cargo-tarpaulin
cargo tarpaulin --workspace --out Html

# Test PyO3 import (after building)
python3 -c "import yori_core; print(yori_core.__version__)"
```

## Deployment

### OPNsense Router

```bash
# Copy binary to router
scp target/x86_64-unknown-freebsd/release/libyori_core.so \
    root@router:/usr/local/lib/python3.11/site-packages/

# Test import on FreeBSD
ssh root@router "python3.11 -c 'import yori_core; print(yori_core.__version__)'"
```

### Python Package

```bash
# Build wheel with maturin
pip install maturin
maturin build --release --target x86_64-unknown-freebsd

# Install wheel
pip install target/wheels/yori_core-*.whl
```

## Interface Contract

This module is consumed by:

1. **python-proxy** (Worker 2): FastAPI proxy server
   - Uses `PolicyEngine.evaluate()` for request authorization
   - Uses `Cache` for policy result caching

2. **policy-engine** (Worker 5): Policy management
   - Uses `PolicyEngine.load_policies()` for policy reloading
   - Uses `PolicyEngine.test_policy()` for policy validation

## License

MIT License - see [LICENSE](../../LICENSE) file for details.

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development guidelines.
