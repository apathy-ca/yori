# Worker Identity: allowlist-blocklist

**Role:** Code
**Agent:** Claude
**Branch:** cz2/feat/allowlist-blocklist
**Phase:** 2
**Dependencies:** enforcement-mode

## Mission

Build device allowlist system to prevent blocking trusted devices/IPs, implement time-based exceptions for scheduled access, and create an emergency override mechanism to disable all enforcement instantly. Includes management UI for easy configuration.

## 🚀 YOUR FIRST ACTION

Read enforcement logic from Worker 9, create allowlist configuration schema, and implement allowlist check that bypasses enforcement for trusted devices.

## Dependencies from Upstream Workers

### From enforcement-mode (Worker 9, Phase 2)

**Required Artifacts:**
```python
# python/yori/enforcement.py
def should_enforce_policy(
    request: dict,
    policy_result: PolicyResult,
    client_ip: str
) -> EnforcementDecision:
    # Worker 11 will add allowlist checks HERE
    pass
```

**Verification Before Starting:**
```bash
# Verify enforcement logic exists
python3 -c "from python.yori.enforcement import should_enforce_policy"
```

## Objectives

1. Create device allowlist configuration (IP addresses, MAC addresses)
2. Implement allowlist check in enforcement logic
3. Add time-based exceptions (allow 9am-5pm for homework)
4. Create emergency override mechanism (disable all enforcement)
5. Build allowlist management UI (add/remove devices)
6. Add device discovery (show recent devices, one-click add)
7. Implement MAC address resolution (IP → MAC)
8. Create allowlist groups (e.g., "family", "work devices")
9. Add temporary allowlist entries (1 hour, 1 day)
10. Write tests for allowlist logic

## Interface Contract

### Exports for enhanced-audit (Worker 12)

**Allowlist Events:**
```python
# Audit events for Worker 12
- 'allowlist_added'        # Device added to allowlist
- 'allowlist_removed'      # Device removed
- 'allowlist_bypassed'     # Request bypassed enforcement (on allowlist)
- 'time_exception_active'  # Time-based exception allowed request
- 'emergency_override'     # Emergency override activated
```

**Allowlist Configuration:**
```yaml
# yori.conf
enforcement:
  allowlist:
    devices:
      - ip: "192.168.1.100"
        name: "Dad's Laptop"
        mac: "aa:bb:cc:dd:ee:ff"
        enabled: true
      - ip: "192.168.1.101"
        name: "Work Desktop"
        permanent: true  # Never block

    groups:
      - name: "family"
        devices: ["192.168.1.100", "192.168.1.101"]

    time_exceptions:
      - name: "homework_hours"
        days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
        start_time: "15:00"
        end_time: "18:00"
        devices: ["192.168.1.102"]  # Kid's laptop

  emergency_override:
    enabled: false
    password_hash: "sha256:..."
```

## Files to Create

**Python Core:**
- `python/yori/allowlist.py` - Allowlist management and checking
- `python/yori/time_exceptions.py` - Time-based exception logic
- `python/yori/emergency.py` - Emergency override mechanism

**Configuration:**
- Update `yori.conf.example` with allowlist section
- Add allowlist schema to `python/yori/models.py`

**Integration:**
- Update `python/yori/enforcement.py` - Add allowlist checks

**OPNsense UI:**
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/allowlist.volt` - Allowlist management page
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/emergency.volt` - Emergency override page
- `opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/Api/AllowlistController.php` - API

**Tests:**
- `tests/unit/test_allowlist.py` - Allowlist logic tests
- `tests/unit/test_time_exceptions.py` - Time-based exception tests
- `tests/integration/test_allowlist_bypass.py` - End-to-end allowlist test

## Performance Targets

- **Allowlist Check:** <1ms (simple IP/MAC lookup)
- **Time Exception Check:** <1ms (time comparison)
- **No Performance Impact:** Checks are fast lookups

## Testing Requirements

**Unit Tests:**
- Allowlist IP checking
- MAC address resolution
- Time-based exception logic
- Emergency override validation
- Group membership checking

**Integration Tests:**
- Allowlisted device bypasses enforcement
- Non-allowlisted device gets blocked
- Time exception allows access during hours
- Emergency override disables all enforcement
- Temporary allowlist expires correctly

**Edge Cases:**
- IP changes but MAC same (still allowlisted)
- Device on allowlist AND violates policy (allowlist wins)
- Multiple time exceptions overlap
- Emergency override + allowlist both active

## Verification Commands

### From Worker Branch (cz2/feat/allowlist-blocklist)

```bash
# Test allowlist checking
python3 -c "
from python.yori.allowlist import is_allowlisted
from python.yori.config import load_config

config = load_config('yori.conf.example')
result = is_allowlisted('192.168.1.100', config)
print(f'Device allowlisted: {result}')
"

# Test time-based exception
python3 -c "
from python.yori.time_exceptions import is_exception_active
from datetime import datetime

now = datetime(2026, 1, 20, 16, 30)  # Monday 4:30pm
result = is_exception_active('homework_hours', '192.168.1.102', now)
print(f'Exception active: {result}')
"

# Test emergency override
python3 -c "
from python.yori.emergency import is_emergency_override_active
from python.yori.config import load_config

config = load_config('yori.conf.example')
result = is_emergency_override_active(config)
print(f'Emergency override: {result}')
"

# Verify UI exists
ls -la opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/allowlist.volt
```

### Integration Test

```bash
# Start YORI in enforcement mode
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &

# Configure allowlist
cat > yori.conf <<EOF
mode: enforce
enforcement:
  enabled: true
  consent_accepted: true
  allowlist:
    devices:
      - ip: "192.168.1.100"
        name: "Test Device"
        enabled: true
EOF

# Send request from allowlisted IP
# (Mock source IP as 192.168.1.100)
curl -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# Expected: Request forwarded (NOT blocked), even if policy would block

# Send request from non-allowlisted IP
curl -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.200" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# Expected: Request blocked (normal enforcement)
```

### Allowlist Management UI Example

```
┌─────────────────────────────────────────┐
│  Allowlist Management                   │
├─────────────────────────────────────────┤
│                                         │
│  Devices Never Blocked:                 │
│  ┌────────────────────────────────────┐ │
│  │ ☑ Dad's Laptop (192.168.1.100)    │ │
│  │ ☑ Work Desktop (192.168.1.101)    │ │
│  │ ☐ Kid's Laptop (192.168.1.102)    │ │
│  └────────────────────────────────────┘ │
│                                         │
│  [Add Device]  [Remove Selected]        │
│                                         │
│  Time-Based Exceptions:                 │
│  ┌────────────────────────────────────┐ │
│  │ Homework Hours                     │ │
│  │ Mon-Fri, 3:00pm - 6:00pm          │ │
│  │ Applies to: Kid's Laptop           │ │
│  └────────────────────────────────────┘ │
│                                         │
│  [Add Exception]  [Edit]                │
│                                         │
│  ⚠️  Emergency Override:                │
│  [ Disable All Enforcement ]            │
│  (Requires admin password)              │
│                                         │
└─────────────────────────────────────────┘
```

### Handoff Verification for Worker 12 (enhanced-audit)

Worker 12 should be able to:
```bash
# Query allowlist bypasses from audit
sqlite3 /var/db/yori/audit.db "
SELECT
    timestamp,
    client_ip,
    policy_name,
    event_type
FROM audit_events
WHERE event_type = 'allowlist_bypassed'
ORDER BY timestamp DESC
LIMIT 10;
"

# Track emergency override activations
sqlite3 /var/db/yori/audit.db "
SELECT timestamp, event_type, client_ip
FROM audit_events
WHERE event_type = 'emergency_override'
ORDER BY timestamp DESC;
"
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Device allowlist configuration implemented
- [ ] Allowlist check integrated into enforcement logic
- [ ] Allowlisted devices bypass enforcement (tested)
- [ ] Time-based exceptions functional (9am-5pm example works)
- [ ] Emergency override mechanism implemented
- [ ] Emergency override disables ALL enforcement instantly
- [ ] Allowlist management UI completed
- [ ] Device discovery shows recent devices
- [ ] MAC address resolution working
- [ ] Allowlist groups functional ("family", "work")
- [ ] Temporary allowlist entries (1 hour, 1 day)
- [ ] All unit tests passing
- [ ] Integration tests demonstrate allowlist bypass
- [ ] Performance targets met (<1ms allowlist check)
- [ ] Code committed to branch cz2/feat/allowlist-blocklist
- [ ] Ready for Worker 12 (enhanced-audit) integration
