# YORI Dashboard Implementation

## Overview

This directory contains the complete web dashboard implementation for the YORI OPNsense plugin, providing LLM usage statistics, audit log viewing, and real-time monitoring capabilities.

## Architecture

### Components

1. **Backend (PHP)**
   - `StatsController.php` - Statistics API endpoints for charts and summary data
   - `AuditController.php` - Audit log search, filtering, and CSV export

2. **Frontend (Volt Templates)**
   - `dashboard.volt` - Main dashboard with charts and summary cards
   - `audit.volt` - Audit log viewer with search and filters
   - `stats.volt` - Detailed statistics and analytics

3. **Assets**
   - `dashboard.js` - Chart.js integration and AJAX data loading
   - `dashboard.css` - Bootstrap 5 extensions and custom styling

4. **Database**
   - `schema.sql` - SQLite schema with tables, indexes, and views

## Features

### Dashboard Page (`/ui/yori/dashboard`)

**Summary Cards:**
- Total Requests (all time)
- Requests Last 24 Hours
- Average Tokens per Request
- Total Policy Alerts

**Charts:**
- Requests Last 24 Hours (line chart)
- Top Endpoints (pie chart)
- Top Devices (horizontal bar chart)
- Peak Usage Hours (bar chart)
- Recent Alerts table

**Auto-refresh:** Every 60 seconds

### Audit Log Viewer (`/ui/yori/audit`)

**Features:**
- Paginated table view (25/50/100/250 per page)
- Advanced filtering:
  - Date range (from/to)
  - Endpoint selection
  - Client IP/Device
  - Event type (request/response/block)
  - Search in prompt preview and policy reason
- Event detail modal
- CSV export with filters
- Responsive design

### Statistics Page (`/ui/yori/stats`)

**Displays:**
- Overall statistics (total, 7 days, 24 hours, avg tokens)
- Endpoint distribution table
- Device statistics table
- Hourly usage heatmap
- Policy activity summary

## API Endpoints

### Statistics API (`/api/yori/stats/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `summary` | GET | Overall statistics summary |
| `last24h` | GET | Hourly requests for last 24 hours |
| `topEndpoints` | GET | Top 10 endpoints by request count |
| `topDevices` | GET | Top 10 devices by request count |
| `recentAlerts` | GET | Last 10 policy alerts/blocks |
| `hourlyDistribution` | GET | Requests by hour of day (0-23) |

### Audit API (`/api/yori/audit/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `search` | POST | Search audit events with filters and pagination |
| `get` | POST | Get single event details by ID |
| `export` | POST | Export audit events to CSV |
| `endpoints` | GET | Get list of unique endpoints for filters |
| `clients` | GET | Get list of unique client IPs for filters |

### API Response Format

All API endpoints return JSON with the following structure:

```json
{
  "status": "ok" | "error",
  "message": "Optional error message",
  "data": [...] | {...}
}
```

## Database Schema

### Main Table: `audit_events`

Stores all LLM API request/response events with the following key fields:

- `timestamp` - ISO 8601 timestamp
- `event_type` - request | response | block
- `client_ip` - Source IP address
- `client_device` - Device name (from DHCP)
- `endpoint` - LLM API endpoint (e.g., api.openai.com)
- `prompt_tokens` / `response_tokens` - Token counts
- `policy_result` - allow | alert | block
- `policy_reason` - Why policy triggered

### Views

- `daily_stats` - Daily aggregated statistics by endpoint
- `hourly_stats` - Hourly aggregated statistics
- `device_stats` - Per-device usage statistics
- `endpoint_stats` - Per-endpoint statistics
- `alert_events` - Filtered view of alerts and blocks

### Indexes

Optimized for dashboard queries:
- `idx_timestamp` - Time-based queries
- `idx_client_ip` - Device filtering
- `idx_endpoint` - Endpoint filtering
- `idx_policy_result` - Alert queries
- `idx_event_type` - Event type filtering

## Performance

### Query Optimization

- All queries use proper indexes
- Views pre-aggregate common statistics
- Pagination limits result sets
- CSV export capped at 10,000 records

### Targets (from PROJECT_PLAN.md)

- Page load: <2 seconds (with 100k+ records)
- Query performance: <500ms for all chart queries
- CSV export: <5 seconds (10k records)

## Security

### Input Validation

- All user inputs sanitized via Pydantic/PHP filters
- SQL injection prevented via PDO prepared statements
- XSS prevented via HTML escaping in JavaScript

### Authentication

- OPNsense session authentication (handled by framework)
- No additional authentication required

### Data Privacy

- Prompt preview limited to 200 characters (configurable)
- Can be disabled entirely in configuration
- No LLM API keys stored

## Integration

### Dependencies

**From opnsense-plugin (Worker 3):**
- Plugin directory structure
- Bootstrap 5 theme
- Template variables

**From python-proxy (Worker 2):**
- SQLite database at `/var/db/yori/audit.db`
- Table: `audit_events` with data
- View: `daily_stats`

### Handoff to documentation (Worker 6)

All dashboard features ready for screenshots:
- Main dashboard with all charts
- Audit log viewer with filters
- Statistics summary page
- CSV export functionality

## Testing

### Manual Tests

```bash
# 1. Verify templates exist
ls -la opnsense/src/opnsense/mvc/app/views/OPNsense/YORI/

# 2. Test SQL schema
sqlite3 /var/db/yori/audit.db < sql/schema.sql

# 3. Test SQL queries
sqlite3 /var/db/yori/audit.db "
SELECT
  strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
  COUNT(*) as count
FROM audit_events
WHERE timestamp >= datetime('now', '-24 hours')
  AND event_type = 'request'
GROUP BY hour;
"

# 4. Verify Chart.js integration
grep -r "Chart.js" opnsense/src/opnsense/mvc/app/views/
```

### Integration Test (on OPNsense VM)

1. Navigate to `http://opnsense-ip/ui/yori/dashboard`
2. Verify all 4 charts render
3. Check summary cards display data
4. Test auto-refresh (60 seconds)
5. Navigate to audit log viewer
6. Test filters (date range, endpoint, client)
7. Test pagination
8. Test CSV export
9. View statistics page

## File Structure

```
opnsense/
├── DASHBOARD_README.md              # This file
├── src/opnsense/
│   ├── mvc/app/
│   │   ├── controllers/OPNsense/YORI/Api/
│   │   │   ├── StatsController.php  # Statistics API (318 lines)
│   │   │   └── AuditController.php  # Audit log API (373 lines)
│   │   └── views/OPNsense/YORI/
│   │       ├── dashboard.volt       # Main dashboard (232 lines)
│   │       ├── audit.volt          # Audit log viewer (467 lines)
│   │       └── stats.volt          # Statistics page (416 lines)
│   └── www/
│       ├── js/yori/
│       │   └── dashboard.js        # Chart.js integration (442 lines)
│       └── css/yori/
│           └── dashboard.css       # Custom styles (211 lines)
sql/
└── schema.sql                      # Database schema (107 lines)

Total: 2,566 lines of code
```

## Technology Stack

- **Backend:** PHP 8.1+ with PDO
- **Frontend:** Bootstrap 5, jQuery, Chart.js 4.4.1
- **Database:** SQLite 3
- **Charts:** Chart.js (line, bar, doughnut)
- **Template Engine:** Volt (Phalcon)

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (responsive design)

## Accessibility

- Semantic HTML5
- ARIA labels on charts
- Keyboard navigation support
- Focus visible indicators
- Screen reader compatible

## Future Enhancements

- Real-time WebSocket updates
- Customizable dashboard widgets
- Advanced analytics (ML-based anomaly detection)
- Export to PDF/Excel
- Custom date range selection
- Chart drill-down capabilities
- Dashboard user preferences (saved filters, layouts)

## License

MIT License - Copyright (c) 2026 YORI Project

## Support

For issues or questions:
- GitHub Issues: https://github.com/apathy-ca/yori/issues
- Documentation: See docs/ directory in repository root
