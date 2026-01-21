# YORI Enforcement Mode Guide

## Overview

Enforcement mode allows YORI to actually block LLM requests based on policies.
This is an **opt-in feature** requiring explicit user consent.

## Enabling Enforcement

1. Navigate to: System → YORI → Enforcement Settings
2. Read the warning about potential functionality breakage
3. Check: "I understand and accept the risks"
4. Click: Enable Enforcement
5. Set per-policy actions (allow/alert/block)

## Per-Policy Enforcement

Each policy can have different actions:
- **Allow:** Always allow (no enforcement)
- **Alert:** Log and alert, but don't block
- **Block:** Actually block the request

## Block Page

When a request is blocked, users see a friendly explanation page showing:
- Policy name that triggered the block
- Reason for the block
- Timestamp
- Option to override with password (if enabled)

## Override Mechanism

### Password Override
Users can bypass blocks with a password:
1. Enter override password on block page
2. If correct, request is allowed and logged
3. Failed attempts are rate limited (3 per minute)

### Setting Override Password
```bash
# Generate password hash
python3 -c "import hashlib; print('sha256:' + hashlib.sha256(b'your_password').hexdigest())"

# Add to yori.conf
enforcement:
  override_enabled: true
  override_password_hash: "sha256:..."
```

## Allowlist

Prevent blocking trusted devices:
1. Navigate to: System → YORI → Allowlist
2. Add devices by IP or MAC address
3. Devices on allowlist bypass all policies

### Time-Based Exceptions
Allow access during specific hours:
```yaml
time_exceptions:
  - name: "homework_hours"
    description: "Allow LLM access for homework help"
    days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
    start_time: "15:00"  # 3:00 PM
    end_time: "18:00"    # 6:00 PM
    device_ips: ["192.168.1.102"]
    enabled: true
```

## Emergency Override

Disable all enforcement instantly:
1. Navigate to: System → YORI → Emergency Override
2. Enter admin password
3. Click: Disable All Enforcement
4. All requests allowed until re-enabled

### Setting Emergency Override Password
```bash
# Generate password hash
python3 -c "from yori.emergency import hash_password; print(hash_password('your_password'))"

# Add to yori.conf
enforcement:
  emergency_override:
    password_hash: "sha256:..."
    require_password: true
```

## Enforcement Dashboard

View enforcement statistics:
- Navigate to: System → YORI → Dashboard
- Enforcement Status widget shows:
  - Total blocks
  - Overrides (success/fail)
  - Allowlist bypasses
  - Emergency override status

## Enforcement Timeline

View chronological enforcement events:
1. Navigate to: System → YORI → Enforcement Timeline
2. See all blocks, overrides, and bypasses
3. Filter by date range, policy, or device

## Best Practices

1. **Start in Observe Mode**
   - Run in observe mode for at least 1 week
   - Review audit logs to understand patterns
   - Identify legitimate use cases for allowlist

2. **Test Policies Carefully**
   - Use "alert" action first to see what would be blocked
   - Only change to "block" after validating policy behavior
   - Start with lenient policies, tighten gradually

3. **Configure Allowlist First**
   - Add trusted devices before enabling enforcement
   - Set up time exceptions for known access patterns
   - Keep emergency override password secure but accessible

4. **Monitor Regularly**
   - Check enforcement dashboard weekly
   - Review override attempts for unauthorized access
   - Adjust policies based on false positives

5. **Emergency Procedures**
   - Document emergency override password location
   - Test emergency override before critical need
   - Have plan to disable enforcement if needed

## Troubleshooting

### Legitimate Requests Being Blocked

1. Check enforcement timeline for block reason
2. Add device to allowlist if trusted
3. Create time exception if pattern-based
4. Adjust policy to be less restrictive
5. Use override mechanism for one-time access

### Override Not Working

1. Verify override_enabled is true in config
2. Check password hash is correct format
3. Review rate limiting (max 3 attempts/minute)
4. Check audit logs for override attempts
5. Use emergency override if urgent

### Emergency Override Not Working

1. Verify password hash in configuration
2. Check require_password setting
3. Review admin_token_hash format
4. Check emergency override enabled status

## Configuration Reference

See `yori.conf.example` for full configuration examples including:
- Enforcement mode settings
- Per-policy actions
- Override configuration
- Allowlist examples
- Time exceptions
- Emergency override setup

## See Also

- [Configuration Guide](CONFIGURATION.md)
- [Policy Guide](POLICY_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Security Best Practices](../SECURITY.md)
