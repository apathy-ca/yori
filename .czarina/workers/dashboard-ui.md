# Worker Identity: dashboard-ui

**Role:** Code
**Agent:** Windsurf
**Branch:** cz1/feat/dashboard-ui
**Phase:** 1
**Dependencies:** opnsense-plugin

## Mission

Build comprehensive web dashboard for LLM usage statistics, audit log viewer, and real-time monitoring. Create interactive charts and export capabilities.

## 🚀 YOUR FIRST ACTION

Examine OPNsense Bootstrap 5 theme, create dashboard page template in Volt, and implement first chart (requests last 24h) using Chart.js with SQLite query for data.

## Objectives

1. Create dashboard page layout (Bootstrap 5 grid)
2. Implement SQLite query functions in PHP (via PDO)
3. Add Chart.js library to plugin assets
4. Build dashboard widgets:

## Deliverables

Complete implementation of: Build comprehensive web dashboard for LLM usage statistics, audit log viewer, and real-time monitoring

## Dependencies from Upstream Workers

### From opnsense-plugin (Worker 3)

**Required Artifacts:**
- Plugin views directory: `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/`
- Bootstrap 5 theme and variables
- Template variables: `$service_status`, `$config_path`, `$database_path`, `$version`

### From python-proxy (Worker 2)

**Required Artifacts:**
- SQLite database: `/var/db/yori/audit.db`
- Table: `audit_events` with columns from PROJECT_PLAN.md
- View: `daily_stats` for aggregated queries

**Verification Before Starting:**
```bash
# Verify SQLite database exists and has data
sqlite3 /var/db/yori/audit.db "SELECT COUNT(*) FROM audit_events;"
# Expected: >0 (some test data)
```

## Interface Contract

### Exports for documentation (Worker 6)

**Dashboard Features to Document:**
- All charts and their data sources
- Filter capabilities (date range, endpoint, device)
- CSV export functionality
- Screenshot-worthy dashboard views

## Files to Create

**Volt Templates:**
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/dashboard.volt` - Main dashboard page
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/audit.volt` - Audit log viewer
- `opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/stats.volt` - Statistics summary

**PHP Controllers:**
- `opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/Api/StatsController.php` - API for statistics
- `opnsense/src/opnsense/mvc/app/controllers/OPNsense/YORI/Api/AuditController.php` - API for audit logs

**Assets:**
- `opnsense/src/opnsense/www/js/yori/dashboard.js` - Dashboard JavaScript
- `opnsense/src/opnsense/www/css/yori/dashboard.css` - Custom styles
- Chart.js library (CDN or bundled)

## Performance Targets

- **Page Load:** <2 seconds for dashboard with 100k+ audit records
- **Query Performance:** <500ms for all chart data queries
- **Export:** <5 seconds to generate CSV with 10k records

## Testing Requirements

**Manual Tests:**
- Dashboard displays all widgets correctly
- Charts render with real data from SQLite
- Filters work (date range, endpoint, device)
- CSV export generates valid file
- Pagination works in audit log viewer

**SQL Query Tests:**
- All queries use proper indexes
- Query performance measured with EXPLAIN
- Test with 100k+ audit records

## Verification Commands

### From Worker Branch (cz1/feat/dashboard-ui)

```bash
# Verify templates exist
ls -la opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/

# Test SQL queries directly
sqlite3 /var/db/yori/audit.db "
SELECT
  DATE(timestamp) as date,
  COUNT(*) as request_count
FROM audit_events
WHERE timestamp >= datetime('now', '-24 hours')
GROUP BY DATE(timestamp);
"

# Check dashboard JavaScript
cat opnsense/src/opnsense/www/js/yori/dashboard.js

# Verify Chart.js integration
grep -r "Chart.js" opnsense/src/opnsense/mvc/app/views/
```

### Integration Test (OPNsense VM)

```bash
# Navigate to dashboard in web UI
# URL: http://opnsense-ip/ui/yori/dashboard

# Verify charts display
# Expected: 4 charts (24h requests, endpoints, devices, alerts)

# Test filters
# Expected: Charts update when date range changes

# Test CSV export
# Expected: File downloads with audit_events_YYYYMMDD.csv
```

### Handoff Verification for Worker 6

Worker 6 should be able to:
```bash
# Take screenshots of dashboard for documentation
# Document all features: charts, filters, export

# Verify dashboard features list:
# - Requests last 24h (bar chart)
# - Top endpoints (pie chart)
# - Top devices (bar chart)
# - Recent alerts (table)
# - Audit log viewer (paginated table)
# - CSV export button
```

## Success Criteria

- [ ] All objectives completed
- [ ] All files created as specified above
- [ ] Dependencies verified (plugin structure, SQLite data)
- [ ] Dashboard displays all 4 charts correctly
- [ ] Audit log viewer with pagination works
- [ ] Search and filter capabilities functional
- [ ] CSV export generates valid files
- [ ] Statistics summary cards display data
- [ ] Performance targets met (<2s page load, <500ms queries)
- [ ] SQL queries optimized with indexes
- [ ] Bootstrap 5 styling consistent with OPNsense theme
- [ ] Code committed to branch cz1/feat/dashboard-ui
- [ ] Dashboard ready for screenshots (Worker 6)
