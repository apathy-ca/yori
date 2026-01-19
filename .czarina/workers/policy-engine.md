# Worker Identity: policy-engine

**Role:** Code
**Agent:** Claude
**Branch:** cz1/feat/policy-engine
**Phase:** 1
**Dependencies:** rust-foundation, python-proxy

## Mission

Integrate sark-opa policy engine for Rego evaluation, create policy editor UI, implement advisory alerts (email, web, push), and build pre-packaged policy templates.

## 🚀 YOUR FIRST ACTION

Review sark-opa Rust crate API, implement Rust policy evaluation wrapper in yori-core, and create Python interface for loading .rego files from /usr/local/etc/yori/policies/.

## Objectives

1. Integrate sark-opa in Rust core (load .rego, evaluate policies)
2. Create policy evaluation pipeline in Python proxy
3. Implement advisory alert system:

## Deliverables

Complete implementation of: Integrate sark-opa policy engine for Rego evaluation, create policy editor UI, implement advisory alerts

## Dependencies from Upstream Workers

### From rust-foundation (Worker 1)

**Required Artifacts:**
- `yori_core` module with policy evaluation functions
- `yori_core.evaluate_policy(request: dict, policy_path: str) -> PolicyResult`
- Rego file loader and validator

### From python-proxy (Worker 2)

**Required Artifacts:**
- Proxy integration points in `python/yori/proxy.py`
- Policy result handling (allow/alert/block actions)
- Configuration system for policy paths

**Verification Before Starting:**
```bash
# Verify policy evaluation works
python3 -c "
import yori_core
result = yori_core.evaluate_policy(
    {'method': 'POST', 'path': '/v1/chat'},
    'policies/test.rego'
)
print(result)
"
```

## Interface Contract

### Exports for documentation (Worker 6)

**Policy Features to Document:**
- 4+ pre-built policy templates with examples
- Policy editor UI usage
- Alert configuration (email, web, push)
- Policy testing/dry-run feature
- Policy cookbook with 10+ examples

### Exports for testing-qa (Worker 7)

**Testable Components:**
- Policy evaluation accuracy
- Alert delivery mechanisms
- Policy template functionality
- Performance (policy eval <5ms)

## Files to Create

**Rego Policy Templates:**
- `policies/home_default.rego` - Default allow-all policy
- `policies/bedtime.rego` - Time-based alerts (LLM use after 21:00)
- `policies/high_usage.rego` - Threshold alerts (>50 requests/day)
- `policies/privacy.rego` - PII detection in prompts
- `policies/homework_helper.rego` - Educational keyword detection

**Python Integration:**
- `python/yori/policy.py` - Policy evaluation wrapper
- `python/yori/alerts.py` - Alert system (email, web, push)
- `python/yori/policy_loader.py` - Load/validate Rego files

**OPNsense UI:**
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/policies.volt` - Policy editor page
- `opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/Api/PolicyController.php` - Policy API

**Configuration:**
- Alert configuration in `yori.conf` (SMTP, Pushover, Gotify settings)

## Performance Targets

- **Policy Evaluation:** <5ms per request (p95)
- **Alert Delivery:** <1 second for web alerts, <10 seconds for email
- **Policy Load Time:** <100ms to load all policies on startup

## Testing Requirements

**Unit Tests:**
- Policy evaluation with test Rego files
- Alert delivery (mocked SMTP, etc.)
- Policy validation (syntax checking)

**Integration Tests:**
- End-to-end: Request → policy check → alert trigger
- Test all 4+ policy templates
- Alert delivery to all channels (email, web, push)

**Performance Tests:**
- Policy evaluation latency <5ms
- Load test with policies enabled

## Verification Commands

### From Worker Branch (cz1/feat/policy-engine)

```bash
# Test policy evaluation
python3 -c "
from python.yori.policy import evaluate_request
result = evaluate_request({'method': 'POST'}, 'policies/bedtime.rego')
print(f'Action: {result.action}, Reason: {result.reason}')
"

# Verify all policy templates
for policy in policies/*.rego; do
    echo "Testing $policy"
    python3 -c "from yori_core import evaluate_policy; \
                evaluate_policy({}, '$policy')"
done

# Test alert system
python3 -c "
from python.yori.alerts import send_alert
send_alert('Test alert', 'email')  # Should send test email
"

# Verify policy editor UI
ls -la opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/policies.volt
```

### Integration Test

```bash
# Generate test traffic that should trigger bedtime policy
# (after 21:00)
curl -X POST http://localhost:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# Verify alert was logged
sqlite3 /var/db/yori/audit.db \
  "SELECT * FROM audit_events WHERE policy_result = 'alert';"

# Check web UI for alert notification
# Navigate to OPNsense → YORI → Dashboard
# Expected: Alert displayed in "Recent Alerts" widget
```

### Handoff Verification for Worker 6

Worker 6 should be able to:
```bash
# Document all 4+ policy templates
cat policies/bedtime.rego      # Time-based example
cat policies/high_usage.rego   # Threshold example
cat policies/privacy.rego      # PII detection example

# Take screenshots of policy editor UI
# Document alert configuration options
```

### Handoff Verification for Worker 7

Worker 7 should be able to:
```bash
# Run policy evaluation performance tests
python3 tests/test_policy_performance.py
# Expected: <5ms per evaluation

# Test all alert delivery mechanisms
pytest tests/test_alerts.py -v
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Dependencies verified (yori_core policy functions, proxy integration)
- [ ] sark-opa integrated in Rust core
- [ ] Policy evaluation pipeline works in Python proxy
- [ ] Advisory alert system functional (email, web, push)
- [ ] At least 4 pre-built policy templates included and tested
- [ ] Policy editor UI implemented in OPNsense plugin
- [ ] Policy testing/dry-run feature works
- [ ] Alert configuration in yori.conf
- [ ] Performance targets met (<5ms policy eval)
- [ ] All unit and integration tests passing
- [ ] Code committed to branch cz1/feat/policy-engine
- [ ] Policy documentation ready for Worker 6 (POLICY_GUIDE.md outline)
