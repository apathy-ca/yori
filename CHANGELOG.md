# Changelog

All notable changes to YORI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Integration Complete (2026-01-19) - v0.1.0-rc1

**Release Branch:** `cz1/release/v0.1.0`
**Status:** ⚠️ Integration Complete - Critical Issues Found
**Release Readiness:** 65% (NOT READY - See QA_REVIEW_REPORT.md)

All 7 worker branches successfully merged with comprehensive conflict resolution. Integration produced a substantial codebase with 120 source files, but critical build and test issues prevent immediate release.

#### Worker Branch Merges (7/7 Complete)

| Worker | Status | Commits | Conflicts | Key Deliverables |
|--------|--------|---------|-----------|------------------|
| rust-foundation | ✅ Merged | 5 | 2 | Rust workspace, PyO3 bindings, FreeBSD support |
| python-proxy | ✅ Merged | 3 | 1 | FastAPI proxy, LLM interception, audit logging |
| opnsense-plugin | ✅ Merged | 1 | 3 | Plugin package, service management, web UI |
| dashboard-ui | ✅ Merged | 2 | 2 | Dashboard, Chart.js, audit viewer, CSV export |
| policy-engine | ✅ Merged | 1 | 5 | OPA integration, 5 policies, alert system |
| documentation | ✅ Merged | 2 | 1 | User/dev guides, FAQ, troubleshooting |
| testing-qa | ✅ Merged | 2 | 1 | Test suite, coverage reporting |

**Integration Statistics:**
- Total Commits: 16 (7 merges + 9 worker commits)
- Conflicts Resolved: 15 file conflicts
- Source Files: 120 (32 Rust, 31 Python, 6 PHP, 5 Rego, 10 docs)
- Lines of Code: ~13,000+
- Conflict Resolution Success: 100%

#### Critical Issues Found (Blocking Release)

🔴 **P0 Blockers:**
1. **Rust Compilation Failure**
   - Vendored sark-opa has API mismatch with opa-wasm 0.1.9
   - 7 compilation errors in `rust/vendor/sark-opa/src/lib.rs`
   - Cannot build libyori_core.so artifact
   - Fix: Revert to external SARK OR update vendored API

2. **Test Coverage Below Target**
   - Python coverage: 39% (target: 80%)
   - 263 statements uncovered
   - Main proxy logic untested
   - Fix: Add integration tests

🟡 **P1 Major Issues:**
3. **Python Test Import Errors**
   - ModuleNotFoundError in test suite
   - Pytest path configuration issue
   - Fix: Update conftest.py

#### What Works

✅ All worker code integrated successfully
✅ Comprehensive documentation (6,000+ lines)
✅ 5 policy templates (bedtime, high_usage, homework, privacy, default)
✅ OPNsense plugin structure complete
✅ Dashboard UI implementation
✅ Python proxy with 4 LLM providers
✅ Zero code loss during integration

#### What's Broken

❌ Rust compilation (vendored SARK API mismatch)
❌ Python test suite (39% coverage, import errors)
❌ Cannot build release artifacts
❌ Performance targets not validated

#### Next Steps (Required for v0.1.0 Release)

1. Fix Rust compilation (2-4 hours)
2. Fix Python test imports (30 minutes)
3. Increase test coverage to 80% (8-12 hours)
4. Build and verify artifacts (2 hours)

**Estimated Time to Release:** 12-18 hours

See `QA_REVIEW_REPORT.md` for comprehensive analysis.

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
