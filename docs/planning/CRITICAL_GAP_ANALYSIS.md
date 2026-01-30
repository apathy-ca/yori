# YORI v0.2.0 Critical Gap Analysis

**Date:** 2026-01-27
**Context:** Ready to deploy to OPNsense for actual utility demonstration
**Status:** ⚠️ **CRITICAL COMPONENT MISSING**

---

## The Bottom Line

**What Works:** ✅
- All enforcement logic (153 tests passing)
- Allowlist, consent, time exceptions, emergency override
- Audit logging, block page rendering
- Configuration loading, policy evaluation
- Rust/PyO3 integration (stubs)

**What's Missing:** ❌
- **HTTP/HTTPS Proxy Server Implementation**

---

## The Missing Component

### What We Have: Logic Without Plumbing

```python
# ✅ These all work perfectly:
from yori.enforcement import EnforcementEngine
from yori.allowlist import is_allowlisted
from yori.block_page import render_block_page
from yori.audit import log_block_event

# ❌ This doesn't exist:
from yori.proxy import ProxyServer  # Module exists, but empty stub
```

### What We Need: HTTP Proxy Server

**Required functionality:**

1. **Listen on port 8443 (HTTPS)**
   - Accept incoming TLS connections
   - Terminate TLS with custom certificate
   - Parse HTTP requests

2. **Request Interception**
   - Identify LLM API endpoints (openai.com, anthropic.com, etc.)
   - Extract request details (method, path, headers, body)
   - Log to audit database

3. **Policy Evaluation Integration**
   - Call `EnforcementEngine.should_enforce_policy()`
   - Get decision: allow/alert/block

4. **Action Execution**
   - **If ALLOW:** Forward request to real API, return response
   - **If ALERT:** Forward but log warning
   - **If BLOCK:** Return block page HTML

5. **Response Handling**
   - Forward upstream response to client
   - Log response metadata (status, tokens, duration)

---

## Current State of Proxy Code

### What Exists in Repository

**File:** `python/yori/proxy.py`
**Status:** ~289 lines of stub code
**Reality:** Does NOT implement HTTP proxy

**What it contains:**
```python
# Type definitions
class ProxyConfig(BaseModel): ...
class ProxyMode(Enum): ...

# Functions that return NotImplementedError
def forward_request(...) -> ProxyResponse:
    raise NotImplementedError("Proxy forwarding not yet implemented")

def intercept_request(...) -> InterceptResult:
    raise NotImplementedError("Request interception not yet implemented")
```

### What the Rust Code Has

**File:** `rust/yori-core/src/proxy.rs`
**Status:** ~160 lines of struct definitions
**Reality:** NO actual proxy implementation

**What it contains:**
```rust
// Structs defined but not used
pub struct ProxyConfig { ... }
pub struct ProxyServer { ... }

// Methods that are never called
impl ProxyServer {
    pub fn new(...) -> Self { unimplemented!() }
    pub async fn start(&self) -> Result<()> { unimplemented!() }
}
```

---

## Impact on OPNsense Deployment

### What WILL Work

✅ **Package Installation**
- Python package installs
- Service script runs
- Configuration loads
- Logs initialize

✅ **Network Configuration**
- DNS overrides work (api.openai.com → 10.0.0.1)
- Port forwarding works (443 → 8443)
- Client traffic reaches OPNsense

✅ **Enforcement Logic**
- Allowlist checks work
- Time exceptions apply
- Emergency override functions
- All decision logic validated

### What WON'T Work

❌ **Actual Interception**
```
Client Request
    ↓
DNS: api.openai.com → 10.0.0.1  ✅
    ↓
TCP: Connect to 10.0.0.1:8443   ✅
    ↓
TLS Handshake                   ❌ No listener
    ↓
HTTP Request                    ❌ Not handled
    ↓
[Connection fails]
```

**The proxy doesn't listen or respond.**

❌ **Traffic Forwarding**
- Requests not forwarded to real APIs
- Responses not returned to clients
- System appears broken from client perspective

❌ **Actual Blocking**
- Can't serve block page (no HTTP server)
- Can't log requests (nothing to intercept)
- Enforcement engine never called

---

## Test Plan Impact

### From OPNSENSE_DEPLOYMENT_TEST_PLAN.md

**Phases 1-6 (Setup):** ✅ Will work
- OPNsense installation
- Package installation
- Service configuration
- Network setup
- Service starts

**Phase 7 (Traffic Testing):** ⚠️ Partial
- DNS resolution: ✅ Works
- Connection attempts: ✅ Reaches OPNsense
- Traffic interception: ❌ **FAILS** (no listener)
- Request logging: ❌ **FAILS** (nothing to log)

**Phase 8 (Enforcement):** ❌ Cannot test
- All enforcement logic requires working proxy
- Block page cannot be served
- Allowlist bypass can't be demonstrated
- No actual requests to enforce

**Phase 9 (Audit):** ❌ Empty
- Database created: ✅
- Events logged: ❌ **NONE** (no traffic)
- Statistics: ❌ All zeros

**Phase 10 (Performance):** ❌ N/A
- Can't measure latency of non-existent proxy
- Can't load test non-functional service

---

## Demonstration Limitations

### What You CAN Demonstrate

1. **"Look, the config loads!"**
   ```bash
   # Show config file
   cat /usr/local/etc/yori/yori.conf

   # Show it parses
   python -c "from yori.config import YoriConfig; YoriConfig.from_yaml(...)"
   ```

2. **"The enforcement logic works!"**
   ```bash
   # Run unit tests
   pytest tests/unit/ -v
   # Shows: 119/127 passing
   ```

3. **"DNS interception works!"**
   ```bash
   nslookup api.openai.com
   # Returns: 10.0.0.1
   ```

4. **"Network setup is correct!"**
   ```bash
   tcpdump -i em1 port 8443
   # Shows: Connections arriving
   ```

### What You CANNOT Demonstrate

❌ **"YORI blocks OpenAI requests"**
- Because proxy doesn't handle requests

❌ **"Allowlist bypass works"**
- Because no requests are processed

❌ **"Block page is shown to users"**
- Because proxy doesn't serve HTTP

❌ **"Audit logs capture traffic"**
- Because no traffic is intercepted

❌ **"Emergency override works in practice"**
- Because there's nothing to override

---

## Options Forward

### Option 1: Implement HTTP Proxy (Required for Demo)

**Effort:** 2-4 days for basic implementation
**Complexity:** Moderate-High (async Python + TLS)

**Approach A: FastAPI Reverse Proxy**
```python
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(request: Request, path: str):
    # 1. Check enforcement
    decision = enforcement_engine.should_enforce_policy(...)

    if decision.should_block:
        # 2. Return block page
        return render_block_page(...)

    # 3. Forward to real API
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"https://real-api.openai.com/{path}",
            headers=request.headers,
            content=await request.body()
        )

    # 4. Log and return
    log_request(...)
    return response
```

**Approach B: mitmproxy Integration**
```python
from mitmproxy import http

class YORIAddon:
    def request(self, flow: http.HTTPFlow):
        # Check enforcement
        # Block or allow
        # Log event

    def response(self, flow: http.HTTPFlow):
        # Log response
        # Audit tokens/duration
```

**Approach C: Use Rust Proxy (More Work)**
```rust
// Implement in rust/yori-core/src/proxy.rs
// Use hyper + rustls for TLS proxy
// Call Python enforcement logic via PyO3
```

### Option 2: Demo with Mock Proxy

**Effort:** 2-4 hours
**Complexity:** Low

Create minimal HTTP server that:
- Listens on 8443
- Logs all requests
- Returns canned responses
- Demonstrates flow without actually proxying

**Good for:** Proving concept
**Bad for:** Production use

### Option 3: Document Current State

**Effort:** 1 hour
**Complexity:** Low

Create honest demo showing:
- ✅ What works (enforcement logic, tests)
- ⚠️ What's partial (network setup, DNS)
- ❌ What's missing (proxy implementation)
- 📋 Roadmap to completion

**Good for:** Transparency, planning
**Bad for:** "Wow factor"

---

## Recommendation

### For Immediate Demo (Next Week)

**Implement Option 1A: FastAPI Reverse Proxy**

**Why:**
- FastAPI already a dependency
- Async support built-in
- TLS with uvicorn
- Can integrate with existing enforcement logic
- 2-4 days to working prototype

**MVP Feature Set:**
```
✅ Listen on HTTPS (port 8443)
✅ Intercept OpenAI/Anthropic requests
✅ Call EnforcementEngine for decisions
✅ Return block page when blocked
✅ Forward requests when allowed
✅ Log to audit database
✅ Handle TLS termination
```

**Out of scope for MVP:**
- ❌ Streaming responses (gpt-4 streaming)
- ❌ WebSocket support
- ❌ Response transformation
- ❌ Advanced caching

### Implementation Checklist

**Day 1: Basic Proxy**
- [ ] Create FastAPI app with catch-all route
- [ ] Accept any HTTP method
- [ ] Forward to hardcoded upstream
- [ ] Return response

**Day 2: TLS & Enforcement**
- [ ] Configure TLS with custom cert
- [ ] Integrate EnforcementEngine
- [ ] Serve block page on block decision
- [ ] Log decisions to audit

**Day 3: Request/Response Handling**
- [ ] Parse request headers/body
- [ ] Preserve all headers in forward
- [ ] Handle different content types
- [ ] Error handling

**Day 4: Testing & Polish**
- [ ] Test with real OpenAI API
- [ ] Test enforcement scenarios
- [ ] Deploy to OPNsense
- [ ] End-to-end validation

---

## Code Skeleton for FastAPI Proxy

**File:** `python/yori/proxy_server.py` (new file)

```python
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import httpx
import logging
from pathlib import Path

from yori.config import YoriConfig
from yori.enforcement import EnforcementEngine
from yori.models import PolicyResult, BlockDecision
from yori.block_page import render_block_page
from yori.audit_enforcement import EnforcementAuditLogger

logger = logging.getLogger(__name__)

app = FastAPI(title="YORI Proxy")

# Global state (loaded on startup)
config: YoriConfig = None
engine: EnforcementEngine = None
audit: EnforcementAuditLogger = None

UPSTREAM_HOSTS = {
    "api.openai.com": "https://api.openai.com",
    "api.anthropic.com": "https://api.anthropic.com",
}

@app.on_event("startup")
async def startup():
    global config, engine, audit

    config_path = Path("/usr/local/etc/yori/yori.conf")
    config = YoriConfig.from_yaml(config_path)
    engine = EnforcementEngine(config)
    audit = EnforcementAuditLogger(str(config.audit.database))

    logger.info(f"YORI Proxy started in {config.mode} mode")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_handler(request: Request, path: str):
    """Main proxy handler - intercepts all requests"""

    client_ip = request.client.host
    host = request.headers.get("Host", "unknown")

    logger.info(f"Request from {client_ip} to {host}/{path}")

    # 1. Check if this is an LLM endpoint we intercept
    if host not in UPSTREAM_HOSTS:
        logger.warning(f"Unknown host: {host}")
        return Response(content="Not Found", status_code=404)

    # 2. Check enforcement
    # TODO: Get actual policy result from OPA engine
    policy_result = PolicyResult(
        action="alert",  # Stub - replace with real policy
        policy_name="default.rego",
        reason="Test policy"
    )

    decision = engine.should_enforce_policy(
        request={"method": request.method, "path": path},
        policy_result=policy_result,
        client_ip=client_ip
    )

    # 3. If blocked, return block page
    if decision.should_block:
        logger.warning(f"BLOCKED: {client_ip} - {decision.reason}")

        # Log block event
        audit.log_block_event(
            client_ip=client_ip,
            policy_name=decision.policy_name,
            reason=decision.reason,
            endpoint=host
        )

        # Render and return block page
        block = BlockDecision(
            should_block=True,
            policy_name=decision.policy_name,
            reason=decision.reason,
            allow_override=False  # TODO: Make configurable
        )
        html = render_block_page(block)
        return HTMLResponse(content=html, status_code=403)

    # 4. Forward request to real API
    upstream_url = f"{UPSTREAM_HOSTS[host]}/{path}"

    # Preserve headers (remove some)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("connection", None)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=await request.body(),
                timeout=30.0
            )

        # 5. Log successful request
        audit.log_request_event(
            client_ip=client_ip,
            endpoint=host,
            method=request.method,
            path=path,
            status_code=response.status_code
        )

        logger.info(f"FORWARDED: {client_ip} → {host} → {response.status_code}")

        # Return upstream response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )

    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return Response(content="Bad Gateway", status_code=502)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        ssl_keyfile="/usr/local/etc/yori/yori.key",
        ssl_certfile="/usr/local/etc/yori/yori.crt",
        log_level="info"
    )
```

---

## Timeline to Working Demo

**With FastAPI Proxy Implementation:**

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Implement basic proxy | Requests forwarded |
| 2 | Add enforcement integration | Blocking works |
| 3 | Polish & testing | All features work |
| 4 | Deploy to OPNsense | Live demo ready |

**Total: 4 days to working demonstration**

---

## Final Status

**Current:** v0.2.0 has excellent *logic* but no *plumbing*
**Needed:** HTTP proxy server implementation
**Effort:** ~4 days for working demo
**Outcome:** Fully functional LLM traffic interception and enforcement

**The enforcement logic is production-ready. We just need the proxy server to connect it to real traffic.**

