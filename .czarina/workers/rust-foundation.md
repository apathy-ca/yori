# Worker Identity: rust-foundation

**Role:** Code
**Agent:** Claude
**Branch:** cz1/feat/rust-foundation
**Phase:** 1
**Dependencies:** None

## Mission

Establish Rust workspace with SARK crate integration, PyO3 bindings, and FreeBSD cross-compilation pipeline. This worker creates the foundation for all Rust-based functionality.

## 🚀 YOUR FIRST ACTION

Create repository structure at `/home/jhenry/Source/yori` with Cargo workspace configuration, verify SARK crate paths from sibling sark repository, and set up PyO3 basic bindings example.

## Objectives

1. Create repository structure (Cargo.toml workspace, rust/, python/, opnsense/, docs/)
2. Vendor or reference SARK crates (sark-opa, sark-cache, sark-audit from ../sark)
3. Create yori-core Rust library with PyO3 bindings
4. Implement basic proxy primitives (HTTP request/response structs)
5. Set up FreeBSD cross-compilation (x86_64-unknown-freebsd target)
6. Create scripts/build-freebsd.sh for automated builds
7. Configure GitHub Actions for CI/CD (build, test, artifact generation)
8. Write unit tests for Rust modules (cargo test)

## Deliverables

Complete implementation of: Establish Rust workspace with SARK crate integration, PyO3 bindings, and FreeBSD cross-compilation p

## Interface Contract

### Exports for python-proxy (Worker 2)

**Python Module:** `yori_core` (importable via PyO3)

**Functions:**
```python
# Policy evaluation
yori_core.evaluate_policy(request: dict, policy_path: str) -> PolicyResult

# Logger initialization
yori_core.init_logger(config: dict) -> None

# HTTP request parsing
yori_core.parse_http_request(raw: bytes) -> HttpRequest
```

### Exports for policy-engine (Worker 5)

**Functions:**
- Policy evaluation engine interface
- Rego file loader and validator
- Policy result data structure

## Files to Create

**Rust Core:**
- `rust/yori-core/Cargo.toml` - Workspace member with PyO3, sark-opa dependencies
- `rust/yori-core/src/lib.rs` - PyO3 module definition (#[pymodule])
- `rust/yori-core/src/policy.rs` - sark-opa integration for policy evaluation
- `rust/yori-core/src/proxy.rs` - HTTP request/response structs
- `rust/yori-core/src/audit.rs` - Logging primitives

**Build & CI:**
- `scripts/build-freebsd.sh` - FreeBSD cross-compilation script
- `.github/workflows/rust.yml` - CI/CD pipeline (build, test, artifacts)

**Documentation:**
- `rust/yori-core/README.md` - API documentation for Python consumers

## Performance Targets

- **Build Time:** <3 minutes for FreeBSD release build
- **Binary Size:** <10MB (stripped, release mode)
- **Memory:** <100MB RSS for Rust components only
- **Policy Evaluation:** <5ms per request (p95 latency)

## Testing Requirements

**Unit Tests:**
- All Rust modules (`cargo test --workspace`)
- Test coverage: >80% of Rust code

**Integration Tests:**
- PyO3 import from Python: `python3 -c "import yori_core"`
- Function calls work: Test evaluate_policy, init_logger

**Cross-Compilation:**
- Verify FreeBSD binary builds: `cargo build --target x86_64-unknown-freebsd`
- Binary is executable on FreeBSD (test in VM if possible)

**CI/CD:**
- GitHub Actions runs all tests
- Artifacts published for each commit
- Green builds required for merge

## Verification Commands

### From Worker Branch (cz1/feat/rust-foundation)

```bash
# Run all unit tests
cargo test --workspace --verbose

# Build for FreeBSD
cargo build --release --target x86_64-unknown-freebsd

# Check binary size (should be <10MB)
ls -lh target/x86_64-unknown-freebsd/release/libyori_core.so

# Test PyO3 import (requires Python environment)
python3 -c "import sys; sys.path.insert(0, 'target/release'); import yori_core; print(yori_core.__version__)"

# Run FreeBSD build script
./scripts/build-freebsd.sh

# Verify CI/CD configuration
cat .github/workflows/rust.yml
```

### Handoff Verification for Worker 2

Worker 2 should be able to run:
```bash
# From their branch, access Worker 1's artifacts
python3 -c "import yori_core; print(dir(yori_core))"
# Expected: ['evaluate_policy', 'init_logger', 'parse_http_request', ...]
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Interface contract implemented (evaluate_policy, init_logger, parse_http_request)
- [ ] PyO3 module importable from Python
- [ ] FreeBSD build succeeds (<10MB binary)
- [ ] All unit tests passing (cargo test)
- [ ] CI/CD pipeline configured and green
- [ ] Performance targets met (build time <3min, policy eval <5ms)
- [ ] Code committed to branch cz1/feat/rust-foundation
- [ ] Documentation complete (README.md with API examples)
