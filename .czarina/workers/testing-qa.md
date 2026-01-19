# Worker Identity: testing-qa

**Role:** Qa
**Agent:** Cursor
**Branch:** cz1/feat/testing-qa
**Phase:** 1
**Dependencies:** policy-engine

## Mission

Develop comprehensive test suite covering unit tests, integration tests, end-to-end tests, and performance benchmarks. Verify all functionality and performance targets.

## 🚀 YOUR FIRST ACTION

Review all code from workers 1-5, create tests/ directory structure (unit/, integration/, e2e/), and write integration test that sends real request through proxy to verify end-to-end flow.

## Objectives

1. Create test infrastructure (pytest config, test fixtures)
2. Write Rust unit tests (cargo test for all modules)
3. Write Python unit tests (pytest for proxy, audit, config)
4. Create integration tests:

## Deliverables

Complete implementation of: Develop comprehensive test suite covering unit tests, integration tests, end-to-end tests, and performance benchmarks

## Dependencies from Upstream Workers

### From All Workers (1-5)

**Code to Test:**
- Rust core (Worker 1): Policy evaluation, PyO3 bindings
- Python proxy (Worker 2): FastAPI, SQLite, proxy logic
- OPNsense plugin (Worker 3): Service management, web UI
- Dashboard (Worker 4): UI rendering, SQL queries
- Policy engine (Worker 5): Policy evaluation, alerts

**Verification Before Starting:**
```bash
# Verify all code is implemented and builds
cargo build --workspace
pytest python/ --collect-only  # List Python tests
ls -la opnsense/  # Check plugin exists
```

## Interface Contract

### Exports for integration-release (Worker 8)

**Test Results:**
- All tests passing (100% success rate)
- >80% code coverage (Rust and Python)
- Performance benchmarks documented:
  - Latency: <10ms (p95)
  - Memory: <256MB RSS
  - Throughput: 50 req/sec
- Test reports (HTML coverage, benchmark results)

## Files to Create

**Test Infrastructure:**
- `pytest.ini` - Pytest configuration
- `tests/conftest.py` - Pytest fixtures
- `.github/workflows/tests.yml` - CI/CD test automation

**Rust Unit Tests:**
- `rust/yori-core/src/policy.rs` - Policy tests (inline with #[cfg(test)])
- `rust/yori-core/src/proxy.rs` - Proxy tests
- `rust/yori-core/src/audit.rs` - Audit tests

**Python Unit Tests:**
- `tests/unit/test_proxy.py` - Proxy logic tests
- `tests/unit/test_audit.py` - SQLite audit tests
- `tests/unit/test_config.py` - Configuration tests
- `tests/unit/test_policy.py` - Policy wrapper tests
- `tests/unit/test_alerts.py` - Alert system tests

**Integration Tests:**
- `tests/integration/test_e2e_proxy.py` - End-to-end proxy flow
- `tests/integration/test_policy_eval.py` - Policy evaluation with real Rego
- `tests/integration/test_audit_logging.py` - SQLite integrity
- `tests/integration/test_alerts.py` - Alert delivery

**E2E Tests:**
- `tests/e2e/test_opnsense_install.py` - Plugin installation
- `tests/e2e/test_service_management.py` - Start/stop/status
- `tests/e2e/test_dashboard.py` - UI rendering
- `tests/e2e/test_llm_traffic.py` - Real LLM interception

**Performance Tests:**
- `tests/performance/test_latency.py` - Latency measurement
- `tests/performance/test_throughput.py` - Load testing (wrk/ab)
- `tests/performance/test_memory.py` - Memory profiling
- `tests/performance/test_sqlite.py` - Database performance

**Test Reports:**
- `tests/reports/coverage.html` - Coverage report
- `tests/reports/benchmarks.md` - Performance results

## Performance Targets

All targets from PROJECT_PLAN.md must be validated:

- **Latency:** <10ms overhead (p95) - proxy adds minimal delay
- **Throughput:** 50 requests/sec sustained
- **Memory:** <256MB RSS under normal load
- **SQLite:** Query time <100ms for 100k+ records
- **Policy Eval:** <5ms per request (from Worker 1)

## Testing Requirements

**Coverage Targets:**
- Rust: >80% code coverage (`cargo tarpaulin`)
- Python: >80% code coverage (`pytest --cov`)

**Test Categories:**

1. **Unit Tests (Fast, Isolated)**
   - Rust: All modules with #[cfg(test)]
   - Python: All modules mocked

2. **Integration Tests (Medium Speed)**
   - End-to-end proxy flow
   - Database operations
   - Policy evaluation with real Rego
   - Alert delivery

3. **E2E Tests (Slow, Full System)**
   - OPNsense plugin installation
   - Service lifecycle
   - Dashboard rendering
   - Real LLM traffic

4. **Performance Tests (Benchmarks)**
   - Latency measurement (wrk)
   - Load testing (ab)
   - Memory profiling (ps/valgrind)
   - SQLite performance

## Verification Commands

### From Worker Branch (cz1/feat/testing-qa)

```bash
# Run all Rust tests
cargo test --workspace --verbose

# Run all Python unit tests
pytest tests/unit/ -v --cov=yori --cov-report=html

# Run integration tests
pytest tests/integration/ -v

# Run E2E tests (requires OPNsense VM)
pytest tests/e2e/ -v

# Run performance tests
pytest tests/performance/ -v

# Generate coverage report
pytest --cov=yori --cov-report=html
firefox tests/reports/coverage.html

# Check coverage percentage
pytest --cov=yori --cov-report=term | grep TOTAL
# Expected: >80%
```

### Performance Benchmarks

```bash
# Start YORI service
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &

# Latency test (wrk)
wrk -t4 -c100 -d30s http://127.0.0.1:8443/health
# Expected: p95 < 10ms

# Throughput test (ab)
ab -n 3000 -c 50 http://127.0.0.1:8443/health
# Expected: >50 req/sec

# Memory test
ps aux | grep yori | awk '{print $6/1024 " MB"}'
# Expected: <256 MB RSS

# SQLite performance
python3 tests/performance/test_sqlite.py
# Expected: <100ms queries with 100k records
```

### CI/CD Integration

```bash
# Verify CI/CD workflow
cat .github/workflows/tests.yml

# Run CI locally (if using act)
act -j test

# Check GitHub Actions status
gh run list --workflow=tests.yml
```

### Handoff Verification for Worker 8

Worker 8 should be able to:
```bash
# Verify all tests pass
pytest tests/ -v
cargo test --workspace

# Check coverage meets target
pytest --cov=yori --cov-report=term | grep TOTAL
# Expected: >80%

# Verify performance benchmarks
cat tests/reports/benchmarks.md
# Expected: All targets met (<10ms, <256MB, 50 req/sec)

# Run final QA before release
./scripts/qa-checklist.sh
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Test infrastructure set up (pytest.ini, conftest.py, CI/CD)
- [ ] >80% code coverage (Rust and Python combined)
- [ ] All Rust unit tests passing (cargo test)
- [ ] All Python unit tests passing (pytest unit/)
- [ ] All integration tests passing (pytest integration/)
- [ ] All E2E tests passing (pytest e2e/)
- [ ] Performance targets met and documented:
  - [ ] Latency <10ms (p95)
  - [ ] Memory <256MB RSS
  - [ ] Throughput >50 req/sec
  - [ ] SQLite queries <100ms (100k records)
- [ ] Load test passes (50 req/sec for 60 seconds)
- [ ] Coverage reports generated (HTML)
- [ ] Benchmark results documented (tests/reports/benchmarks.md)
- [ ] CI/CD workflow configured and passing
- [ ] Code committed to branch cz1/feat/testing-qa
- [ ] All test results ready for Worker 8 integration
