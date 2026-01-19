# Worker Identity: python-proxy

**Role:** Code
**Agent:** Aider
**Branch:** cz1/feat/python-proxy
**Phase:** 1
**Dependencies:** rust-foundation

## Mission

Build FastAPI transparent proxy service that intercepts LLM traffic, evaluates policies via Rust core, and forwards requests to real LLM endpoints. Implement comprehensive audit logging to SQLite.

## 🚀 YOUR FIRST ACTION

Read Rust PyO3 bindings from worker 1, create python/yori/ package structure with FastAPI app skeleton, and implement basic health check endpoint to verify service startup.

## Objectives

1. Create Python package structure (pyproject.toml, python/yori/)
2. Implement FastAPI application with TLS termination support
3. Create transparent proxy logic (listen :8443, forward to LLM endpoints)
4. Integrate Rust policy evaluation via PyO3 (import yori_core)
5. Implement SQLite audit logging (schema from docs/PROJECT_PLAN.md)
6. Add LLM endpoint detection (OpenAI, Anthropic, Gemini, Mistral)
7. Create configuration loader (YAML from /usr/local/etc/yori/yori.conf)
8. Implement observe/advisory/enforce mode switching
9. Add request/response logging with privacy controls (prompt preview truncation)
10. Write Python unit tests (pytest, pytest-asyncio)

## Deliverables

Complete implementation of: Build FastAPI transparent proxy service that intercepts LLM traffic, evaluates policies via Rust cor

## Dependencies from Upstream Workers

### From rust-foundation (Worker 1)

**Required Artifacts:**
- `yori_core` Python module (PyO3 bindings)
- Functions needed:
  - `yori_core.evaluate_policy(request: dict, policy_path: str) -> PolicyResult`
  - `yori_core.init_logger(config: dict) -> None`
  - `yori_core.parse_http_request(raw: bytes) -> HttpRequest`

**Verification Before Starting:**
```bash
# Verify Worker 1 artifacts are available
python3 -c "import yori_core; print(yori_core.__version__)"
# Expected: "0.1.0" or successful import
```

## Interface Contract

### Exports for opnsense-plugin (Worker 3)

**FastAPI Application:**
- Location: `python/yori/main.py`
- Start command: `uvicorn yori.main:app --host 0.0.0.0 --port 8443`
- Health check: `GET /health` → `{"status": "healthy", "version": "0.1.0"}`

**Configuration:**
- File: `/usr/local/etc/yori/yori.conf` (YAML format)
- Schema documented in `python/yori/config.py`

### Exports for dashboard-ui (Worker 4)

**SQLite Database:**
- Location: `/var/db/yori/audit.db`
- Schema: See `sql/schema.sql`
- Table: `audit_events` (matches PROJECT_PLAN.md spec)
- Views: `daily_stats` for aggregated queries

**Optional API Endpoints:**
- `GET /api/stats` - Statistics for dashboard
- `GET /api/audit` - Paginated audit logs

### Exports for policy-engine (Worker 5)

**Policy Integration Points:**
- `python/yori/proxy.py` - Proxy logic with policy evaluation hooks
- Policy result handling (allow/alert/block actions)
- Alert trigger interface

## Files to Create

**Python Package:**
- `python/yori/__init__.py` - Package initialization, version
- `python/yori/main.py` - FastAPI application entry point
- `python/yori/proxy.py` - Transparent proxy logic (intercept, forward)
- `python/yori/audit.py` - SQLite audit logging implementation
- `python/yori/config.py` - YAML configuration loader
- `python/yori/models.py` - Pydantic models (request, response, config)

**Database:**
- `sql/schema.sql` - SQLite database schema (audit_events table, indexes, views)

**Configuration:**
- Example config: `examples/yori.conf.example` (YAML)

**Tests:**
- `tests/test_proxy.py` - Proxy logic tests
- `tests/test_audit.py` - SQLite logging tests
- `tests/test_config.py` - Configuration loading tests
- `tests/test_integration.py` - End-to-end proxy flow

## Performance Targets

- **Request Latency:** <10ms overhead (p95) - proxy should add minimal latency
- **Throughput:** 50 requests/sec sustained (home use: ~1-10 req/sec typical)
- **Memory:** <150MB RSS for Python service
- **Database Writes:** <5ms per audit record

## Testing Requirements

**Unit Tests:**
- All Python modules (`pytest tests/`)
- Test coverage: >80% of Python code
- Mock Rust bindings for unit tests (use unittest.mock)

**Integration Tests:**
- End-to-end proxy flow: Request → log → policy check → forward → response
- SQLite database operations (insert, query, export)
- Configuration loading from YAML

**Load Tests:**
- 50 req/sec for 60 seconds: `ab -n 3000 -c 50 http://localhost:8443/health`
- Database performance: 1000+ audit records without degradation

**Performance Tests:**
- Measure latency overhead (proxy vs direct)
- Memory usage under load
- SQLite query performance (with indexes)

## Verification Commands

### From Worker Branch (cz1/feat/python-proxy)

```bash
# Run all unit tests
pytest tests/ --cov=yori --cov-report=term

# Start FastAPI service
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &

# Health check
curl http://127.0.0.1:8443/health
# Expected: {"status": "healthy", "version": "0.1.0"}

# Test proxy flow (mock LLM endpoint)
curl -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# Verify SQLite logging
sqlite3 /var/db/yori/audit.db "SELECT COUNT(*) FROM audit_events;"
# Expected: >0 (audit records exist)

# Load test
ab -n 1000 -c 10 http://127.0.0.1:8443/health

# Performance test
wrk -t4 -c100 -d30s http://127.0.0.1:8443/health
```

### Handoff Verification for Worker 3

Worker 3 should be able to run:
```bash
# From their branch, start the service
cd <python-proxy-worktree>
uvicorn yori.main:app --host 0.0.0.0 --port 8443 &

# Verify service responds
curl http://localhost:8443/health
# Expected: {"status": "healthy"}
```

### Handoff Verification for Worker 4

Worker 4 should be able to:
```bash
# Query SQLite database for dashboard
sqlite3 /var/db/yori/audit.db "
SELECT
  DATE(timestamp) as date,
  endpoint,
  COUNT(*) as request_count
FROM audit_events
GROUP BY DATE(timestamp), endpoint;
"
# Expected: Aggregated data for charts
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Dependencies from Worker 1 verified (yori_core importable)
- [ ] Interface contracts implemented (FastAPI, SQLite, config)
- [ ] FastAPI service starts and responds to health check
- [ ] Proxy logs LLM traffic to SQLite (end-to-end test)
- [ ] Configuration loading works (YAML → Pydantic models)
- [ ] All unit tests passing (pytest, >80% coverage)
- [ ] Performance targets met (< 10ms latency, 50 req/sec throughput)
- [ ] Load tests pass (60 seconds sustained)
- [ ] Code committed to branch cz1/feat/python-proxy
- [ ] Integration tests demonstrate full proxy flow
- [ ] Documentation updated (docstrings, README)
