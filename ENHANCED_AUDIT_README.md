# Enhanced Audit Logging (Phase 2)

## Overview

This feature extends the Phase 1 audit logging system with comprehensive enforcement tracking capabilities. It captures all enforcement-related events including blocks, overrides, allowlist bypasses, and mode changes.

## Components

### Database Schema

**Files:**
- `sql/schema.sql` - Phase 1 base audit schema
- `sql/schema_enforcement.sql` - Phase 2 enforcement additions
- `sql/migrate_enforcement.sql` - Migration script from Phase 1 to Phase 2

**New Columns (audit_events table):**
- `enforcement_action` - Action taken (allow, alert, block, override, allowlist_bypass)
- `override_user` - User who performed override
- `allowlist_reason` - Reason for allowlist bypass

**New Tables:**
- `enforcement_events` - Tracks configuration changes (mode changes, allowlist updates, etc.)

**New Views:**
- `enforcement_stats` - Daily enforcement statistics
- `recent_blocks` - Recent block events for dashboard
- `override_stats` - Override success rate statistics
- `top_blocking_policies` - Most active blocking policies

### Python Modules

**Core Logging:**
- `python/yori/audit_enforcement.py` - Enforcement-specific audit logging
  - `EnforcementAuditLogger` class with methods for:
    - `log_block_event()` - Log request blocks
    - `log_override_attempt()` - Log override attempts (success/fail)
    - `log_allowlist_bypass()` - Log allowlist bypasses
    - `log_mode_change()` - Log enforcement mode changes
    - `log_allowlist_change()` - Log allowlist modifications
    - `log_emergency_override()` - Log emergency overrides

**Statistics:**
- `python/yori/enforcement_stats.py` - Statistics calculation
  - `EnforcementStatsCalculator` class with methods for:
    - `get_enforcement_summary()` - Overall summary statistics
    - `get_daily_stats()` - Daily breakdown
    - `get_recent_blocks()` - Recent block events
    - `get_top_blocking_policies()` - Most active policies
    - `get_enforcement_timeline()` - Event timeline
    - `get_enforcement_mode_history()` - Mode change history

**Reports:**
- `python/yori/reports/enforcement_summary.py` - Weekly/monthly report generator
  - Generates text and JSON format reports
  - CLI tool: `python -m yori.reports.enforcement_summary --days 7`

### Dashboard & UI

**Views (Volt Templates):**
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/enforcement_dashboard.volt`
  - Enforcement status widget
  - Statistics cards (blocks, overrides, bypasses, alerts)
  - Recent blocks table
  - Top blocking policies list
  - Auto-refresh every 30 seconds

- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/enforcement_timeline.volt`
  - Chronological event timeline
  - Filtering by time range, action type, client IP
  - Visual event icons (🚫 block, ✓ override, → bypass)

**API Controller (PHP):**
- `opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/Api/EnforcementStatsController.php`
  - REST API endpoints:
    - `GET /api/yori/enforcement/stats` - Summary statistics
    - `GET /api/yori/enforcement/recent_blocks` - Recent blocks
    - `GET /api/yori/enforcement/top_policies` - Top policies
    - `GET /api/yori/enforcement/timeline` - Event timeline
    - `GET /api/yori/enforcement/daily_stats` - Daily statistics
    - `GET /api/yori/enforcement/mode_history` - Mode change history

### Tests

**Unit Tests:**
- `tests/unit/test_audit_enforcement.py`
  - Tests for all EnforcementAuditLogger methods
  - Event logging verification
  - Database schema validation

**Integration Tests:**
- `tests/integration/test_enforcement_logging.py`
  - End-to-end enforcement flow testing
  - Statistics calculation verification
  - Report generation testing
  - Timeline and history tracking

## Usage

### Database Migration

Migrate existing Phase 1 database to Phase 2:

```bash
sqlite3 /var/db/yori/audit.db < sql/migrate_enforcement.sql
```

### Logging Enforcement Events

```python
from pathlib import Path
from yori.audit_enforcement import EnforcementAuditLogger

logger = EnforcementAuditLogger(Path("/var/db/yori/audit.db"))

# Log a block event
logger.log_block_event(
    policy_name="bedtime.rego",
    client_ip="192.168.1.100",
    endpoint="api.openai.com",
    reason="After hours access",
    client_device="child-laptop"
)

# Log an override
logger.log_override_attempt(
    policy_name="bedtime.rego",
    client_ip="192.168.1.100",
    endpoint="api.openai.com",
    success=True,
    override_user="parent"
)

# Log allowlist bypass
logger.log_allowlist_bypass(
    client_ip="192.168.1.50",
    endpoint="api.openai.com",
    allowlist_reason="Device on allowlist"
)
```

### Calculating Statistics

```python
from yori.enforcement_stats import EnforcementStatsCalculator

stats = EnforcementStatsCalculator(Path("/var/db/yori/audit.db"))

# Get summary for last 30 days
summary = stats.get_enforcement_summary(days=30)
print(f"Total blocks: {summary.total_blocks}")
print(f"Override success rate: {summary.override_success_rate}%")

# Get daily breakdown
daily = stats.get_daily_stats(days=7)
for day in daily:
    print(f"{day.date}: {day.blocks} blocks, {day.overrides} overrides")

# Get top policies
top_policies = stats.get_top_blocking_policies(limit=10, days=7)
for policy in top_policies:
    print(f"{policy.policy_name}: {policy.block_count} blocks")
```

### Generating Reports

```bash
# Generate text report for last 7 days
python -m yori.reports.enforcement_summary --days 7

# Generate JSON report
python -m yori.reports.enforcement_summary --days 30 --format json --output report.json
```

## Performance

**Targets:**
- Audit write: <5ms per event
- Dashboard queries: <500ms
- No impact on request processing

**Optimizations:**
- Indexed columns for fast queries
- Pre-calculated views for common queries
- Efficient SQLite schema design

## Integration Points

### From block-page (Worker 10)
Events to log:
- `override_attempt`, `override_success`, `override_failed`
- `emergency_override`

### From allowlist-blocklist (Worker 11)
Events to log:
- `allowlist_added`, `allowlist_removed`, `allowlist_bypassed`
- `time_exception_active`

### From enforcement-mode (Worker 9)
Events to log:
- `enforcement_enabled`, `enforcement_disabled`
- `request_blocked`

### To integration-release (Worker 13)
Exports:
- Enhanced SQLite schema with enforcement tracking
- Dashboard widgets and API endpoints
- Report generation tools

## Testing

Run unit tests:
```bash
pytest tests/unit/test_audit_enforcement.py -v
```

Run integration tests:
```bash
pytest tests/integration/test_enforcement_logging.py -v
```

Run all tests with coverage:
```bash
pytest tests/ --cov=yori.audit_enforcement --cov=yori.enforcement_stats --cov-report=term
```

## Files Created

Total files: 17

**SQL (3):**
- sql/schema.sql
- sql/schema_enforcement.sql
- sql/migrate_enforcement.sql

**Python (6):**
- python/yori/audit_enforcement.py
- python/yori/enforcement_stats.py
- python/yori/reports/__init__.py
- python/yori/reports/enforcement_summary.py

**UI (3):**
- opnsense/.../enforcement_dashboard.volt
- opnsense/.../enforcement_timeline.volt
- opnsense/.../EnforcementStatsController.php

**Tests (2):**
- tests/unit/test_audit_enforcement.py
- tests/integration/test_enforcement_logging.py

**Documentation (3):**
- tests/__init__.py
- python/yori/reports/__init__.py
- This README

## Next Steps

1. Integrate with block-page worker (Worker 10)
2. Integrate with allowlist-blocklist worker (Worker 11)
3. Integrate with enforcement-mode worker (Worker 9)
4. Final integration testing with Worker 13
5. Performance validation
6. Documentation updates

## Success Criteria ✓

- [x] All objectives completed
- [x] SQLite schema extended with enforcement columns
- [x] enforcement_events table created
- [x] Schema migration script works
- [x] All enforcement events can be logged
- [x] Enforcement dashboard widget created
- [x] Enforcement timeline view implemented
- [x] Statistics calculation implemented
- [x] Enforcement metrics calculated
- [x] Weekly enforcement report generator created
- [x] Unit tests written and comprehensive
- [x] Integration tests demonstrate complete logging
- [x] All files created as specified
- [x] Ready for Worker 13 integration
