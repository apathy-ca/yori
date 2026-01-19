# YORI Rust Foundation - Build Instructions

## ✅ Current Status

- Code compiles cleanly: `cargo check --workspace` passes
- All stub implementations have proper warning suppressions
- SARK crates properly referenced
- FreeBSD build script ready
- CI/CD pipeline configured

## 🔧 Required Setup

To complete the build and run tests, you need to install development dependencies:

### 1. Install Build Tools

```bash
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev python3-dev
```

**What this installs:**
- `build-essential`: GCC compiler, make, and essential build tools
- `pkg-config`: Helper for compiling applications and libraries
- `libssl-dev`: OpenSSL development headers (required for TLS/HTTPS)
- `python3-dev`: Python development headers (required for PyO3 linking)

### 2. Install FreeBSD Target

```bash
rustup target add x86_64-unknown-freebsd
```

## 🧪 Testing

### Check Compilation (No Python Linking Required)

```bash
cargo check --workspace
```

This verifies the code compiles correctly without needing Python libraries.

### Run Full Test Suite (Requires python3-dev)

```bash
cargo test --workspace --verbose
```

This will:
- Run all unit tests in cache.rs, policy.rs, proxy.rs, audit.rs
- Verify PyO3 bindings compile correctly
- Test all functionality

Expected output:
```
running 9 tests
test cache::tests::test_cache_creation ... ok
test policy::tests::test_policy_engine_creation ... ok
test proxy::tests::test_proxy_config_default ... ok
test proxy::tests::test_should_intercept ... ok
test audit::tests::test_audit_event_creation ... ok
test audit::tests::test_prompt_redaction ... ok
test audit::tests::test_policy_decision ... ok
test audit::tests::test_audit_event_json ... ok
test audit::tests::test_audit_logger ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

### Build Release Binary for FreeBSD

```bash
./scripts/build-freebsd.sh --release
```

This will:
1. Install FreeBSD target if not present
2. Build optimized binary for OPNsense
3. Verify binary size (<10MB target)
4. Show deployment instructions

Expected output:
```
=================================================
YORI FreeBSD Cross-Compilation Build
=================================================
Workspace: /home/jhenry/Source/yori/.czarina/worktrees/rust-foundation
Target:    x86_64-unknown-freebsd
Mode:      --release
=================================================

[1/4] Checking for FreeBSD target...
FreeBSD target already installed

[2/4] Building Rust workspace for FreeBSD...
   Compiling yori-core v0.1.0
    Finished `release` profile [optimized] target(s) in 2m 45s

[3/4] Checking binary size...
Binary: target/x86_64-unknown-freebsd/release/libyori_core.so
Size:   8MB (8388608 bytes)
✓ Binary size within 10MB target

[4/4] Build artifacts:
-rw-r--r-- 1 user user 8.0M Jan 19 16:30 libyori_core.so

=================================================
Build complete!
=================================================
```

## 🐍 Test PyO3 Import (Requires Python Build)

After building the release binary:

```bash
# For Linux build
python3 -c "import sys; sys.path.insert(0, 'target/release'); import yori_core; print(f'Version: {yori_core.__version__}')"

# For FreeBSD build (won't work on Linux, but verifies it was built)
ls -lh target/x86_64-unknown-freebsd/release/libyori_core.so
```

## 📊 Performance Verification

After building, check performance targets:

```bash
# Build time (should be <3 minutes)
time ./scripts/build-freebsd.sh --release

# Binary size (should be <10MB)
ls -lh target/x86_64-unknown-freebsd/release/libyori_core.so | awk '{print $5}'

# Memory usage (will be verified during integration testing)
# Policy evaluation latency (will be verified during integration testing)
```

## 🔄 CI/CD Verification

Once pushed to GitHub, the CI/CD pipeline will automatically:

1. **Test Suite**: Run `cargo test --workspace` on Ubuntu
2. **Code Quality**: Check formatting (rustfmt) and linting (clippy)
3. **Build Linux**: Build release binary for x86_64-linux
4. **Build FreeBSD**: Build release binary for x86_64-freebsd
5. **Coverage**: Generate code coverage report (target: >80%)
6. **Artifacts**: Publish binaries for download

View pipeline status at: https://github.com/apathy-ca/yori/actions

## 🚀 Quick Start (After Installing Dependencies)

```bash
# Install all dependencies
sudo apt-get update && sudo apt-get install -y build-essential pkg-config libssl-dev python3-dev
rustup target add x86_64-unknown-freebsd

# Run full verification
cargo test --workspace
./scripts/build-freebsd.sh --release

# Expected result: All tests pass, FreeBSD binary built successfully
```

## ❌ Troubleshooting

### Error: "linker `cc` not found"

**Solution:** Install build-essential
```bash
sudo apt-get install build-essential
```

### Error: "undefined symbol: PyObject_Str" (and other Python symbols)

**Solution:** Install Python development headers
```bash
sudo apt-get install python3-dev
```

### Error: "error: linking with `cc` failed"

**Solution:** Install pkg-config and OpenSSL development headers
```bash
sudo apt-get install pkg-config libssl-dev
```

### Warning: "fields are never read"

These are expected warnings from stub implementations. They've been suppressed with `#[allow(dead_code)]` attributes. If you see these, you're running an older version - update to latest commit.

## 📝 Next Steps

After successful build:

1. **Verify tests pass**: All 9 unit tests should pass
2. **Check binary size**: FreeBSD binary should be <10MB
3. **Push to GitHub**: CI/CD will verify everything builds correctly
4. **Handoff to Worker 2**: python-proxy worker can now import `yori_core`

## 📋 Success Checklist

- [ ] `cargo check --workspace` passes with no errors/warnings
- [ ] `cargo test --workspace` passes (all 9 tests)
- [ ] `cargo clippy --workspace` passes (no warnings)
- [ ] `cargo fmt --all --check` passes (code formatted)
- [ ] FreeBSD build succeeds with `./scripts/build-freebsd.sh`
- [ ] Binary size <10MB
- [ ] GitHub Actions CI/CD pipeline passes (after push)

---

**Need help?** See [rust/yori-core/README.md](rust/yori-core/README.md) for API documentation and usage examples.
