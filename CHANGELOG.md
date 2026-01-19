# Changelog

All notable changes to YORI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Integration Status (2026-01-19)

**Release Branch:** `cz1/release/v0.1.0`

This release branch has been created to integrate work from all czarina workers.
Current integration status:

#### Worker Branch Merges
- ✅ rust-foundation: Merged (no conflicts)
- ✅ python-proxy: Merged (no conflicts)
- ✅ opnsense-plugin: Merged (no conflicts)
- ✅ dashboard-ui: Merged (no conflicts)
- ✅ policy-engine: Merged (no conflicts)
- ✅ documentation: Merged (no conflicts)
- ✅ testing-qa: Merged (no conflicts)

#### Integration Fixes
- Fixed SARK dependency paths for worktree environment (`../../../../sark` vs `../sark`)

#### Known Blockers
- Build environment missing C compiler (required for Rust compilation)
- Worker branches do not yet contain completed work (expected at project start)

#### Pending Tasks
- Version updates in all files (Cargo.toml, pyproject.toml, +MANIFEST)
- Build validation (blocked by missing C compiler)
- Artifact generation (blocked by missing implementations)

---

## [0.1.0] - TBD

### Added
- Transparent proxy for LLM traffic (OpenAI, Anthropic, Gemini, Mistral)
- SQLite audit logging with 365-day retention
- Rust-based policy engine (sark-opa integration)
- OPNsense web UI (dashboard, audit viewer, policy editor)
- Advisory alert system (email, web, push notifications)
- 4+ pre-built policy templates (bedtime, high usage, privacy, homework)
- Comprehensive documentation (installation, configuration, policy guide)

### Performance Targets
- Latency overhead: <10ms (p95)
- Memory usage: <256MB RSS
- Throughput: >50 requests/sec
- SQLite queries: <100ms (100k+ records)

### Testing Targets
- Code coverage: >80% (Rust and Python)
- All tests passing (unit, integration, e2e)
- Performance benchmarks validated

[Unreleased]: https://github.com/apathy-ca/yori/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/apathy-ca/yori/releases/tag/v0.1.0
