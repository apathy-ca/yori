# YORI Developer Guide

Guide for developers who want to build, test, or contribute to YORI.

---

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Building from Source](#building-from-source)
- [Testing](#testing)
- [Development Workflow](#development-workflow)
- [Contributing](#contributing)
- [Release Process](#release-process)

---

## Development Environment Setup

### Prerequisites

**Required Tools:**
- Git 2.30+
- Rust 1.92+ (via rustup)
- Python 3.11+
- FreeBSD 13.2+ (for native builds) or Docker (for cross-compilation)

**Optional Tools:**
- maturin 1.4+ (for PyO3 package building)
- pre-commit (for git hooks)
- act (for local GitHub Actions testing)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/apathy-ca/yori.git
cd yori

# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup install 1.92
rustup default 1.92

# Add FreeBSD target (for cross-compilation)
rustup target add x86_64-unknown-freebsd

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -e ".[dev]"

# Install development tools
pip install maturin pytest pytest-asyncio black ruff

# Install pre-commit hooks
pre-commit install
```

---

## Building from Source

### Building Rust Core

```bash
# Navigate to Rust workspace
cd rust/yori-core

# Build in development mode (faster, includes debug symbols)
cargo build

# Build in release mode (optimized, production)
cargo build --release

# Run tests
cargo test

# Check for common issues
cargo clippy
```

**Output:**
- Development: `target/debug/libyori_core.so`
- Release: `target/release/libyori_core.so`

### Cross-Compiling for FreeBSD

**From Linux/macOS:**

```bash
# Install FreeBSD cross-compilation toolchain
./scripts/install-freebsd-toolchain.sh

# Build for FreeBSD
cargo build --release --target x86_64-unknown-freebsd

# Output: target/x86_64-unknown-freebsd/release/libyori_core.so
```

**Using Docker (easier):**

```bash
# Build using FreeBSD container
docker run --rm -v $(pwd):/source \
    freebsd:13.2 \
    sh -c "cd /source && cargo build --release"
```

### Building Python Package

**Using maturin (PyO3 packages):**

```bash
# Build wheel in development mode (editable install)
maturin develop

# Build wheel for distribution
maturin build --release

# Output: target/wheels/yori-0.1.0-cp311-cp311-freebsd_13_2_x86_64.whl
```

### Building OPNsense Package

```bash
# Package script handles all steps
./scripts/package.sh --version 0.1.0

# Steps performed:
# 1. Build Rust core for FreeBSD
# 2. Build Python package
# 3. Create OPNsense plugin structure
# 4. Generate +MANIFEST
# 5. Create .pkg file

# Output: dist/os-yori-0.1.0.pkg
```

---

## Testing

### Unit Tests (Rust)

```bash
cd rust/yori-core

# Run all tests
cargo test

# Run specific test
cargo test test_policy_evaluation

# Run with output
cargo test -- --nocapture

# Run with coverage
cargo tarpaulin --out Html
```

### Unit Tests (Python)

```bash
# Run all Python tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=yori --cov-report=html

# Run with verbose output
pytest -v
```

### Integration Tests

```bash
# Run full integration test suite
./scripts/run-integration-tests.sh

# Tests include:
# - Full request interception flow
# - Policy evaluation
# - SQLite audit logging
# - Alert dispatching
```

### End-to-End Tests

**Requirements:**
- OPNsense VM or physical router
- Test devices with CA certificate installed

```bash
# Deploy to test OPNsense instance
./scripts/deploy-test.sh --target 192.168.1.1

# Run E2E test suite
./scripts/run-e2e-tests.sh

# Cleanup
./scripts/cleanup-test.sh
```

---

## Development Workflow

### Making Changes

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Follow code style guidelines (see below)
   - Write tests for new functionality
   - Update documentation

3. **Run tests locally**
   ```bash
   cargo test
   pytest
   ./scripts/run-integration-tests.sh
   ```

4. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

### Code Style

**Rust:**
- Follow Rust standard style (enforced by `rustfmt`)
- Run `cargo fmt` before committing
- Run `cargo clippy` and fix warnings

**Python:**
- Follow PEP 8 (enforced by `black` and `ruff`)
- Run `black .` before committing
- Run `ruff check .` and fix issues

**Commit Messages:**
- Follow Conventional Commits specification
- Format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

**Examples:**
```
feat(policy): Add bedtime policy template
fix(proxy): Handle connection timeouts gracefully
docs(readme): Update installation instructions
test(audit): Add SQLite integration tests
```

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full contribution guidelines.

### Quick Contribution Checklist

- [ ] Fork repository and create feature branch
- [ ] Write code following style guidelines
- [ ] Add tests for new functionality
- [ ] Update documentation
- [ ] Run full test suite locally
- [ ] Ensure CI passes
- [ ] Request review from maintainers

### Areas Needing Contribution

**High Priority:**
- Transparent proxy implementation (Python)
- sark-opa integration (Rust)
- OPNsense plugin UI (PHP/Volt)
- Dashboard charts (JavaScript)

**Medium Priority:**
- Additional policy templates
- Alert system (email/push)
- FreeBSD build automation
- Test coverage improvements

**Documentation:**
- Installation guides for specific hardware
- Policy examples for various use cases
- Video tutorials
- Translation to other languages

---

## Release Process

### Version Numbering

YORI follows Semantic Versioning (SemVer):

- **Major (1.0.0):** Breaking changes
- **Minor (0.1.0):** New features, backward compatible
- **Patch (0.1.1):** Bug fixes only

### Creating a Release

**Maintainers only:**

```bash
# 1. Update version in all files
./scripts/bump-version.sh 0.1.0

# Files updated:
# - Cargo.toml
# - pyproject.toml
# - opnsense/+MANIFEST

# 2. Update CHANGELOG.md
# Add release notes under new version header

# 3. Commit version bump
git add .
git commit -m "chore: Bump version to 0.1.0"

# 4. Tag release
git tag -a v0.1.0 -m "Release v0.1.0"

# 5. Push to GitHub
git push origin main --tags

# 6. Build release artifacts
./scripts/build-release.sh --version 0.1.0

# Artifacts created:
# - dist/os-yori-0.1.0.pkg
# - dist/yori-0.1.0-cp311-cp311-freebsd_13_2_x86_64.whl
# - dist/yori-0.1.0.tar.gz (source)

# 7. Create GitHub Release
# - Upload artifacts
# - Copy CHANGELOG section to release notes
# - Mark as pre-release if < 1.0.0
```

### Release Checklist

- [ ] All tests passing on CI
- [ ] CHANGELOG.md updated with release notes
- [ ] Version bumped in all files
- [ ] Documentation updated for new features
- [ ] Security review completed (if applicable)
- [ ] Package tested on fresh OPNsense install
- [ ] Release notes reviewed by maintainers
- [ ] GitHub release created with artifacts

---

## Debugging

### Debugging Rust Code

```bash
# Build with debug symbols
cargo build

# Run with RUST_BACKTRACE for detailed errors
RUST_BACKTRACE=1 cargo test

# Use rust-gdb for debugging
rust-gdb target/debug/yori_core

# Enable debug logging
RUST_LOG=debug cargo run
```

### Debugging Python Code

```bash
# Run with Python debugger
python -m pdb -m yori --config test-config.yaml

# Use ipdb for better experience
pip install ipdb
# Add: import ipdb; ipdb.set_trace() in code

# Enable debug logging
YORI_LOG_LEVEL=DEBUG python -m yori
```

### Debugging on OPNsense

```bash
# SSH into OPNsense router
ssh root@192.168.1.1

# Watch service logs in real-time
tail -f /var/log/yori/yori.log

# Run YORI manually for immediate feedback
/usr/local/bin/yori --config /usr/local/etc/yori/yori.conf --debug

# Check service status
service yori status

# Restart with verbose logging
service yori restart && tail -f /var/log/yori/yori.log
```

---

## Architecture Decisions

For understanding design choices, see:

- [Architecture Documentation](ARCHITECTURE.md)
- [Project Plan](PROJECT_PLAN.md)
- [ADRs (Architecture Decision Records)](../docs/adr/) - _Coming in v0.2.0_

---

## Getting Help

**For Contributors:**
- GitHub Discussions: General questions
- GitHub Issues: Bug reports, feature requests
- Discord: Real-time chat with maintainers (link in README)

**For Maintainers:**
- Maintainer docs: `docs/MAINTAINER_GUIDE.md` (private repo)
- Security issues: GitHub Security Advisories

---

**Developer guide version:** v0.1.0 (2026-01-19)
