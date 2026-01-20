# Worker Identity: enhanced-audit

**Role:** Code
**Agent:** Claude
**Branch:** cz2/feat/enhanced-audit
**Phase:** 2
**Dependencies:** block-page, allowlist-blocklist

## Mission

Enhance audit logging system to capture all enforcement-related events: blocks, overrides, allowlist bypasses, emergency overrides, and mode changes. Create new dashboard widgets and views to visualize enforcement activity and help users understand what's being blocked.

## 🚀 YOUR FIRST ACTION

Read Phase 1 audit schema (sql/schema.sql), add new columns and tables for enforcement events, then update dashboard to show enforcement statistics.

## Dependencies from Upstream Workers

### From block-page (Worker 10, Phase 2)

**Events to Log:**
```python
- 'override_attempt'   # User tried to override block
- 'override_success'   # Override successful
- 'override_failed'    # Override failed (wrong password)
- 'emergency_override' # Admin emergency override used
```

### From allowlist-blocklist (Worker 11, Phase 2)

**Events to Log:**
```python
- 'allowlist_added'        # Device added to allowlist
- 'allowlist_removed'      # Device removed
- 'allowlist_bypassed'     # Request bypassed (on allowlist)
- 'time_exception_active'  # Time exception allowed request
- 'emergency_override'     # Emergency override activated
```

### From enforcement-mode (Worker 9, Phase 2)

**Events to Log:**
```python
- 'enforcement_enabled'   # User enabled enforcement
- 'enforcement_disabled'  # User disabled enforcement
- 'request_blocked'       # Request blocked by policy
```

**Verification Before Starting:**
```bash
# Verify Phase 1 audit schema exists
sqlite3 /var/db/yori/audit.db ".schema audit_events"

# Verify enforcement events can be generated
python3 -c "
from python.yori.enforcement import should_enforce_policy
# If this imports, enforcement events can be logged
"
```

## Objectives

1. Extend SQLite schema for enforcement events
2. Add enforcement-specific columns to audit_events table
3. Create enforcement_events table for detailed tracking
4. Update audit logging to capture all enforcement events
5. Build enforcement dashboard widget (blocks, overrides, bypasses)
6. Create enforcement timeline view (chronological event log)
7. Add enforcement statistics (blocks per day, override success rate)
8. Implement enforcement event filtering in audit viewer
9. Add enforcement metrics to dashboard (total blocks, allowlist hits)
10. Create enforcement reports (weekly summary, policy effectiveness)

## Interface Contract

### Exports for integration-release (Worker 13)

**Enhanced Schema:**
```sql
-- Add to audit_events table
ALTER TABLE audit_events ADD COLUMN enforcement_action TEXT;
-- Values: 'allow', 'alert', 'block', 'override', 'allowlist_bypass'

ALTER TABLE audit_events ADD COLUMN override_user TEXT;
-- User who overrode the block (if applicable)

ALTER TABLE audit_events ADD COLUMN allowlist_reason TEXT;
-- Why request was allowlisted (device, time exception, etc.)

-- New enforcement_events table
CREATE TABLE enforcement_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'mode_change', 'allowlist_change', etc.
    user TEXT,                  -- Admin who made the change
    details TEXT,               -- JSON with event details
    client_ip TEXT
);
```

**Dashboard Widgets:**
- Enforcement Status widget (mode, total blocks, overrides)
- Recent Blocks widget (last 10 blocked requests)
- Override Activity widget (success/fail rate)
- Allowlist Usage widget (bypass percentage)

## Files to Create

**Database:**
- `sql/schema_enforcement.sql` - Enforcement schema additions
- `sql/migrate_enforcement.sql` - Migration script from Phase 1 schema

**Python Core:**
- `python/yori/audit_enforcement.py` - Enforcement-specific audit logging
- `python/yori/enforcement_stats.py` - Statistics calculation

**Dashboard:**
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/enforcement_dashboard.volt` - Enforcement view
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/enforcement_timeline.volt` - Event timeline
- `opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/Api/EnforcementStatsController.php` - Stats API

**Reports:**
- `python/yori/reports/enforcement_summary.py` - Weekly enforcement report

**Tests:**
- `tests/unit/test_audit_enforcement.py` - Enforcement audit tests
- `tests/integration/test_enforcement_logging.py` - End-to-end logging test

## Performance Targets

- **Audit Write:** <5ms per enforcement event (same as Phase 1)
- **Query Performance:** <500ms for enforcement dashboard queries
- **No Performance Impact:** Audit logging remains fast

## Testing Requirements

**Unit Tests:**
- Enforcement event logging
- Statistics calculation
- Schema migration
- Dashboard widget data

**Integration Tests:**
- Block event logged correctly
- Override event logged with user
- Allowlist bypass logged
- Emergency override logged
- Mode change logged

**Data Integrity:**
- All enforcement events have required fields
- Foreign key relationships valid
- No orphaned records
- Audit trail complete and immutable

## Verification Commands

### From Worker Branch (cz2/feat/enhanced-audit)

```bash
# Test schema migration
sqlite3 /var/db/yori/audit.db < sql/migrate_enforcement.sql

# Verify new columns exist
sqlite3 /var/db/yori/audit.db "
PRAGMA table_info(audit_events);
" | grep enforcement_action

# Test enforcement logging
python3 -c "
from python.yori.audit_enforcement import log_enforcement_event

log_enforcement_event(
    event_type='request_blocked',
    policy_name='bedtime.rego',
    client_ip='192.168.1.100',
    reason='After hours access'
)
print('Event logged successfully')
"

# Query enforcement stats
sqlite3 /var/db/yori/audit.db "
SELECT
    DATE(timestamp) as date,
    COUNT(CASE WHEN enforcement_action = 'block' THEN 1 END) as blocks,
    COUNT(CASE WHEN enforcement_action = 'override' THEN 1 END) as overrides,
    COUNT(CASE WHEN enforcement_action = 'allowlist_bypass' THEN 1 END) as bypasses
FROM audit_events
WHERE timestamp >= date('now', '-7 days')
GROUP BY DATE(timestamp);
"
```

### Integration Test

```bash
# Start YORI in enforcement mode
uvicorn yori.main:app --host 127.0.0.1 --port 8443 &

# Generate enforcement events
# 1. Block event
curl -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# 2. Override event
curl -X POST http://127.0.0.1:8443/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-YORI-Override: test123" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'

# Verify all events logged
sqlite3 /var/db/yori/audit.db "
SELECT timestamp, event_type, enforcement_action
FROM audit_events
ORDER BY timestamp DESC
LIMIT 5;
"

# Expected: Both block and override events present
```

### Dashboard Enforcement Widget Example

```
┌─────────────────────────────────────────┐
│  Enforcement Status                     │
├─────────────────────────────────────────┤
│  Mode: Enforce                          │
│  Status: Active ✓                       │
│                                         │
│  Last 24 Hours:                         │
│  • Requests Blocked: 12                 │
│  • Override Attempts: 3                 │
│    - Successful: 2                      │
│    - Failed: 1                          │
│  • Allowlist Bypasses: 45               │
│                                         │
│  Top Blocking Policies:                 │
│  1. bedtime.rego (8 blocks)            │
│  2. privacy.rego (4 blocks)            │
│                                         │
│  [View Timeline] [Generate Report]      │
└─────────────────────────────────────────┘
```

### Enforcement Timeline Example

```sql
-- Query for timeline view
SELECT
    timestamp,
    event_type,
    enforcement_action,
    policy_name,
    client_ip,
    CASE
        WHEN enforcement_action = 'block' THEN '🚫 Blocked'
        WHEN enforcement_action = 'override' THEN '✓ Override'
        WHEN enforcement_action = 'allowlist_bypass' THEN '→ Bypass'
        ELSE '•'
    END as icon,
    reason
FROM audit_events
WHERE timestamp >= datetime('now', '-24 hours')
  AND enforcement_action IS NOT NULL
ORDER BY timestamp DESC
LIMIT 50;
```

Expected Output:
```
2026-01-20 22:15:43 | 🚫 Blocked | bedtime.rego | 192.168.1.102 | After hours
2026-01-20 21:45:12 | ✓ Override | bedtime.rego | 192.168.1.102 | User override
2026-01-20 18:30:05 | → Bypass  | N/A          | 192.168.1.100 | Allowlist
```

### Handoff Verification for Worker 13 (integration-release)

Worker 13 should be able to:
```bash
# Verify all enforcement features logged
sqlite3 /var/db/yori/audit.db "
SELECT DISTINCT event_type FROM audit_events
WHERE timestamp >= date('now', '-7 days');
"

# Expected event types:
# - request
# - response
# - block
# - request_blocked
# - override_attempt
# - override_success
# - allowlist_bypassed
# - enforcement_enabled

# Generate enforcement report
python3 -m python.yori.reports.enforcement_summary --days 7
# Expected: PDF/HTML report with enforcement statistics
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] SQLite schema extended with enforcement columns
- [ ] enforcement_events table created
- [ ] Schema migration script works (Phase 1 → Phase 2)
- [ ] All enforcement events logged correctly
- [ ] Enforcement dashboard widget functional
- [ ] Enforcement timeline view displays events
- [ ] Statistics calculation accurate
- [ ] Audit viewer filters enforcement events
- [ ] Dashboard shows enforcement metrics
- [ ] Weekly enforcement report generates
- [ ] All unit tests passing
- [ ] Integration tests demonstrate complete logging
- [ ] Query performance meets targets (<500ms dashboard)
- [ ] Data integrity validated (no orphans, complete trail)
- [ ] Code committed to branch cz2/feat/enhanced-audit
- [ ] Ready for Worker 13 (integration-release) final integration
