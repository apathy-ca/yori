# Worker Identity: block-page

**Role:** Code
**Agent:** Claude
**Branch:** cz2/feat/block-page
**Phase:** 2
**Dependencies:** enforcement-mode

## Mission

Create a friendly, informative block page that explains to users why their LLM request was blocked. Include policy name, reason, timestamp, and an optional override mechanism with password authentication.

## 🚀 YOUR FIRST ACTION

Read enforcement-mode code to understand EnforcementDecision structure, then create block page HTML template with clear explanation and override form.

## Dependencies from Upstream Workers

### From enforcement-mode (Worker 9, Phase 2)

**Required Artifacts:**
```python
# python/yori/enforcement.py
class EnforcementDecision:
    should_block: bool
    policy_name: str
    reason: str
    timestamp: datetime
    allow_override: bool
```

**Verification Before Starting:**
```bash
# Verify enforcement logic exists
python3 -c "from python.yori.enforcement import should_enforce_policy"
# Expected: No import error
```

### From python-proxy (Phase 1, Worker 2)

**Integration Point:**
- `python/yori/proxy.py` - Request handler to return block page

## Objectives

1. Create block page HTML template (friendly, informative)
2. Implement block page rendering in proxy
3. Add request override mechanism (password/PIN)
4. Create override password configuration
5. Log override attempts (successful and failed)
6. Add override audit trail
7. Create customizable block messages per policy
8. Add "emergency override" option (admin only)
9. Implement rate limiting on override attempts
10. Write tests for block page rendering and overrides

## Interface Contract

### Exports for enhanced-audit (Worker 12)

**Override Events:**
```python
# Audit events for Worker 12
- 'override_attempt'   # User tried to override block
- 'override_success'   # Override successful
- 'override_failed'    # Override failed (wrong password)
- 'emergency_override' # Admin emergency override used
```

**Override Data:**
```python
class OverrideEvent:
    request_id: str
    client_ip: str
    policy_name: str
    password_hash: str  # For failed attempts (audit)
    success: bool
    timestamp: datetime
```

## Files to Create

**Templates:**
- `python/yori/templates/block_page.html` - Main block page template
- `python/yori/templates/override_form.html` - Override form template

**Python Core:**
- `python/yori/block_page.py` - Block page rendering
- `python/yori/override.py` - Override password validation

**Configuration:**
```yaml
# Add to yori.conf
enforcement:
  override_enabled: true
  override_password_hash: "sha256:..."  # Hashed password
  override_rate_limit: 3  # Max 3 attempts per minute

  custom_messages:
    bedtime: "LLM access is restricted after bedtime. Please try again tomorrow."
    privacy: "This request contains potentially sensitive information."
```

**OPNsense UI:**
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/override_settings.volt` - Override config page

**Tests:**
- `tests/unit/test_block_page.py` - Block page rendering tests
- `tests/unit/test_override.py` - Override mechanism tests
- `tests/integration/test_override_flow.py` - End-to-end override test

## Performance Targets

- **Page Render:** <50ms to generate block page
- **Override Check:** <100ms to validate password
- **No Latency Impact:** Blocking is faster than proxying

## Testing Requirements

**Unit Tests:**
- Block page HTML rendering
- Override password validation
- Rate limiting logic
- Custom message selection

**Integration Tests:**
- Request blocked → block page displayed
- Correct password → request allowed through
- Wrong password → block page shown again
- Rate limit → lockout after N attempts
- Emergency override → all policies bypassed

**Security Tests:**
- Password stored as hash, not plaintext
- Override attempts logged
- Rate limiting prevents brute force
- Emergency override requires admin auth

## Verification Commands

### From Worker Branch (cz2/feat/block-page)

```bash
# Test block page rendering
python3 -c "
from python.yori.block_page import render_block_page
from python.yori.enforcement import EnforcementDecision
from datetime import datetime

decision = EnforcementDecision(
    should_block=True,
    policy_name='bedtime.rego',
    reason='LLM access not allowed after 21:00',
    timestamp=datetime.now(),
    allow_override=True
)

html = render_block_page(decision)
print(html[:200])  # First 200 chars
"

# Test override password
python3 -c "
from python.yori.override import validate_override_password

# Hash of 'test123'
password_hash = 'sha256:...'
is_valid = validate_override_password('test123', password_hash)
print(f'Password valid: {is_valid}')
"

# Verify templates exist
ls -la python/yori/templates/block_page.html
ls -la python/yori/templates/override_form.html
```

### Integration Test

```bash
# Start YORI in enforcement mode
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &

# Send request that should be blocked
response=$(curl -s -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}')

# Verify block page returned
echo "$response" | grep "Request Blocked by YORI"
# Expected: Block page HTML

# Test override with correct password
response=$(curl -s -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-YORI-Override: test123" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}')

# Expected: Request forwarded to OpenAI (or mock), not blocked
```

### Block Page Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Request Blocked - YORI</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; }
        .warning { color: #d32f2f; font-size: 48px; }
        .reason { background: #f5f5f5; padding: 15px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="warning">🚫</div>
    <h1>Request Blocked by YORI</h1>

    <div class="reason">
        <strong>Policy:</strong> bedtime.rego<br>
        <strong>Reason:</strong> LLM access not allowed after 21:00<br>
        <strong>Time:</strong> 2026-01-20 22:15:43
    </div>

    <p>Your request to the LLM was blocked by a network policy.</p>

    <h3>Override This Block</h3>
    <form method="POST" action="/override">
        <input type="password" name="password" placeholder="Override password">
        <input type="hidden" name="request_id" value="...">
        <button type="submit">Override</button>
    </form>

    <p><small>If you believe this is an error, contact your network administrator.</small></p>
</body>
</html>
```

### Handoff Verification for Worker 12 (enhanced-audit)

Worker 12 should be able to:
```bash
# Query override attempts from audit database
sqlite3 /var/db/yori/audit.db "
SELECT
    timestamp,
    client_ip,
    policy_name,
    event_type
FROM audit_events
WHERE event_type IN ('override_attempt', 'override_success', 'override_failed')
ORDER BY timestamp DESC
LIMIT 10;
"

# Expected: Log of override events
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Block page HTML template created (friendly, informative)
- [ ] Block page rendering functional in proxy
- [ ] Override mechanism implemented (password auth)
- [ ] Override password stored as hash (security)
- [ ] Override attempts logged (audit trail)
- [ ] Rate limiting on override attempts (3 per minute)
- [ ] Custom block messages per policy
- [ ] Emergency override option (admin only)
- [ ] All unit tests passing
- [ ] Integration tests demonstrate override flow
- [ ] Block page displays correctly in browser
- [ ] Performance target met (<50ms render, <100ms override check)
- [ ] Code committed to branch cz2/feat/block-page
- [ ] Ready for Worker 12 (enhanced-audit) integration
