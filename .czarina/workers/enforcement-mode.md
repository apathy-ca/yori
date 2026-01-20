# Worker Identity: enforcement-mode

**Role:** Code
**Agent:** Claude
**Branch:** cz2/feat/enforcement-mode
**Phase:** 2
**Dependencies:** None (builds on Phase 1 foundation)

## Mission

Implement enforcement mode that allows YORI to actually block LLM requests based on policies. This is an opt-in feature requiring explicit user consent, with clear warnings about breaking functionality and per-policy enforcement controls.

## 🚀 YOUR FIRST ACTION

Read Phase 1 policy engine code (cz1/feat/policy-engine), understand current policy evaluation flow, and add enforcement mode configuration to yori.conf with explicit consent flag.

## Dependencies from Phase 1

### From rust-foundation (Phase 1, Worker 1)
- Policy evaluation engine (`yori_core.evaluate_policy`)
- PolicyResult data structure

### From python-proxy (Phase 1, Worker 2)
- Proxy request interception (`python/yori/proxy.py`)
- Configuration system (`python/yori/config.py`)
- Request routing logic

### From policy-engine (Phase 1, Worker 5)
- Policy evaluation integration
- Alert system
- Policy templates

**Verification Before Starting:**
```bash
# Verify Phase 1 policy evaluation works
python3 -c "
from yori_core import evaluate_policy
result = evaluate_policy({'method': 'POST'}, 'policies/bedtime.rego')
print(f'Current action: {result.action}')  # Should be 'allow' or 'alert'
"
```

## Objectives

1. Add enforcement mode configuration to yori.conf
2. Implement explicit user consent requirement (checkbox + warning)
3. Create per-policy enforcement toggles (allow/alert/block per policy)
4. Add mode switching UI (observe → advisory → enforce)
5. Implement block logic in proxy (return error instead of forwarding)
6. Add enforcement mode indicator to dashboard
7. Create warning system for enabling enforcement
8. Implement safe defaults (enforcement disabled by default)
9. Add audit logging for mode changes
10. Write unit tests for enforcement logic

## Interface Contract

### Exports for block-page (Worker 10)

**Block Decision:**
```python
# In python/yori/proxy.py
class EnforcementDecision:
    should_block: bool
    policy_name: str
    reason: str
    timestamp: datetime
    allow_override: bool
```

**Configuration:**
```yaml
# yori.conf
mode: enforce  # observe | advisory | enforce

enforcement:
  enabled: false  # Requires explicit consent
  consent_accepted: false  # User must check this box

policies:
  bedtime:
    enabled: true
    action: block  # allow | alert | block
  privacy:
    enabled: true
    action: alert  # Just alert, don't block
```

### Exports for allowlist-blocklist (Worker 11)

**Enforcement Check Interface:**
```python
# python/yori/enforcement.py
def should_enforce_policy(
    request: dict,
    policy_result: PolicyResult,
    client_ip: str
) -> EnforcementDecision:
    """
    Determines if request should be blocked.
    Worker 11 will add allowlist checks here.
    """
    pass
```

### Exports for enhanced-audit (Worker 12)

**Audit Events:**
```python
# New audit event types
- 'enforcement_enabled'   # User enabled enforcement mode
- 'enforcement_disabled'  # User disabled enforcement
- 'request_blocked'       # Request blocked by policy
- 'block_overridden'      # User overrode a block
```

## Files to Create

**Python Core:**
- `python/yori/enforcement.py` - Enforcement logic and decision engine
- `python/yori/consent.py` - User consent validation

**Configuration:**
- Update `yori.conf.example` with enforcement section
- Add enforcement schema to `python/yori/models.py`

**Proxy Integration:**
- Update `python/yori/proxy.py` - Add block logic to request handler

**OPNsense UI:**
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/enforcement.volt` - Enforcement settings page
- `opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/Api/EnforcementController.php` - API

**Tests:**
- `tests/unit/test_enforcement.py` - Enforcement logic tests
- `tests/integration/test_blocking.py` - End-to-end blocking tests

## Performance Targets

- **Block Decision:** <1ms (deny fast, faster than forwarding)
- **Latency Impact:** No additional latency beyond Phase 1 (<10ms total)
- **Memory:** No significant increase (<256MB total still)

## Testing Requirements

**Unit Tests:**
- Enforcement decision logic
- Consent validation
- Mode switching
- Per-policy action selection

**Integration Tests:**
- Request blocking end-to-end
- Mode switching (observe → enforce → observe)
- Consent requirement (can't enable without consent)
- Per-policy enforcement (one policy blocks, another alerts)

**Safety Tests:**
- Enforcement disabled by default
- Cannot enable without consent
- Mode changes logged
- Emergency disable works

## Verification Commands

### From Worker Branch (cz2/feat/enforcement-mode)

```bash
# Test enforcement configuration
cat yori.conf.example | grep -A 10 "enforcement:"

# Test enforcement logic
python3 -c "
from python.yori.enforcement import should_enforce_policy
from yori_core import PolicyResult

result = PolicyResult(action='block', reason='Bedtime policy')
decision = should_enforce_policy(
    request={'method': 'POST'},
    policy_result=result,
    client_ip='192.168.1.100'
)
print(f'Should block: {decision.should_block}')
"

# Test consent requirement
python3 -c "
from python.yori.config import load_config
config = load_config('yori.conf.example')
assert config.enforcement.enabled == False  # Disabled by default
assert config.enforcement.consent_accepted == False  # No consent
"

# Verify UI exists
ls -la opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/enforcement.volt
```

### Integration Test

```bash
# Start YORI in enforcement mode
# Edit yori.conf:
#   mode: enforce
#   enforcement.enabled: true
#   enforcement.consent_accepted: true
#   policies.bedtime.action: block

uvicorn yori.main:app --host 127.0.0.1 --port 8443 &

# Send request that should be blocked
curl -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# Expected: HTTP 403 or similar, request NOT forwarded to OpenAI
```

### Handoff Verification for Worker 10 (block-page)

Worker 10 should be able to:
```bash
# Access EnforcementDecision from blocked requests
# File: python/yori/enforcement.py
from python.yori.enforcement import should_enforce_policy

# Use decision to render block page
decision.policy_name  # "bedtime.rego"
decision.reason       # "LLM access not allowed after 21:00"
decision.timestamp    # "2026-01-20 22:15:43"
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Enforcement mode configuration added to yori.conf
- [ ] Explicit consent requirement implemented (checkbox + warning)
- [ ] Per-policy enforcement toggles working (allow/alert/block)
- [ ] Mode switching UI implemented (observe/advisory/enforce)
- [ ] Block logic functional in proxy (requests actually blocked)
- [ ] Enforcement disabled by default (safe defaults)
- [ ] Cannot enable without consent checkbox
- [ ] Mode changes logged to audit
- [ ] Enforcement indicator on dashboard
- [ ] All unit tests passing
- [ ] Integration tests demonstrate blocking
- [ ] Performance target met (<1ms block decision)
- [ ] Code committed to branch cz2/feat/enforcement-mode
- [ ] Ready for Worker 10 (block-page) integration
