# YORI v0.2.0 Quick Test Guide

**For the impatient:** Run these tests in 15 minutes to verify core functionality.

---

## Setup (2 minutes)

```bash
# 1. Install YORI
cd ~/Source/yori
pip install -e .

# 2. Create test directory
mkdir -p /tmp/yori-quick-test

# 3. Start Python REPL
python3
```

---

## Quick Tests (Run in Python REPL)

### Test 1: Imports Work (30 seconds)

```python
# Test all imports
import yori
from yori.config import YoriConfig
from yori.enforcement import EnforcementEngine
from yori.consent import validate_enforcement_config
from yori.allowlist import is_allowlisted, add_device
from yori.emergency import activate_emergency_override
from yori.block_page import render_block_page
from yori.models import *

print("✅ All imports successful!")
```

**Expected:** No errors

---

### Test 2: Configuration Loads (1 minute)

```python
from yori.config import YoriConfig

# Test default config
config = YoriConfig()
print(f"Mode: {config.mode}")
print(f"Endpoints: {len(config.endpoints)}")
print(f"Enforcement enabled: {config.enforcement.enabled}")

assert config.mode == "observe"
assert len(config.endpoints) == 4
assert config.enforcement.enabled == False

print("✅ Configuration works!")
```

**Expected:** Shows observe mode with 4 endpoints

---

### Test 3: Consent Validation (1 minute)

```python
from yori.config import YoriConfig, EnforcementConfig
from yori.consent import validate_enforcement_config

# Test 1: Observe mode needs no consent
config1 = YoriConfig(mode="observe")
errors = validate_enforcement_config(config1)
assert len(errors) == 0
print("✅ Observe mode: No consent needed")

# Test 2: Enforce mode needs consent
config2 = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=False)
)
errors = validate_enforcement_config(config2)
assert len(errors) > 0
print("✅ Enforce mode: Consent required (validated)")

# Test 3: Full enforcement works
config3 = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True)
)
errors = validate_enforcement_config(config3)
assert len(errors) == 0
print("✅ Full enforcement: Validated!")
```

**Expected:** All 3 tests pass

---

### Test 4: Allowlist System (2 minutes)

```python
from yori.config import YoriConfig
from yori.models import AllowlistDevice
from yori.allowlist import add_device, is_allowlisted

config = YoriConfig()

# Add a device
device = AllowlistDevice(
    ip="192.168.1.100",
    name="test-laptop",
    mac="aa:bb:cc:dd:ee:ff",
    enabled=True
)
add_device(device, config)

# Check if it's allowlisted
is_allowed, found = is_allowlisted("192.168.1.100", config)
assert is_allowed == True
assert found.name == "test-laptop"
print(f"✅ Allowlist works! Device: {found.name}")

# Check device NOT on allowlist
is_allowed, found = is_allowlisted("192.168.1.200", config)
assert is_allowed == False
print("✅ Non-allowlisted device rejected")
```

**Expected:** Allowlist add/check works

---

### Test 5: Time Exceptions (2 minutes)

```python
from yori.models import TimeException
from yori.time_exceptions import is_exception_active
from datetime import datetime

# Create exception for all day today
now = datetime.now()
current_day = now.strftime("%A").lower()

exception = TimeException(
    name="all-day-test",
    days=[current_day],
    start_time="00:00",
    end_time="23:59",
    device_ips=["192.168.1.100"],
    enabled=True
)

# Should be active right now
active = is_exception_active(exception, "192.168.1.100", now)
assert active == True
print(f"✅ Time exception active on {current_day}")

# Wrong device should not match
active = is_exception_active(exception, "192.168.1.200", now)
assert active == False
print("✅ Time exception device filtering works")
```

**Expected:** Exception active for right device/time

---

### Test 6: Emergency Override (2 minutes)

```python
from yori.config import YoriConfig
from yori.emergency import activate_emergency_override, is_emergency_override_active, deactivate_emergency_override

config = YoriConfig()

# Check not active initially
assert is_emergency_override_active(config) == False
print("✅ Emergency override off by default")

# Activate it
activate_emergency_override(config, "admin123", "192.168.1.1")
assert is_emergency_override_active(config) == True
assert config.enforcement.emergency_override.activated_by == "192.168.1.1"
print("✅ Emergency override activated!")

# Deactivate it
deactivate_emergency_override(config)
assert is_emergency_override_active(config) == False
print("✅ Emergency override deactivated")
```

**Expected:** Override toggles correctly

---

### Test 7: Enforcement Engine (3 minutes)

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig, EnforcementConfig, PolicyConfig, PolicyFileConfig
from yori.models import PolicyResult

# Test 1: Enforcement disabled by default
config1 = YoriConfig()
engine1 = EnforcementEngine(config1)
assert engine1._is_enforcement_enabled() == False
print("✅ Enforcement disabled by default")

# Test 2: Enforcement enabled when configured
config2 = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True)
)
engine2 = EnforcementEngine(config2)
assert engine2._is_enforcement_enabled() == True
print("✅ Enforcement enables when configured")

# Test 3: Block action actually blocks
config3 = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
    policies=PolicyConfig(
        files={"test": PolicyFileConfig(enabled=True, action="block")}
    )
)
engine3 = EnforcementEngine(config3)
policy_result = PolicyResult(action="alert", policy_name="test.rego", reason="Test")
decision = engine3.should_enforce_policy(
    request={},
    policy_result=policy_result,
    client_ip="192.168.1.100"
)
assert decision.should_block == True
assert decision.action_taken == "block"
print("✅ Block action blocks requests")

# Test 4: Alert action doesn't block
config4 = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
    policies=PolicyConfig(
        files={"test": PolicyFileConfig(enabled=True, action="alert")}
    )
)
engine4 = EnforcementEngine(config4)
decision = engine4.should_enforce_policy(
    request={},
    policy_result=policy_result,
    client_ip="192.168.1.100"
)
assert decision.should_block == False
assert decision.action_taken == "alert"
print("✅ Alert action doesn't block")
```

**Expected:** All enforcement logic works

---

### Test 8: Block Page Rendering (2 minutes)

```python
from yori.models import BlockDecision
from yori.block_page import render_block_page
from datetime import datetime

# Create a block decision
decision = BlockDecision(
    should_block=True,
    policy_name="bedtime.rego",
    reason="LLM access not allowed after 21:00",
    timestamp=datetime.now(),
    request_id="test-123",
    allow_override=True
)

# Render it
html = render_block_page(decision)

# Verify content
assert "blocked" in html.lower() or "block" in html.lower()
assert "bedtime.rego" in html
assert "test-123" in html
assert len(html) > 500  # Substantial HTML
print("✅ Block page renders")
print(f"   HTML length: {len(html)} chars")

# Check for override form
assert "password" in html.lower()
print("✅ Override form included")
```

**Expected:** HTML block page generated

---

### Test 9: Audit Logging (2 minutes)

```python
from yori.audit_enforcement import EnforcementAuditLogger
import os

# Create test database
db_path = "/tmp/yori-quick-test/audit.db"
if os.path.exists(db_path):
    os.remove(db_path)

logger = EnforcementAuditLogger(db_path)
logger.initialize_db()
assert os.path.exists(db_path)
print("✅ Audit database created")

# Log a block event
event_id = logger.log_block_event(
    client_ip="192.168.1.100",
    policy_name="test.rego",
    reason="Test block",
    endpoint="api.openai.com"
)
assert event_id is not None
print(f"✅ Block event logged (ID: {event_id})")

# Log an override attempt
event_id = logger.log_override_attempt(
    client_ip="192.168.1.100",
    policy_name="test.rego",
    success=False,
    reason="Wrong password"
)
assert event_id is not None
print(f"✅ Override attempt logged (ID: {event_id})")

# Get recent events
events = logger.get_recent_events(limit=10)
assert len(events) >= 2
print(f"✅ Retrieved {len(events)} audit events")

# Get statistics
stats = logger.get_enforcement_stats()
assert stats["total_blocks"] >= 1
assert stats["total_overrides"] >= 1
print(f"✅ Statistics: {stats['total_blocks']} blocks, {stats['total_overrides']} overrides")
```

**Expected:** Audit logging works

---

### Test 10: Rust Integration (1 minute)

```python
import yori._core

# Check module metadata
print(f"Module: {yori._core}")
print(f"Version: {yori._core.__version__}")
print(f"Author: {yori._core.__author__}")

# Test PolicyEngine (stub)
engine = yori._core.PolicyEngine("/tmp/test")
policies = engine.list_policies()
print(f"PolicyEngine policies: {policies}")
result = engine.evaluate({"user": "alice"})
print(f"PolicyEngine evaluate: {result}")

# Test Cache (stub)
cache = yori._core.Cache(1000, 300)
cache.set("test", {"data": "value"})
value = cache.get("test")
stats = cache.stats()
print(f"Cache stats: {stats}")

print("✅ Rust/PyO3 integration works (stubs functional)")
```

**Expected:** Rust module imports and stubs work

---

## Exit Python and Cleanup

```python
exit()
```

```bash
# Clean up test data
rm -rf /tmp/yori-quick-test
```

---

## Summary Checklist

After running all 10 tests, you should see:

- ✅ All imports work
- ✅ Configuration loads
- ✅ Consent validation works
- ✅ Allowlist add/check works
- ✅ Time exceptions work
- ✅ Emergency override toggles
- ✅ Enforcement engine enforces
- ✅ Block page renders
- ✅ Audit logging works
- ✅ Rust integration works

---

## If All Tests Pass

**🎉 v0.2.0 core functionality is validated!**

Next steps:
1. Try the full manual test plan (MANUAL_TEST_PLAN.md)
2. Test with actual HTTP proxy server
3. Create test policies and test enforcement
4. Prepare for FreeBSD/OPNsense deployment

---

## If Tests Fail

1. Check error messages carefully
2. Verify package installation: `pip list | grep yori`
3. Check for import errors: `python -c "import yori"`
4. Review SESSION_SUMMARY.md for known issues
5. Report issues with full error output

---

## Quick Reference

- **Full manual test plan:** MANUAL_TEST_PLAN.md (48 tests, ~2.5 hours)
- **Test status report:** V0.2.0_TEST_STATUS.md
- **Fix summary:** TEST_FIX_SUMMARY.md
- **Session summary:** SESSION_SUMMARY.md
- **SARK status:** SARK_DEPENDENCY_STATUS.md
