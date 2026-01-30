# YORI v0.2.0 Manual Test Plan

**Version:** 0.2.0 (Enforcement Mode)
**Date:** 2026-01-27
**Platform:** Linux development environment
**Estimated Time:** 2-3 hours

---

## Prerequisites

### Environment Setup

```bash
# 1. Ensure package is installed
cd ~/Source/yori
pip install -e .

# 2. Verify installation
python -c "import yori; import yori._core; print('✅ YORI installed')"

# 3. Create test directories
mkdir -p /tmp/yori-test/{policies,data}

# 4. Verify SQLite available
sqlite3 --version
```

### Test Data Preparation

Create test configuration file:

```bash
cat > /tmp/yori-test/test_config.yaml << 'EOF'
mode: observe
listen: 0.0.0.0:8443

endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true

audit:
  database: /tmp/yori-test/data/audit.db
  retention_days: 365

policies:
  directory: /tmp/yori-test/policies
  default: home_default.rego
  files:
    bedtime:
      enabled: true
      action: alert
    test_policy:
      enabled: true
      action: block

enforcement:
  enabled: false
  consent_accepted: false
  allowlist:
    devices:
      - ip: "192.168.1.100"
        name: "test-device-1"
        enabled: true
        permanent: false
      - ip: "192.168.1.101"
        name: "test-device-2"
        enabled: false
    groups:
      - name: "family"
        device_ips: ["192.168.1.100", "192.168.1.102"]
        enabled: true
    time_exceptions:
      - name: "homework_hours"
        days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
        start_time: "15:00"
        end_time: "18:00"
        device_ips: ["192.168.1.100"]
        enabled: true
  emergency_override:
    enabled: false
    require_password: true
EOF
```

---

## Test Suite Overview

| Phase | Category | Tests | Duration |
|-------|----------|-------|----------|
| 1 | Configuration Loading | 5 | 10 min |
| 2 | Consent Validation | 6 | 15 min |
| 3 | Allowlist System | 8 | 20 min |
| 4 | Time Exceptions | 6 | 15 min |
| 5 | Emergency Override | 5 | 15 min |
| 6 | Enforcement Engine | 7 | 20 min |
| 7 | Block Page Rendering | 5 | 15 min |
| 8 | Audit Logging | 6 | 20 min |
| **Total** | | **48 tests** | **~2.5 hours** |

---

## Phase 1: Configuration Loading

### Test 1.1: Load Default Configuration

**Objective:** Verify YORI can create default configuration

```python
from yori.config import YoriConfig

# Load defaults
config = YoriConfig()

# Verify defaults
assert config.mode == "observe"
assert config.listen == "0.0.0.0:8443"
assert len(config.endpoints) == 4
assert config.enforcement.enabled == False
print("✅ Test 1.1 PASS: Default configuration loads")
```

**Expected:** Default configuration created with observe mode

### Test 1.2: Load from YAML File

**Objective:** Verify configuration loads from YAML

```python
from yori.config import YoriConfig
from pathlib import Path

# Load from file
config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Verify values
assert config.mode == "observe"
assert config.audit.database == Path("/tmp/yori-test/data/audit.db")
assert len(config.enforcement.allowlist.devices) == 2
print("✅ Test 1.2 PASS: YAML configuration loads correctly")
```

**Expected:** All YAML values loaded correctly

### Test 1.3: Verify Enforcement Config

**Objective:** Verify enforcement configuration structure

```python
from yori.config import YoriConfig
from pathlib import Path

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Check enforcement settings
assert config.enforcement is not None
assert config.enforcement.enabled == False
assert config.enforcement.consent_accepted == False

# Check allowlist
assert len(config.enforcement.allowlist.devices) == 2
assert config.enforcement.allowlist.devices[0].ip == "192.168.1.100"
assert config.enforcement.allowlist.devices[0].name == "test-device-1"

print("✅ Test 1.3 PASS: Enforcement configuration valid")
```

**Expected:** Enforcement structure matches YAML

### Test 1.4: Verify Time Exceptions

**Objective:** Verify time exception configuration

```python
from yori.config import YoriConfig
from pathlib import Path

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Check time exceptions
exceptions = config.enforcement.allowlist.time_exceptions
assert len(exceptions) == 1
assert exceptions[0].name == "homework_hours"
assert exceptions[0].start_time == "15:00"
assert exceptions[0].end_time == "18:00"
assert "monday" in exceptions[0].days

print("✅ Test 1.4 PASS: Time exceptions configured")
```

**Expected:** Time exception loaded correctly

### Test 1.5: Verify Policy Configuration

**Objective:** Verify per-policy action settings

```python
from yori.config import YoriConfig
from pathlib import Path

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Check policy files config
assert config.policies.files is not None
assert "bedtime" in config.policies.files
assert config.policies.files["bedtime"].action == "alert"
assert config.policies.files["test_policy"].action == "block"

print("✅ Test 1.5 PASS: Policy configuration valid")
```

**Expected:** Policy actions configured correctly

---

## Phase 2: Consent Validation

### Test 2.1: Observe Mode Requires No Consent

**Objective:** Verify observe mode works without consent

```python
from yori.config import YoriConfig
from yori.consent import validate_enforcement_config

config = YoriConfig(mode="observe")
errors = validate_enforcement_config(config)

assert len(errors) == 0
print("✅ Test 2.1 PASS: Observe mode requires no consent")
```

**Expected:** No validation errors

### Test 2.2: Enforcement Requires Mode=Enforce

**Objective:** Verify enforcement.enabled without mode fails

```python
from yori.config import YoriConfig, EnforcementConfig
from yori.consent import validate_enforcement_config

config = YoriConfig(
    mode="observe",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True)
)
errors = validate_enforcement_config(config)

assert len(errors) > 0
assert any("mode must be 'enforce'" in str(e) for e in errors)
print("✅ Test 2.2 PASS: Mode mismatch detected")
```

**Expected:** Error about mode mismatch

### Test 2.3: Enforcement Requires Consent

**Objective:** Verify enforcement without consent fails

```python
from yori.config import YoriConfig, EnforcementConfig
from yori.consent import validate_enforcement_config

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=False)
)
errors = validate_enforcement_config(config)

assert len(errors) > 0
assert any("consent" in str(e).lower() for e in errors)
print("✅ Test 2.3 PASS: Missing consent detected")
```

**Expected:** Error about missing consent

### Test 2.4: Valid Enforcement Configuration

**Objective:** Verify correct enforcement config passes

```python
from yori.config import YoriConfig, EnforcementConfig
from yori.consent import validate_enforcement_config

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True)
)
errors = validate_enforcement_config(config)

assert len(errors) == 0
print("✅ Test 2.4 PASS: Valid enforcement configuration")
```

**Expected:** No validation errors

### Test 2.5: Get Consent Warning Message

**Objective:** Verify warning message generation

```python
from yori.consent import get_consent_warning

warning = get_consent_warning()

assert "explicit consent" in warning.lower()
assert "blocking" in warning.lower() or "block" in warning.lower()
assert len(warning) > 100  # Substantial warning
print("✅ Test 2.5 PASS: Consent warning generated")
```

**Expected:** Warning message contains key information

### Test 2.6: Mode Enforcement Warning

**Objective:** Verify mode-specific warnings

```python
from yori.config import YoriConfig
from yori.consent import get_mode_warning

config = YoriConfig(mode="enforce")
warning = get_mode_warning(config)

assert warning is not None
assert "enforce" in warning.lower()
print("✅ Test 2.6 PASS: Mode warning generated")
```

**Expected:** Enforcement mode triggers warning

---

## Phase 3: Allowlist System

### Test 3.1: Device Allowlist Check - IP Match

**Objective:** Verify device found by IP

```python
from yori.config import YoriConfig
from yori.allowlist import is_allowlisted
from pathlib import Path

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Check allowlisted IP
is_allowed, device = is_allowlisted("192.168.1.100", config)

assert is_allowed == True
assert device is not None
assert device.name == "test-device-1"
print("✅ Test 3.1 PASS: IP allowlist match")
```

**Expected:** Device found and matched

### Test 3.2: Device Not on Allowlist

**Objective:** Verify non-allowlisted device rejected

```python
from yori.config import YoriConfig
from yori.allowlist import is_allowlisted
from pathlib import Path

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Check non-allowlisted IP
is_allowed, device = is_allowlisted("192.168.1.200", config)

assert is_allowed == False
assert device is None
print("✅ Test 3.2 PASS: Non-allowlisted IP rejected")
```

**Expected:** Device not found

### Test 3.3: Disabled Device Not Allowed

**Objective:** Verify disabled devices don't bypass

```python
from yori.config import YoriConfig
from yori.allowlist import is_allowlisted
from pathlib import Path

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Device 192.168.1.101 is disabled in config
is_allowed, device = is_allowlisted("192.168.1.101", config)

assert is_allowed == False
print("✅ Test 3.3 PASS: Disabled device rejected")
```

**Expected:** Disabled device not allowed

### Test 3.4: Add Device to Allowlist

**Objective:** Verify adding device dynamically

```python
from yori.config import YoriConfig
from yori.models import AllowlistDevice
from yori.allowlist import add_device

config = YoriConfig()

# Add new device
new_device = AllowlistDevice(
    ip="192.168.1.50",
    name="new-test-device",
    enabled=True
)
add_device(new_device, config)

# Verify added
from yori.allowlist import is_allowlisted
is_allowed, device = is_allowlisted("192.168.1.50", config)

assert is_allowed == True
assert device.name == "new-test-device"
print("✅ Test 3.4 PASS: Device added to allowlist")
```

**Expected:** Device added and found

### Test 3.5: Remove Device from Allowlist

**Objective:** Verify removing device

```python
from yori.config import YoriConfig
from yori.models import AllowlistDevice
from yori.allowlist import add_device, remove_device, is_allowlisted

config = YoriConfig()

# Add and remove
device = AllowlistDevice(ip="192.168.1.99", name="temp", enabled=True)
add_device(device, config)
remove_device("192.168.1.99", config)

# Verify removed
is_allowed, _ = is_allowlisted("192.168.1.99", config)
assert is_allowed == False
print("✅ Test 3.5 PASS: Device removed from allowlist")
```

**Expected:** Device no longer on allowlist

### Test 3.6: Temporary Allowlist with Expiration

**Objective:** Verify expired devices not allowed

```python
from yori.config import YoriConfig
from yori.models import AllowlistDevice
from yori.allowlist import add_device, is_allowlisted
from datetime import datetime, timedelta

config = YoriConfig()

# Add expired device
expired_device = AllowlistDevice(
    ip="192.168.1.88",
    name="expired",
    enabled=True,
    expires_at=datetime.now() - timedelta(hours=1)  # Expired 1 hour ago
)
add_device(expired_device, config)

# Check if allowed (should be false due to expiration)
is_allowed, _ = is_allowlisted("192.168.1.88", config)
assert is_allowed == False
print("✅ Test 3.6 PASS: Expired device rejected")
```

**Expected:** Expired device not allowed

### Test 3.7: MAC Address Matching

**Objective:** Verify MAC address allowlist

```python
from yori.config import YoriConfig
from yori.models import AllowlistDevice
from yori.allowlist import add_device, is_allowlisted

config = YoriConfig()

# Add device with MAC
device = AllowlistDevice(
    ip="192.168.1.77",
    name="mac-device",
    mac="aa:bb:cc:dd:ee:ff",
    enabled=True
)
add_device(device, config)

# Check with MAC
is_allowed, found = is_allowlisted(
    "192.168.1.77",
    config,
    client_mac="aa:bb:cc:dd:ee:ff"
)

assert is_allowed == True
assert found.mac == "aa:bb:cc:dd:ee:ff"
print("✅ Test 3.7 PASS: MAC address matched")
```

**Expected:** Device matched by MAC

### Test 3.8: Get Allowlist Statistics

**Objective:** Verify statistics generation

```python
from yori.config import YoriConfig
from pathlib import Path
from yori.allowlist import get_allowlist_stats

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))
stats = get_allowlist_stats(config)

assert stats["total_devices"] >= 2
assert stats["enabled_devices"] >= 1
assert "groups" in stats
print("✅ Test 3.8 PASS: Allowlist statistics generated")
```

**Expected:** Statistics show device counts

---

## Phase 4: Time Exceptions

### Test 4.1: Time Exception Active During Range

**Objective:** Verify time exception activates correctly

```python
from yori.config import YoriConfig
from yori.models import TimeException
from yori.time_exceptions import is_exception_active
from datetime import datetime

config = YoriConfig()

# Create exception for current day, wide time range
now = datetime.now()
current_day = now.strftime("%A").lower()

exception = TimeException(
    name="test-exception",
    days=[current_day],
    start_time="00:00",
    end_time="23:59",
    device_ips=["192.168.1.100"],
    enabled=True
)

# Check if active
active = is_exception_active(exception, "192.168.1.100", now)
assert active == True
print("✅ Test 4.1 PASS: Time exception active in range")
```

**Expected:** Exception active during time range

### Test 4.2: Time Exception Inactive Outside Range

**Objective:** Verify time exception doesn't activate outside range

```python
from yori.models import TimeException
from yori.time_exceptions import is_exception_active
from datetime import datetime, time

exception = TimeException(
    name="morning-only",
    days=["monday", "tuesday", "wednesday", "thursday", "friday"],
    start_time="06:00",
    end_time="09:00",
    device_ips=["192.168.1.100"],
    enabled=True
)

# Check at noon (outside range)
test_time = datetime.now().replace(hour=12, minute=0)
active = is_exception_active(exception, "192.168.1.100", test_time)

assert active == False
print("✅ Test 4.2 PASS: Exception inactive outside range")
```

**Expected:** Exception not active outside time

### Test 4.3: Time Exception Wrong Day

**Objective:** Verify exception doesn't activate on wrong day

```python
from yori.models import TimeException
from yori.time_exceptions import is_exception_active
from datetime import datetime

exception = TimeException(
    name="weekday-only",
    days=["monday"],  # Only Monday
    start_time="00:00",
    end_time="23:59",
    device_ips=["192.168.1.100"],
    enabled=True
)

# If today is not Monday, should be inactive
now = datetime.now()
if now.strftime("%A").lower() != "monday":
    active = is_exception_active(exception, "192.168.1.100", now)
    assert active == False
    print("✅ Test 4.3 PASS: Exception inactive on wrong day")
else:
    print("⏭️ Test 4.3 SKIP: Today is Monday")
```

**Expected:** Exception not active on wrong day

### Test 4.4: Time Exception Wrong Device

**Objective:** Verify exception only applies to specified devices

```python
from yori.models import TimeException
from yori.time_exceptions import is_exception_active
from datetime import datetime

now = datetime.now()
current_day = now.strftime("%A").lower()

exception = TimeException(
    name="specific-device",
    days=[current_day],
    start_time="00:00",
    end_time="23:59",
    device_ips=["192.168.1.100"],  # Only this IP
    enabled=True
)

# Check different device
active = is_exception_active(exception, "192.168.1.200", now)
assert active == False
print("✅ Test 4.4 PASS: Exception not active for wrong device")
```

**Expected:** Exception doesn't apply to other devices

### Test 4.5: Overnight Time Range

**Objective:** Verify overnight ranges work (23:00 - 02:00)

```python
from yori.time_exceptions import _time_in_range
from datetime import time

# 23:00 - 02:00 range (crosses midnight)
result = _time_in_range(
    time(1, 0),    # 1 AM (should be in range)
    time(23, 0),   # Start: 11 PM
    time(2, 0)     # End: 2 AM
)

assert result == True
print("✅ Test 4.5 PASS: Overnight range works")
```

**Expected:** Overnight ranges calculated correctly

### Test 4.6: Check Any Exception Active

**Objective:** Verify checking multiple exceptions

```python
from yori.config import YoriConfig
from pathlib import Path
from yori.time_exceptions import check_any_exception_active

config = YoriConfig.from_yaml(Path("/tmp/yori-test/test_config.yaml"))

# Config has homework_hours exception
# Check if any exception active for device
active, exception = check_any_exception_active("192.168.1.100", config)

# May or may not be active depending on current time
# Just verify it returns properly
assert isinstance(active, bool)
if active:
    assert exception is not None
print("✅ Test 4.6 PASS: Exception check works")
```

**Expected:** Returns proper boolean and exception

---

## Phase 5: Emergency Override

### Test 5.1: Emergency Override Activation

**Objective:** Verify emergency override can be activated

```python
from yori.config import YoriConfig
from yori.emergency import activate_emergency_override

config = YoriConfig()

# Activate override
activate_emergency_override(
    config,
    admin_password="test123",
    activated_by="192.168.1.1"
)

assert config.enforcement.emergency_override.enabled == True
assert config.enforcement.emergency_override.activated_by == "192.168.1.1"
print("✅ Test 5.1 PASS: Emergency override activated")
```

**Expected:** Override activated and logged

### Test 5.2: Emergency Override Check

**Objective:** Verify override status check

```python
from yori.config import YoriConfig
from yori.emergency import activate_emergency_override, is_emergency_override_active

config = YoriConfig()
activate_emergency_override(config, "test123", "192.168.1.1")

assert is_emergency_override_active(config) == True
print("✅ Test 5.2 PASS: Override status check works")
```

**Expected:** Override detected as active

### Test 5.3: Emergency Override Deactivation

**Objective:** Verify override can be deactivated

```python
from yori.config import YoriConfig
from yori.emergency import (
    activate_emergency_override,
    deactivate_emergency_override,
    is_emergency_override_active
)

config = YoriConfig()
activate_emergency_override(config, "test123", "192.168.1.1")
deactivate_emergency_override(config)

assert is_emergency_override_active(config) == False
print("✅ Test 5.3 PASS: Override deactivated")
```

**Expected:** Override disabled

### Test 5.4: Password Validation

**Objective:** Verify password checking works

```python
from yori.emergency import validate_emergency_password
import hashlib

# Hash a test password
test_password = "secure123"
password_hash = hashlib.sha256(test_password.encode()).hexdigest()

# Validate correct password
assert validate_emergency_password("secure123", password_hash) == True

# Validate incorrect password
assert validate_emergency_password("wrong", password_hash) == False
print("✅ Test 5.4 PASS: Password validation works")
```

**Expected:** Password correctly validated

### Test 5.5: Emergency Override Bypasses Enforcement

**Objective:** Verify override bypasses all enforcement

```python
from yori.config import YoriConfig, EnforcementConfig
from yori.models import PolicyResult
from yori.enforcement import should_enforce_policy
from yori.emergency import activate_emergency_override

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True)
)

# Activate emergency override
activate_emergency_override(config, "admin", "192.168.1.1")

# Try to enforce a blocking policy
policy_result = PolicyResult(
    action="block",
    policy_name="test.rego",
    reason="Test block"
)

decision = should_enforce_policy(
    request={},
    policy_result=policy_result,
    client_ip="192.168.1.100",
    config=config
)

# Should not block due to emergency override
assert decision.should_block == False
assert "emergency" in decision.reason.lower()
print("✅ Test 5.5 PASS: Emergency override bypasses enforcement")
```

**Expected:** Override prevents blocking

---

## Phase 6: Enforcement Engine

### Test 6.1: Enforcement Disabled by Default

**Objective:** Verify enforcement off without config

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig

config = YoriConfig()
engine = EnforcementEngine(config)

assert engine._is_enforcement_enabled() == False
print("✅ Test 6.1 PASS: Enforcement disabled by default")
```

**Expected:** Enforcement not enabled

### Test 6.2: Enforcement Requires All Flags

**Objective:** Verify all requirements checked

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig, EnforcementConfig

# Missing mode=enforce
config1 = YoriConfig(
    mode="observe",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True)
)
assert EnforcementEngine(config1)._is_enforcement_enabled() == False

# Missing enabled flag
config2 = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=False, consent_accepted=True)
)
assert EnforcementEngine(config2)._is_enforcement_enabled() == False

# Missing consent
config3 = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=False)
)
assert EnforcementEngine(config3)._is_enforcement_enabled() == False

print("✅ Test 6.2 PASS: All enforcement requirements checked")
```

**Expected:** Each missing requirement prevents enforcement

### Test 6.3: Enforcement Enabled When Complete

**Objective:** Verify enforcement activates correctly

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig, EnforcementConfig

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True)
)
engine = EnforcementEngine(config)

assert engine._is_enforcement_enabled() == True
print("✅ Test 6.3 PASS: Enforcement enabled when requirements met")
```

**Expected:** Enforcement enabled

### Test 6.4: Block Action Blocks Request

**Objective:** Verify block action actually blocks

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig, EnforcementConfig, PolicyConfig, PolicyFileConfig
from yori.models import PolicyResult

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
    policies=PolicyConfig(
        files={"test": PolicyFileConfig(enabled=True, action="block")}
    )
)

engine = EnforcementEngine(config)
policy_result = PolicyResult(action="alert", policy_name="test.rego", reason="Test")

decision = engine.should_enforce_policy(
    request={},
    policy_result=policy_result,
    client_ip="192.168.1.100"
)

assert decision.should_block == True
assert decision.action_taken == "block"
print("✅ Test 6.4 PASS: Block action blocks request")
```

**Expected:** Request blocked

### Test 6.5: Alert Action Doesn't Block

**Objective:** Verify alert action only logs

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig, EnforcementConfig, PolicyConfig, PolicyFileConfig
from yori.models import PolicyResult

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
    policies=PolicyConfig(
        files={"test": PolicyFileConfig(enabled=True, action="alert")}
    )
)

engine = EnforcementEngine(config)
policy_result = PolicyResult(action="block", policy_name="test.rego", reason="Test")

decision = engine.should_enforce_policy(
    request={},
    policy_result=policy_result,
    client_ip="192.168.1.100"
)

assert decision.should_block == False
assert decision.action_taken == "alert"
print("✅ Test 6.5 PASS: Alert action doesn't block")
```

**Expected:** Request not blocked, only alerted

### Test 6.6: Allowlist Bypasses Enforcement

**Objective:** Verify allowlisted devices not blocked

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig, EnforcementConfig, PolicyConfig, PolicyFileConfig
from yori.models import PolicyResult, AllowlistDevice, AllowlistConfig

allowlist_device = AllowlistDevice(
    ip="192.168.1.100",
    name="test-device",
    enabled=True
)

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(
        enabled=True,
        consent_accepted=True,
        allowlist=AllowlistConfig(devices=[allowlist_device])
    ),
    policies=PolicyConfig(
        files={"test": PolicyFileConfig(enabled=True, action="block")}
    )
)

engine = EnforcementEngine(config)
policy_result = PolicyResult(action="block", policy_name="test.rego", reason="Test")

decision = engine.should_enforce_policy(
    request={},
    policy_result=policy_result,
    client_ip="192.168.1.100"
)

assert decision.should_block == False
assert "allowlist" in decision.reason.lower()
print("✅ Test 6.6 PASS: Allowlist bypasses enforcement")
```

**Expected:** Allowlisted device not blocked

### Test 6.7: Disabled Policy Acts as Allow

**Objective:** Verify disabled policies don't enforce

```python
from yori.enforcement import EnforcementEngine
from yori.config import YoriConfig, EnforcementConfig, PolicyConfig, PolicyFileConfig
from yori.models import PolicyResult

config = YoriConfig(
    mode="enforce",
    enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
    policies=PolicyConfig(
        files={"test": PolicyFileConfig(enabled=False, action="block")}
    )
)

engine = EnforcementEngine(config)
policy_result = PolicyResult(action="block", policy_name="test.rego", reason="Test")

decision = engine.should_enforce_policy(
    request={},
    policy_result=policy_result,
    client_ip="192.168.1.100"
)

assert decision.should_block == False
assert decision.action_taken == "allow"
print("✅ Test 6.7 PASS: Disabled policy allows request")
```

**Expected:** Disabled policy doesn't block

---

## Phase 7: Block Page Rendering

### Test 7.1: Render Basic Block Page

**Objective:** Verify block page HTML generation

```python
from yori.models import BlockDecision
from yori.block_page import render_block_page
from datetime import datetime

decision = BlockDecision(
    should_block=True,
    policy_name="test.rego",
    reason="Test block reason",
    timestamp=datetime.now(),
    allow_override=False
)

html = render_block_page(decision)

assert "Request Blocked" in html or "blocked" in html.lower()
assert "test.rego" in html
assert "Test block reason" in html
print("✅ Test 7.1 PASS: Block page renders")
```

**Expected:** HTML contains block information

### Test 7.2: Block Page with Override Option

**Objective:** Verify override form appears

```python
from yori.models import BlockDecision
from yori.block_page import render_block_page
from datetime import datetime

decision = BlockDecision(
    should_block=True,
    policy_name="bedtime.rego",
    reason="LLM access not allowed after 21:00",
    timestamp=datetime.now(),
    allow_override=True
)

html = render_block_page(decision)

assert "override" in html.lower()
assert 'password' in html.lower()
print("✅ Test 7.2 PASS: Override form present")
```

**Expected:** Override form included

### Test 7.3: Block Page Without Override

**Objective:** Verify no override form when disabled

```python
from yori.models import BlockDecision
from yori.block_page import render_block_page
from datetime import datetime

decision = BlockDecision(
    should_block=True,
    policy_name="strict.rego",
    reason="Strict policy",
    timestamp=datetime.now(),
    allow_override=False
)

html = render_block_page(decision)

# Should not have override form
assert 'type="password"' not in html
print("✅ Test 7.3 PASS: No override form when disabled")
```

**Expected:** No password field

### Test 7.4: Custom Message Display

**Objective:** Verify custom messages shown

```python
from yori.block_page import get_custom_message

message = get_custom_message("bedtime.rego")

assert message is not None
assert len(message) > 0
assert "bedtime" in message.lower() or "tomorrow" in message.lower()
print("✅ Test 7.4 PASS: Custom message retrieved")
```

**Expected:** Custom message exists for bedtime policy

### Test 7.5: HTML Escaping for XSS Prevention

**Objective:** Verify user input is escaped

```python
from yori.models import BlockDecision
from yori.block_page import render_block_page
from datetime import datetime

decision = BlockDecision(
    should_block=True,
    policy_name="<script>alert('xss')</script>",
    reason="<img src=x onerror=alert('xss')>",
    timestamp=datetime.now(),
    allow_override=False
)

html = render_block_page(decision)

# XSS should be escaped
assert "<script>" not in html
assert "&lt;script&gt;" in html
print("✅ Test 7.5 PASS: XSS properly escaped")
```

**Expected:** Malicious input escaped

---

## Phase 8: Audit Logging

### Test 8.1: Initialize Audit Database

**Objective:** Verify database creation

```python
from yori.audit_enforcement import EnforcementAuditLogger
from pathlib import Path
import os

# Clean test database
db_path = "/tmp/yori-test/data/audit_test.db"
if os.path.exists(db_path):
    os.remove(db_path)

# Initialize
logger = EnforcementAuditLogger(db_path)
logger.initialize_db()

assert os.path.exists(db_path)
print("✅ Test 8.1 PASS: Audit database created")
```

**Expected:** Database file created

### Test 8.2: Log Block Event

**Objective:** Verify block events logged

```python
from yori.audit_enforcement import EnforcementAuditLogger

logger = EnforcementAuditLogger("/tmp/yori-test/data/audit_test.db")
logger.initialize_db()

event_id = logger.log_block_event(
    client_ip="192.168.1.100",
    policy_name="test.rego",
    reason="Test block",
    endpoint="api.openai.com"
)

assert event_id is not None
print("✅ Test 8.2 PASS: Block event logged")
```

**Expected:** Event logged with ID

### Test 8.3: Log Override Attempt

**Objective:** Verify override attempts logged

```python
from yori.audit_enforcement import EnforcementAuditLogger

logger = EnforcementAuditLogger("/tmp/yori-test/data/audit_test.db")

event_id = logger.log_override_attempt(
    client_ip="192.168.1.100",
    policy_name="test.rego",
    success=False,
    reason="Wrong password"
)

assert event_id is not None
print("✅ Test 8.3 PASS: Override attempt logged")
```

**Expected:** Override logged

### Test 8.4: Log Allowlist Bypass

**Objective:** Verify allowlist bypasses logged

```python
from yori.audit_enforcement import EnforcementAuditLogger

logger = EnforcementAuditLogger("/tmp/yori-test/data/audit_test.db")

event_id = logger.log_allowlist_bypass(
    client_ip="192.168.1.100",
    device_name="test-device",
    policy_name="test.rego",
    bypass_type="allowlist"
)

assert event_id is not None
print("✅ Test 8.4 PASS: Allowlist bypass logged")
```

**Expected:** Bypass logged

### Test 8.5: Query Recent Events

**Objective:** Verify event retrieval

```python
from yori.audit_enforcement import EnforcementAuditLogger

logger = EnforcementAuditLogger("/tmp/yori-test/data/audit_test.db")

# Get recent events
events = logger.get_recent_events(limit=10)

assert isinstance(events, list)
assert len(events) > 0
print(f"✅ Test 8.5 PASS: Retrieved {len(events)} events")
```

**Expected:** Recent events returned

### Test 8.6: Get Enforcement Statistics

**Objective:** Verify statistics generation

```python
from yori.audit_enforcement import EnforcementAuditLogger

logger = EnforcementAuditLogger("/tmp/yori-test/data/audit_test.db")

stats = logger.get_enforcement_stats()

assert "total_blocks" in stats
assert "total_overrides" in stats
assert "total_bypasses" in stats
print("✅ Test 8.6 PASS: Statistics generated")
```

**Expected:** Statistics returned

---

## Test Execution

### Quick Run (All Phases)

Save this script as `/tmp/yori-test/run_all_tests.py`:

```python
#!/usr/bin/env python3
"""
YORI v0.2.0 Manual Test Runner
Run all test phases automatically
"""

import sys
import traceback

def run_test(test_name, test_func):
    """Run a single test and report result"""
    try:
        test_func()
        return True
    except AssertionError as e:
        print(f"❌ {test_name} FAIL: {e}")
        return False
    except Exception as e:
        print(f"💥 {test_name} ERROR: {e}")
        traceback.print_exc()
        return False

# Import all test phases here and run
# [Test implementations from above]

if __name__ == "__main__":
    print("YORI v0.2.0 Manual Test Suite")
    print("=" * 60)

    passed = 0
    failed = 0

    # Run all tests...
    # (Add test calls here)

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
```

---

## Test Report Template

After completing tests, document results:

```markdown
# YORI v0.2.0 Manual Test Report

**Date:** [DATE]
**Tester:** [YOUR NAME]
**Environment:** Linux / macOS / FreeBSD
**Duration:** [TIME]

## Summary

- **Total Tests:** 48
- **Passed:** XX
- **Failed:** XX
- **Skipped:** XX

## Phase Results

| Phase | Tests | Passed | Failed | Notes |
|-------|-------|--------|--------|-------|
| Configuration | 5 | X | X | ... |
| Consent | 6 | X | X | ... |
| Allowlist | 8 | X | X | ... |
| Time Exceptions | 6 | X | X | ... |
| Emergency Override | 5 | X | X | ... |
| Enforcement Engine | 7 | X | X | ... |
| Block Page | 5 | X | X | ... |
| Audit Logging | 6 | X | X | ... |

## Issues Found

### Critical
- [Issue description]

### Major
- [Issue description]

### Minor
- [Issue description]

## Recommendations

- [Recommendation 1]
- [Recommendation 2]

## Sign-off

**Status:** ✅ PASS / ⚠️ PASS WITH ISSUES / ❌ FAIL
**Ready for v0.3.0:** YES / NO

**Signature:** __________________
**Date:** __________________
```

---

## Cleanup

```bash
# Remove test data
rm -rf /tmp/yori-test

# Uninstall if needed
pip uninstall yori -y
```

---

## Notes

- Tests assume Python imports work correctly
- Some time-based tests may need adjustment for current time
- Database tests create temporary files
- All tests are non-destructive (use /tmp)

**Total estimated time: 2-3 hours**
