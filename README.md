# YORI - Home LLM Gateway

**Zero-trust LLM governance for your home network**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OPNsense](https://img.shields.io/badge/OPNsense-24.1+-blue.svg)](https://opnsense.org/)
[![Rust](https://img.shields.io/badge/rust-1.92+-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

---

## What is YORI?

YORI brings enterprise-grade LLM governance to home networks. It runs as a lightweight plugin on your OPNsense router, observing and optionally controlling AI traffic.

**Think of it as:** Parental controls + network monitoring + privacy protection for AI assistants.

### Use Cases

- 📊 **Monitor AI Usage** - See what your family asks ChatGPT, Claude, Gemini
- 🔒 **Privacy Protection** - Detect when devices send unexpected data to LLMs
- 👨‍👩‍👧‍👦 **Parental Controls** - Set bedtime policies, content filters
- 💰 **Cost Tracking** - Understand ChatGPT Plus usage across your household
- 🏠 **Local-First** - Prefer local Ollama over cloud LLMs

---

## Quick Start

### Prerequisites

- OPNsense 24.1+ router (FreeBSD 13.2+)
- 512MB RAM available
- 1GB disk space for audit logs

### Installation

```bash
# From OPNsense web UI
System → Firmware → Plugins → Search "yori" → Install

# Or manually
pkg install os-yori
service yori enable
service yori start
```

### First Configuration

1. Navigate to **Services → YORI → Dashboard**
2. Select **Mode: Observe** (recommended for first week)
3. Enable endpoints to monitor (OpenAI, Anthropic, Google)
4. Install CA certificate on your devices (see [CA Setup Guide](docs/CA_SETUP.md))

That's it! YORI is now logging all LLM traffic.

---

## Features

### Phase 1: Observe Mode (v0.1.0 - In Development)

- 🔄 Transparent LLM traffic interception
- 🔄 SQLite audit logging (1 year retention)
- 🔄 Web dashboard with charts and statistics
- 🔄 Support for OpenAI, Anthropic, Google, Mistral
- 🔄 Device-level tracking (who asked what)
- 🔄 Export to CSV for analysis

### Phase 2: Advisory Mode (v0.2.0)

- 🔄 Policy-based alerts (email, push notifications)
- 🔄 Pre-built policy templates (bedtime, high usage, homework)
- 🔄 Simple no-code policy builder
- 🔄 Privacy detection (PII in prompts)

### Phase 3: Enforcement Mode (v0.3.0)

- ⏳ Optional blocking (user must opt-in)
- ⏳ Per-device policies
- ⏳ Time-based restrictions
- ⏳ Allowlist/blocklist management

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              OPNsense Router (FreeBSD)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  OPNsense Plugin (PHP/MVC)                         │ │
│  │  - Web UI for config/dashboard                     │ │
│  │  - Service management                              │ │
│  │  - Log viewer                                      │ │
│  └────────────────┬───────────────────────────────────┘ │
│                   │                                      │
│  ┌────────────────▼───────────────────────────────────┐ │
│  │  YORI Service (Python + Rust)                      │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │  Python Layer (FastAPI)                      │ │ │
│  │  │  - Transparent proxy                         │ │ │
│  │  │  - Request routing                           │ │ │
│  │  │  - SQLite audit logging                      │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │  Rust Core (from SARK)                       │ │ │
│  │  │  - sark-opa: Policy evaluation               │ │ │
│  │  │  - sark-cache: In-memory caching             │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Code Sharing with SARK

YORI reuses battle-tested Rust components from [SARK](https://github.com/apathy-ca/sark):

- **sark-opa** - Embedded OPA policy engine (4-10x faster than HTTP)
- **sark-cache** - Lock-free in-memory cache (no Redis needed)
- **sark-audit** - Logging primitives

This gives YORI enterprise-grade performance on home router hardware.

---

## Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[User Guide](docs/USER_GUIDE.md)** - Configuration and usage
- **[Policy Guide](docs/POLICY_GUIDE.md)** - Writing custom policies
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Building from source
- **[Architecture](docs/ARCHITECTURE.md)** - Technical design
- **[FAQ](docs/FAQ.md)** - Common questions

---

## Development

### Building from Source

```bash
# Prerequisites
rustup install 1.92
python3.11 -m venv venv
source venv/bin/activate

# Clone
git clone https://github.com/apathy-ca/yori.git
cd yori

# Build Rust core
cd rust/yori-core
cargo build --release --target x86_64-unknown-freebsd

# Install Python dependencies
pip install -e ".[dev]"

# Run tests
cargo test
pytest
```

See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for details.

---

## Project Status

🚧 **Early Development** - Architecture and skeleton code in place

**What Works Now:**
- ✅ Repository structure and build system
- ✅ Configuration loading (YAML → Pydantic models)
- ✅ PyO3 bindings skeleton (Rust ↔ Python)
- ✅ FastAPI server (basic health check endpoint)

**In Active Development:**
- 🔄 Transparent proxy implementation (stub code exists)
- 🔄 SQLite audit logging (schema defined, not implemented)
- 🔄 sark-opa policy engine integration (stub code exists)
- 🔄 OPNsense plugin (planned, not started)
- 🔄 Web dashboard (planned, not started)

**Current Milestone:** M1 - Foundation complete, starting M2 (Transparent Proxy)
**Target:** v0.1.0 alpha release in ~3 months

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for detailed roadmap.

---

## Relationship to SARK

YORI is the lightweight home variant of [SARK](https://github.com/apathy-ca/sark) (Security Audit and Resource Kontroler).

| Feature | SARK (Enterprise) | YORI (Home) |
|---------|-------------------|-------------|
| Target | Kubernetes, 50K+ users | OPNsense router, single family |
| Resources | 4 CPU, 8GB RAM | 1 CPU, 512MB RAM |
| Database | PostgreSQL + TimescaleDB | SQLite |
| Cache | Valkey/Redis cluster | Rust in-memory |
| Auth | OIDC, LDAP, SAML | HTTP Basic (family) |
| SIEM | Splunk, Datadog | JSON logs + Web UI |
| Deployment | Helm, Terraform | OPNsense plugin |

Both implement the [GRID Protocol](https://github.com/apathy-ca/grid-protocol) for universal AI governance.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code style and standards
- Development workflow
- PR process
- Testing guidelines

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

**Copyright** © 2026 James Henry. All rights reserved.

---

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/apathy-ca/yori/issues)
- **Discussions:** [GitHub Discussions](https://github.com/apathy-ca/yori/discussions)
- **Security:** Report via [GitHub Security Advisories](https://github.com/apathy-ca/yori/security/advisories/new)

---

## Acknowledgments

- **SARK** - Rust core components for policy and caching
- **OPNsense** - Excellent router platform and plugin ecosystem
- **GRID Protocol** - Universal AI governance specification

---

**Built with ❤️ for families who care about AI privacy and safety.**
