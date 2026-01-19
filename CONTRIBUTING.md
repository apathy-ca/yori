# Contributing to YORI

Thank you for your interest in contributing to YORI! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Rust 1.92+ ([install Rust](https://rustup.rs/))
- Python 3.11+
- FreeBSD 13.2+ (for testing on target platform)
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/apathy-ca/yori.git
cd yori

# Set up Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -e ".[dev]"

# Build Rust components
cargo build

# Run tests
cargo test
pytest
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Write clear, concise code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Rust tests
cargo test
cargo clippy

# Python tests
pytest
black python/
ruff check python/

# Build check
cargo build --release
```

### 4. Commit Your Changes

Use conventional commit messages:

```bash
git commit -m "feat: Add new policy evaluation feature"
git commit -m "fix: Resolve proxy timeout issue"
git commit -m "docs: Update installation guide"
```

Commit types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `chore:` - Build/tooling changes
- `refactor:` - Code refactoring

### 5. Submit a Pull Request

1. Push your branch: `git push origin feature/your-feature-name`
2. Open a PR on GitHub
3. Describe your changes clearly
4. Reference any related issues

## Code Style

### Rust

- Follow standard Rust conventions
- Run `cargo fmt` before committing
- Run `cargo clippy` and fix warnings
- Document public APIs with doc comments

### Python

- Follow PEP 8
- Use `black` for formatting (line length: 100)
- Use `ruff` for linting
- Use type hints where appropriate

## Testing

### Rust Tests

```bash
# Run all tests
cargo test

# Run specific test
cargo test test_name

# Run with output
cargo test -- --nocapture
```

### Python Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=yori
```

## Documentation

- Update README.md for user-facing changes
- Update docs/ for detailed documentation
- Add docstrings to new functions/classes
- Update PROJECT_PLAN.md if changing milestones

## FreeBSD Cross-Compilation

YORI targets FreeBSD (OPNsense). To cross-compile:

```bash
# Install FreeBSD target
rustup target add x86_64-unknown-freebsd

# Build for FreeBSD
cargo build --release --target x86_64-unknown-freebsd
```

## Pull Request Guidelines

### Good PRs

- ✅ Single, focused change
- ✅ Clear description
- ✅ Tests included
- ✅ Documentation updated
- ✅ Passes CI checks

### Avoid

- ❌ Multiple unrelated changes
- ❌ No description
- ❌ Breaking existing tests
- ❌ Undocumented changes

## Community

- **Issues:** Report bugs or request features via [GitHub Issues](https://github.com/apathy-ca/yori/issues)
- **Discussions:** Join discussions on [GitHub Discussions](https://github.com/apathy-ca/yori/discussions)
- **Security:** Report security issues via [GitHub Security Advisories](https://github.com/apathy-ca/yori/security/advisories/new)

## Code of Conduct

- Be respectful and constructive
- Help others learn and grow
- Focus on the technical merits
- Assume good intent

## Questions?

If you have questions about contributing:
1. Check existing documentation
2. Search closed issues/PRs
3. Open a discussion on GitHub
4. Ask in your PR

Thank you for contributing to YORI! 🎉
