# Czarina Orchestration: HTTP Proxy Implementation

**Project:** YORI v0.2.0 - HTTP/HTTPS Proxy Server
**Objective:** Implement FastAPI-based reverse proxy for LLM traffic interception
**Duration:** 4 workers × ~4 hours each = 1 day parallelized
**Priority:** CRITICAL - Blocks demonstration of actual utility

---

## Context

YORI v0.2.0 has **complete enforcement logic** (153/187 tests passing) but **no HTTP proxy** to connect it to real traffic. All the decision-making, allowlist, consent, blocking logic works - we just need the plumbing.

**Current State:**
- ✅ EnforcementEngine works (unit tested)
- ✅ Block page rendering works
- ✅ Audit logging works
- ✅ Configuration loading works
- ❌ No HTTP server listening on port 8443
- ❌ No request interception
- ❌ No traffic forwarding

**Goal:** Create FastAPI reverse proxy that intercepts LLM API traffic, evaluates policies, and blocks or forwards requests.

---

## Success Criteria

### Must Have
1. ✅ HTTP/HTTPS server listening on configurable port (default 8443)
2. ✅ TLS termination with custom certificates
3. ✅ Intercept requests to configured LLM endpoints
4. ✅ Integration with EnforcementEngine for policy decisions
5. ✅ Serve block page HTML when requests blocked
6. ✅ Forward allowed requests to real APIs
7. ✅ Return upstream responses to clients
8. ✅ Log all events to audit database
9. ✅ Handle errors gracefully (timeouts, network errors)
10. ✅ Integration tests prove end-to-end flow

### Nice to Have
- Streaming response support (for GPT-4 streaming)
- Request/response body inspection
- Token counting integration
- Performance metrics/monitoring
- WebSocket support

### Explicitly Out of Scope
- Response transformation/modification
- Complex caching (beyond what exists)
- Load balancing multiple upstreams
- Advanced rate limiting
- Protocol translation

---

## Technical Approach

### Architecture

```
Client Request
    ↓
FastAPI Proxy (port 8443)
    ├─ TLS Termination (uvicorn)
    ├─ Parse HTTP Request
    ├─ Extract metadata (IP, headers, body preview)
    ↓
EnforcementEngine.should_enforce_policy()
    ├─ Check allowlist
    ├─ Check time exceptions
    ├─ Check emergency override
    ├─ Evaluate policy action
    ↓
Decision: Block or Allow?
    ↓
┌───────────────┴───────────────┐
│ BLOCK                    ALLOW│
↓                               ↓
render_block_page()      httpx.AsyncClient()
    ↓                           ↓
Return 403 HTML          Forward to real API
    ↓                           ↓
Log block event          Log request event
                               ↓
                        Return response
                               ↓
                        Log response event
```

### Technology Stack

- **Framework:** FastAPI (already dependency)
- **ASGI Server:** uvicorn with TLS support
- **HTTP Client:** httpx (async)
- **Logging:** Python logging + audit database
- **Configuration:** YoriConfig (existing)

### Key Components

**File Structure:**
```
python/yori/
├── proxy_server.py          # NEW - Main proxy FastAPI app
├── proxy_handlers.py        # NEW - Request/response handlers
├── proxy_middleware.py      # NEW - Logging middleware
└── __main__.py              # NEW - Entry point for python -m yori
```

---

## Worker Breakdown

### Worker 1: Basic Proxy Server
**File:** `python/yori/proxy_server.py`
**Objective:** Create FastAPI app that forwards HTTP requests

**Tasks:**
1. Create FastAPI application
2. Implement catch-all route handler `/{path:path}`
3. Accept all HTTP methods (GET, POST, PUT, DELETE, etc.)
4. Extract request details (headers, body, method, path)
5. Forward to hardcoded upstream (e.g., https://api.openai.com)
6. Return upstream response
7. Basic error handling

**Acceptance Criteria:**
```bash
# Start proxy
python -m yori.proxy_server

# Test forwarding (from another terminal)
curl -X POST http://localhost:8443/v1/chat/completions \
  -H "Host: api.openai.com" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Should forward to https://api.openai.com/v1/chat/completions
# Should return response (or error from OpenAI)
```

**Deliverables:**
- `python/yori/proxy_server.py` with FastAPI app
- Can start server with `python -m yori.proxy_server`
- Forwards requests to OpenAI/Anthropic
- Returns responses

**Dependencies:** None (can start immediately)

---

### Worker 2: TLS & Enforcement Integration
**File:** `python/yori/proxy_server.py` (extend Worker 1)
**Objective:** Add TLS support and integrate EnforcementEngine

**Tasks:**
1. Configure uvicorn with TLS (ssl_keyfile, ssl_certfile)
2. Load YoriConfig on startup
3. Initialize EnforcementEngine
4. Map request host to configured endpoints
5. Create PolicyResult (stub or real OPA integration)
6. Call `engine.should_enforce_policy()`
7. Check decision.should_block
8. Route to block handler or forward handler

**Acceptance Criteria:**
```bash
# Generate test cert
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout /tmp/test.key -out /tmp/test.crt \
  -days 365 -subj "/CN=localhost"

# Start with TLS
python -m yori.proxy_server \
  --cert /tmp/test.crt \
  --key /tmp/test.key

# Test HTTPS
curl -k https://localhost:8443/test

# Test enforcement (with test config that blocks)
curl -k https://localhost:8443/v1/chat/completions
# Should return block page if enforcement enabled
```

**Deliverables:**
- TLS support with custom certificates
- EnforcementEngine integrated
- Blocking works (returns error/block indication)
- Allowing works (forwards to upstream)

**Dependencies:** Worker 1 must complete first

---

### Worker 3: Block Page & Audit Integration
**File:** `python/yori/proxy_handlers.py` (new), extend proxy_server.py
**Objective:** Serve proper block page HTML and log to audit database

**Tasks:**
1. Create block response handler
2. Generate BlockDecision from EnforcementEngineDecision
3. Call `render_block_page()` to get HTML
4. Return HTMLResponse with 403 status
5. Initialize EnforcementAuditLogger on startup
6. Log block events when request blocked
7. Log request events when forwarding
8. Log response events after upstream responds
9. Include metadata (client IP, policy name, reason, duration)

**Acceptance Criteria:**
```bash
# Start proxy with enforcement enabled
python -m yori.proxy_server

# Make request that gets blocked
curl -k https://localhost:8443/v1/chat/completions \
  -H "Content-Type: application/json"

# Should return:
# - Status 403
# - HTML content with "Request Blocked by YORI"
# - Policy name and reason visible in HTML

# Check audit database
sqlite3 /var/db/yori/audit.db \
  "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 5;"

# Should show:
# - Block event logged
# - Correct client IP
# - Policy name
# - Reason
```

**Deliverables:**
- Block page served as HTML
- All events logged to audit database
- Block events have all metadata
- Request/response events logged

**Dependencies:** Workers 1 and 2 must complete first

---

### Worker 4: Testing, Polish & CLI
**Files:** `tests/integration/test_proxy.py` (new), `python/yori/__main__.py` (new)
**Objective:** Create integration tests and proper CLI entry point

**Tasks:**
1. Create integration test file
2. Test basic forwarding (mock upstream)
3. Test enforcement blocking
4. Test allowlist bypass
5. Test emergency override
6. Test audit logging
7. Test error handling (upstream timeout, connection error)
8. Create `__main__.py` for `python -m yori`
9. Add CLI arguments (--config, --host, --port, --cert, --key)
10. Add proper signal handling (SIGTERM, SIGINT)
11. Add startup/shutdown logging

**Acceptance Criteria:**
```bash
# Run integration tests
pytest tests/integration/test_proxy.py -v

# Should see:
# ✓ test_proxy_forwards_request
# ✓ test_proxy_blocks_request
# ✓ test_proxy_serves_block_page
# ✓ test_allowlist_bypass
# ✓ test_emergency_override_bypass
# ✓ test_audit_logging
# ✓ test_error_handling

# Test CLI
python -m yori --help
# Shows usage

python -m yori --config /path/to/config.yaml
# Starts proxy with config

# Test graceful shutdown
python -m yori &
PID=$!
kill -TERM $PID
# Should shutdown cleanly with log message
```

**Deliverables:**
- Integration test suite (6+ tests)
- CLI entry point working
- Configuration from file
- Signal handling
- Clean startup/shutdown

**Dependencies:** Workers 1, 2, and 3 must complete first

---

## Integration & Testing

### Integration Checklist

After all workers complete:

1. **Code Integration**
   - [ ] All files committed to git
   - [ ] No merge conflicts
   - [ ] All imports resolve
   - [ ] No circular dependencies

2. **Testing**
   - [ ] Unit tests still pass (pytest tests/unit/)
   - [ ] Integration tests pass (pytest tests/integration/test_proxy.py)
   - [ ] Manual smoke test works

3. **Documentation**
   - [ ] Docstrings on all public functions
   - [ ] README updated with proxy usage
   - [ ] Configuration examples updated

4. **Deployment**
   - [ ] Package builds: `pip install -e .`
   - [ ] Can run: `python -m yori`
   - [ ] Works with test config

### End-to-End Validation

**Test scenario:** Block an OpenAI request

```bash
# 1. Start proxy with enforcement
cat > /tmp/test_config.yaml << EOF
mode: enforce
listen: 0.0.0.0:8443

enforcement:
  enabled: true
  consent_accepted: true

policies:
  files:
    default:
      enabled: true
      action: block
EOF

python -m yori --config /tmp/test_config.yaml &

# 2. Make request (will be blocked)
curl -k https://localhost:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}]}'

# Expected:
# - Returns 403 status
# - HTML block page returned
# - Shows policy name and reason

# 3. Check audit log
sqlite3 /var/db/yori/audit.db \
  "SELECT event_type, client_ip, policy_name, reason FROM audit_events WHERE event_type='block';"

# Expected:
# - Block event logged
# - Has all metadata

# 4. Test allowlist bypass
# Add client to allowlist in config, restart, retry
# Expected: Request forwarded to real API
```

---

## Worker Coordination

### Parallel Execution

Workers 1, 2, 3, 4 must execute **sequentially** due to dependencies:
1. Worker 1 creates foundation
2. Worker 2 extends with TLS + enforcement
3. Worker 3 extends with block page + audit
4. Worker 4 tests everything

### Communication Points

- **Worker 1 → 2:** Must export FastAPI app structure, route handler pattern
- **Worker 2 → 3:** Must export enforcement integration points
- **Worker 3 → 4:** Must provide working proxy for testing

### Code Sharing

All workers work in same repository:
- Worker 1: Creates `proxy_server.py`
- Worker 2: Extends `proxy_server.py`, adds startup/config
- Worker 3: Extends handlers, adds audit
- Worker 4: Creates tests, adds CLI

---

## Technical Specifications

### Configuration Schema

**Already exists in YoriConfig:**
```yaml
listen: "0.0.0.0:8443"  # Proxy listen address

endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true

audit:
  database: /var/db/yori/audit.db

enforcement:
  enabled: true
  consent_accepted: true
```

**New additions needed:**
```yaml
proxy:
  tls_cert: /usr/local/etc/yori/yori.crt
  tls_key: /usr/local/etc/yori/yori.key
  upstream_timeout: 30
  max_request_size: 10485760  # 10MB
```

### API Signature

**Main proxy handler:**
```python
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_handler(request: Request, path: str) -> Response:
    """
    Main proxy handler - intercepts all requests

    Args:
        request: FastAPI Request object
        path: Requested path (e.g., "v1/chat/completions")

    Returns:
        Response: Either block page (403) or proxied response

    Raises:
        HTTPException: On upstream errors (502, 504)
    """
```

### Error Handling

**Required error cases:**
1. **Upstream timeout** → 504 Gateway Timeout
2. **Upstream connection error** → 502 Bad Gateway
3. **Invalid TLS cert** → Log error, return 500
4. **Unknown host** → 404 Not Found
5. **Policy evaluation error** → Allow by default, log error
6. **Audit log error** → Continue processing, log error

### Performance Targets

- **Latency overhead:** < 10ms p95 (proxy processing only)
- **Throughput:** 50 requests/second sustained
- **Memory:** < 256MB RSS under load
- **Concurrent connections:** 100+

---

## Dependencies & Imports

### New Dependencies (Add to pyproject.toml)

```toml
dependencies = [
    "fastapi>=0.109.0",      # Already present ✓
    "uvicorn[standard]>=0.27.0",  # Already present ✓
    "httpx>=0.26.0",         # Already present ✓
    # No new dependencies needed!
]
```

### Import Structure

```python
# Core FastAPI
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse

# HTTP client
import httpx

# YORI modules (all exist)
from yori.config import YoriConfig
from yori.enforcement import EnforcementEngine
from yori.models import PolicyResult, BlockDecision
from yori.block_page import render_block_page
from yori.audit_enforcement import EnforcementAuditLogger

# Standard library
import logging
from pathlib import Path
from typing import Dict, Optional
```

---

## Risk Mitigation

### Risk 1: Streaming Response Support

**Issue:** GPT-4 API uses server-sent events (SSE) for streaming
**Impact:** Streaming responses may not work
**Mitigation:**
- MVP: Support non-streaming responses only
- Future: Add SSE pass-through in v0.3.0
- Workaround: Clients can disable streaming

### Risk 2: TLS Certificate Issues

**Issue:** Custom CA certificates may not be trusted by clients
**Impact:** Clients get SSL errors
**Mitigation:**
- Clear documentation on CA installation
- Test with self-signed cert first
- Support OPNsense built-in CA

### Risk 3: Upstream API Changes

**Issue:** OpenAI/Anthropic may change APIs
**Impact:** Proxy may break
**Mitigation:**
- Pass-through approach (minimal modification)
- Don't parse request/response bodies unless needed
- Log raw requests for debugging

### Risk 4: Performance Under Load

**Issue:** Python async may not handle high concurrency
**Impact:** Slow responses, high memory
**Mitigation:**
- Use async/await throughout
- Connection pooling with httpx
- Load test before production
- Future: Move to Rust proxy if needed

---

## Success Metrics

### Code Quality
- [ ] All functions have docstrings
- [ ] Type hints on all public functions
- [ ] No pylint/mypy warnings
- [ ] Code coverage > 80%

### Functionality
- [ ] Can forward requests to OpenAI
- [ ] Can forward requests to Anthropic
- [ ] Can block requests based on policy
- [ ] Can serve block page HTML
- [ ] Can log to audit database
- [ ] Can handle errors gracefully

### Performance
- [ ] Latency < 10ms overhead
- [ ] Can handle 50 req/sec
- [ ] Memory < 256MB
- [ ] No memory leaks (long-running test)

### Integration
- [ ] Works with existing YoriConfig
- [ ] Works with EnforcementEngine
- [ ] Works with BlockPage rendering
- [ ] Works with audit logging
- [ ] Integration tests pass

---

## Delivery Format

### Git Workflow

```bash
# Worker 1
git checkout -b feature/proxy-basic-server
# ... implement ...
git commit -m "feat: Basic HTTP proxy server with forwarding"
git push origin feature/proxy-basic-server

# Worker 2 (after Worker 1 merges)
git checkout -b feature/proxy-tls-enforcement
git merge feature/proxy-basic-server
# ... implement ...
git commit -m "feat: Add TLS and enforcement integration"
git push origin feature/proxy-tls-enforcement

# Worker 3 (after Worker 2 merges)
git checkout -b feature/proxy-block-audit
git merge feature/proxy-tls-enforcement
# ... implement ...
git commit -m "feat: Add block page and audit logging"
git push origin feature/proxy-block-audit

# Worker 4 (after Worker 3 merges)
git checkout -b feature/proxy-testing-cli
git merge feature/proxy-block-audit
# ... implement ...
git commit -m "feat: Add integration tests and CLI"
git push origin feature/proxy-testing-cli
```

### Final Merge

```bash
# After all workers complete
git checkout main
git merge feature/proxy-testing-cli
git tag v0.2.1-proxy-complete
git push --tags
```

---

## Acceptance Criteria Summary

**For completion and merge to main:**

### Functional Requirements
1. ✅ HTTP/HTTPS server running on port 8443
2. ✅ Intercepts api.openai.com and api.anthropic.com
3. ✅ Integrates with EnforcementEngine
4. ✅ Serves block page when blocked
5. ✅ Forwards requests when allowed
6. ✅ Returns upstream responses
7. ✅ Logs to audit database
8. ✅ Handles errors gracefully

### Testing Requirements
9. ✅ Integration test suite passes (6+ tests)
10. ✅ Unit tests still pass (no regressions)
11. ✅ Manual smoke test succeeds
12. ✅ Load test shows acceptable performance

### Documentation Requirements
13. ✅ All functions documented
14. ✅ README updated with usage
15. ✅ Configuration examples provided

### Deployment Requirements
16. ✅ Package installs: `pip install -e .`
17. ✅ Can run: `python -m yori`
18. ✅ Works on Linux development machine
19. ✅ Ready for OPNsense deployment

---

## Timeline Estimate

**Sequential execution:** ~16 hours (4 workers × 4 hours)

**With perfect handoffs:**
- Hour 0-4: Worker 1 (basic proxy)
- Hour 4-8: Worker 2 (TLS + enforcement)
- Hour 8-12: Worker 3 (block page + audit)
- Hour 12-16: Worker 4 (testing + CLI)

**Realistic with breaks/integration:** 1-2 days

---

## Post-Completion

After all workers complete and merge:

1. **Update SESSION_SUMMARY.md** with proxy completion
2. **Update V0.2.0_TEST_STATUS.md** with integration test results
3. **Update CRITICAL_GAP_ANALYSIS.md** marking proxy as complete
4. **Run full test suite:** `pytest tests/ -v`
5. **Deploy to OPNsense** following OPNSENSE_DEPLOYMENT_TEST_PLAN.md
6. **Demonstrate actual utility** with live traffic interception

---

## Questions for Architect

Before starting implementation:

1. **Streaming support:** Should MVP support streaming responses? (Recommend: No, defer to v0.3.0)
2. **Request body inspection:** Should proxy parse/inspect request bodies? (Recommend: Only log preview)
3. **Response modification:** Should proxy be able to modify responses? (Recommend: No, pure pass-through)
4. **WebSocket support:** Support wss:// for streaming? (Recommend: No, HTTP only for MVP)
5. **Multi-upstream:** Support multiple backends per domain? (Recommend: No, single upstream per domain)

**Recommended answers for MVP:** No to all - keep it simple, pure reverse proxy with enforcement checks.

---

**Ready to orchestrate?** Run this with Czarina to implement the HTTP proxy in parallel with OPNsense testing!

