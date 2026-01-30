# YORI Resilience Architecture

## Executive Summary

This document defines the resilience and fault tolerance architecture for the YORI proxy server. It identifies failure modes, recovery strategies, and implementation patterns to ensure the proxy remains reliable under adverse conditions.

## Current State Analysis

### Existing Resilience Features
- Basic signal handling (SIGTERM, SIGINT) in `__main__.py:53-59`
- Shutdown event handlers in `proxy.py:402-406`
- Error handling around audit logging with graceful degradation
- 30-second timeout on upstream HTTP client

### Identified Gaps
1. **Incomplete graceful shutdown**: Signal handler calls `sys.exit(0)` immediately without waiting for in-flight requests
2. **No circuit breaker**: Upstream API failures cause repeated timeouts and cascading failures
3. **No retry logic**: Transient failures aren't retried with backoff
4. **No audit failure recovery**: Failed audit logs are lost permanently
5. **Binary health checks**: No degraded state reporting

## Failure Modes and Recovery Strategies

### 1. Upstream API Failures

**Failure Scenarios:**
- Timeout (>30s)
- Connection refused
- HTTP 5xx errors
- Rate limiting (HTTP 429)
- DNS resolution failure

**Impact:**
- Request latency increase
- User-facing errors
- Resource exhaustion from repeated retries
- Cascading failures across all requests

**Recovery Strategy:**
- **Circuit Breaker Pattern** (pybreaker library)
  - **CLOSED**: Normal operation, requests flow through
  - **OPEN**: After 5 consecutive failures, reject requests immediately for 60s
  - **HALF-OPEN**: After cooldown, allow 3 test requests to check recovery
  - Track per-endpoint (OpenAI, Anthropic, custom upstreams)

- **Retry with Exponential Backoff** (tenacity library)
  - Max 3 attempts
  - Delays: 1s, 2s, 4s
  - Only retry on transient errors (timeout, 5xx, connection errors)
  - Do NOT retry on 4xx (client errors)

- **Fail-Open Mode** (configurable)
  - When circuit is OPEN, optionally allow requests through without policy enforcement
  - Log degraded state to audit trail
  - Operator can configure fail-closed for strict security

### 2. Audit Logging Failures

**Failure Scenarios:**
- Disk full
- Database locked/corrupted
- Permission denied
- I/O errors

**Impact:**
- Lost audit trail
- Compliance violations
- Inability to investigate incidents

**Recovery Strategy:**
- **Dead Letter Queue (DLQ)**
  - In-memory queue (deque with max 1000 entries)
  - Failed audits written to DLQ instead of being dropped
  - Background task retries DLQ every 5 minutes
  - Persistent DLQ (optional): Write to `/var/lib/yori/audit_dlq.jsonl` on shutdown

- **Graceful Degradation**
  - Continue proxying requests even if audit fails
  - Log audit failures to application log
  - Expose DLQ depth in health check

- **Audit Database Resilience**
  - WAL mode for SQLite (Write-Ahead Logging)
  - Connection pooling with retry
  - Periodic VACUUM to prevent corruption

### 3. Policy Evaluation Failures

**Failure Scenarios:**
- OPA service down
- Policy compilation error
- Evaluation timeout
- Network partition

**Impact:**
- Unable to enforce policy
- Security risk (fail-open) or availability risk (fail-closed)

**Recovery Strategy:**
- **Circuit Breaker** (same pattern as upstream APIs)
  - Track policy evaluation failures separately
  - Open circuit after 5 consecutive failures

- **Fail-Safe Configuration**
  - `policy.fail_mode: "open"` - Allow on policy failure (availability)
  - `policy.fail_mode: "closed"` - Block on policy failure (security)
  - Default: "open" for home use, "closed" for enterprises

- **Caching Last Known Good Policy**
  - Cache successful policy results for 60s
  - On failure, use cached result with degraded flag
  - Log when using cached/degraded policy

### 4. Resource Exhaustion

**Failure Scenarios:**
- Memory pressure from high request volume
- File descriptor exhaustion
- Thread pool saturation

**Impact:**
- Process crash
- Request queueing/delays
- System instability

**Recovery Strategy:**
- **Request Limiting**
  - Max concurrent requests: 100 (configurable)
  - Queue depth: 50 requests
  - Request timeout: 60s total (including retries)

- **Connection Pooling**
  - Max connections per endpoint: 20
  - Connection timeout: 10s
  - Keep-alive: 30s

- **Memory Management**
  - Limit request body size: 10MB
  - Stream large responses (no buffering)
  - Periodic garbage collection hint in health check

### 5. Graceful vs. Forced Shutdown

**Failure Scenarios:**
- SIGTERM (graceful shutdown request)
- SIGKILL (forced termination)
- Process crash
- Container termination

**Impact:**
- In-flight requests dropped
- Partial responses sent to clients
- Corrupted audit logs
- Lost DLQ entries

**Recovery Strategy:**
- **Graceful Shutdown Sequence** (max 30s)
  1. Stop accepting new requests (return HTTP 503)
  2. Wait for in-flight requests to complete (max 25s)
  3. Flush DLQ to disk
  4. Close audit database connections
  5. Shutdown HTTP client connections
  6. Exit process

- **Persistent State on Shutdown**
  - Write DLQ to `/var/lib/yori/audit_dlq.jsonl`
  - Sync audit database (WAL checkpoint)
  - Log shutdown event with stats

- **Startup Recovery**
  - Load DLQ from disk on startup
  - Validate audit database integrity
  - Report recovery status in logs

## Health Check Enhancement

### Current Implementation
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "mode": config.mode}
```

### Enhanced Implementation

**Health States:**
- `healthy`: All systems operational
- `degraded`: Partial functionality (circuit open, DLQ not empty, cache in use)
- `unhealthy`: Critical failure (cannot accept requests)

**Health Check Response:**
```json
{
  "status": "degraded",
  "timestamp": "2025-01-29T22:00:00Z",
  "uptime_seconds": 3600,
  "version": "0.2.0",
  "components": {
    "http_server": {"status": "healthy"},
    "upstream_apis": {
      "status": "degraded",
      "openai_circuit": "open",
      "anthropic_circuit": "closed"
    },
    "policy_engine": {"status": "healthy"},
    "audit_logger": {
      "status": "degraded",
      "dlq_depth": 42,
      "last_success": "2025-01-29T21:55:00Z"
    }
  },
  "metrics": {
    "requests_total": 1000,
    "requests_in_flight": 5,
    "circuit_breakers_open": 1
  }
}
```

**Kubernetes/Docker Integration:**
- `/health` - Overall health (200=healthy, 503=degraded/unhealthy)
- `/health/live` - Liveness probe (200=process alive, 503=restart needed)
- `/health/ready` - Readiness probe (200=can accept traffic, 503=not ready)

## Implementation Components

### 1. Circuit Breaker (pybreaker)
```python
# python/yori/resilience/circuit_breaker.py
from pybreaker import CircuitBreaker

openai_breaker = CircuitBreaker(
    fail_max=5,           # Open after 5 failures
    timeout_duration=60,  # Stay open for 60s
    name="openai_api"
)
```

### 2. Retry Logic (tenacity)
```python
# python/yori/resilience/retry.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
)
async def call_upstream_with_retry(url, ...):
    pass
```

### 3. Dead Letter Queue
```python
# python/yori/resilience/dlq.py
from collections import deque
from typing import Dict, Any
import json

class AuditDeadLetterQueue:
    def __init__(self, max_size: int = 1000):
        self._queue = deque(maxlen=max_size)

    def enqueue(self, audit_event: Dict[str, Any]):
        """Add failed audit to DLQ"""
        pass

    def retry_pending(self):
        """Retry all pending audits"""
        pass

    def save_to_disk(self, path: str):
        """Persist DLQ on shutdown"""
        pass

    def load_from_disk(self, path: str):
        """Restore DLQ on startup"""
        pass
```

### 4. Graceful Shutdown
```python
# python/yori/resilience/shutdown.py
import asyncio
import signal

class GracefulShutdown:
    def __init__(self, app, timeout: int = 30):
        self.app = app
        self.timeout = timeout
        self.shutdown_event = asyncio.Event()

    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self.shutdown_event.wait()

    async def shutdown_sequence(self):
        """Execute graceful shutdown"""
        # 1. Stop accepting new requests
        # 2. Wait for in-flight requests
        # 3. Flush DLQ
        # 4. Close connections
        pass
```

## Testing Strategy

### Unit Tests
- Circuit breaker state transitions
- Retry backoff timing
- DLQ enqueue/dequeue/persistence
- Health check status calculation

### Integration Tests
- Upstream API failure simulation (mock server down)
- Audit database failure (disk full, permission denied)
- Graceful shutdown with in-flight requests
- DLQ persistence and recovery

### Chaos Engineering
- Random upstream failures (10% failure rate)
- Network latency injection (500ms-5s)
- Disk space exhaustion
- SIGTERM during high load

## Configuration

```yaml
# yori.conf
resilience:
  circuit_breaker:
    enabled: true
    fail_max: 5
    timeout_duration: 60
    half_open_max_attempts: 3

  retry:
    enabled: true
    max_attempts: 3
    backoff_multiplier: 1
    backoff_min: 1
    backoff_max: 4

  dead_letter_queue:
    enabled: true
    max_size: 1000
    retry_interval: 300  # 5 minutes
    persist_on_shutdown: true
    persistence_path: /var/lib/yori/audit_dlq.jsonl

  graceful_shutdown:
    enabled: true
    timeout: 30  # seconds
    wait_for_requests: true

  request_limits:
    max_concurrent: 100
    queue_depth: 50
    request_timeout: 60

  fail_modes:
    upstream_api: "fail_through"  # fail_through, fail_block
    policy_engine: "fail_open"    # fail_open, fail_closed
    audit_logger: "continue"      # continue, halt
```

## Success Metrics

1. **Zero dropped requests during graceful shutdown**
   - Test: Send 100 concurrent requests, trigger SIGTERM
   - Success: All requests complete with valid responses

2. **Circuit breaker prevents cascade failures**
   - Test: Simulate upstream API down
   - Success: Circuit opens, requests fail fast (<100ms), no timeout cascade

3. **Retry logic recovers from transient failures**
   - Test: Inject 50% random failures
   - Success: Requests succeed on retry, total latency < 10s

4. **DLQ preserves failed audits**
   - Test: Simulate disk full, send 100 requests
   - Success: 100 events in DLQ, all replayed on recovery

5. **Health check reflects degraded state**
   - Test: Open circuit breaker
   - Success: Health check returns 503 with "degraded" status

6. **Memory usage remains stable under load**
   - Test: 1000 req/s for 5 minutes
   - Success: Memory growth < 10%, no leaks

## Timeline

- **Week 1**: Graceful shutdown + circuit breaker
- **Week 2**: Retry logic + DLQ
- **Week 3**: Health checks + testing
- **Week 4**: Documentation + integration

## Dependencies

- `pybreaker==1.0.1` - Circuit breaker implementation
- `tenacity==8.2.3` - Retry with exponential backoff
- No new system dependencies

## Future Enhancements

1. **Distributed circuit breaker** - Share state across multiple proxy instances
2. **Persistent DLQ** - SQLite or Redis backend
3. **Advanced retry strategies** - Jitter, adaptive backoff
4. **Request hedging** - Send duplicate requests on timeout
5. **Bulkhead pattern** - Isolate resource pools per upstream
6. **Metrics integration** - Prometheus, Grafana dashboards
