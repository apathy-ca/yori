-- YORI Enforcement Schema Additions (Phase 2)
-- Extends Phase 1 audit schema with enforcement-specific columns and tables

-- Add enforcement columns to existing audit_events table
ALTER TABLE audit_events ADD COLUMN enforcement_action TEXT;
-- Values: 'allow', 'alert', 'block', 'override', 'allowlist_bypass'

ALTER TABLE audit_events ADD COLUMN override_user TEXT;
-- User who overrode the block (if applicable)

ALTER TABLE audit_events ADD COLUMN allowlist_reason TEXT;
-- Why request was allowlisted (device, time exception, etc.)

-- New enforcement_events table for tracking enforcement-related configuration changes
CREATE TABLE IF NOT EXISTS enforcement_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'mode_change', 'allowlist_change', 'override_attempt', etc.
    user TEXT,                  -- Admin who made the change
    details TEXT,               -- JSON with event details
    client_ip TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_enforcement_action ON audit_events(enforcement_action);
CREATE INDEX IF NOT EXISTS idx_override_user ON audit_events(override_user);
CREATE INDEX IF NOT EXISTS idx_enforcement_events_timestamp ON enforcement_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_enforcement_events_type ON enforcement_events(event_type);

-- Enforcement statistics view
CREATE VIEW IF NOT EXISTS enforcement_stats AS
SELECT
    DATE(timestamp) as date,
    COUNT(CASE WHEN enforcement_action = 'block' THEN 1 END) as blocks,
    COUNT(CASE WHEN enforcement_action = 'override' THEN 1 END) as overrides,
    COUNT(CASE WHEN enforcement_action = 'allowlist_bypass' THEN 1 END) as bypasses,
    COUNT(CASE WHEN enforcement_action = 'alert' THEN 1 END) as alerts,
    COUNT(CASE WHEN enforcement_action = 'allow' THEN 1 END) as allows
FROM audit_events
WHERE timestamp >= date('now', '-30 days')
GROUP BY DATE(timestamp);

-- Recent blocks view for dashboard widget
CREATE VIEW IF NOT EXISTS recent_blocks AS
SELECT
    timestamp,
    client_ip,
    client_device,
    endpoint,
    policy_name,
    policy_reason,
    enforcement_action,
    override_user
FROM audit_events
WHERE enforcement_action IN ('block', 'override')
ORDER BY timestamp DESC
LIMIT 50;

-- Override success rate view
CREATE VIEW IF NOT EXISTS override_stats AS
SELECT
    DATE(timestamp) as date,
    COUNT(*) as total_override_attempts,
    COUNT(CASE WHEN enforcement_action = 'override' THEN 1 END) as successful_overrides,
    ROUND(CAST(COUNT(CASE WHEN enforcement_action = 'override' THEN 1 END) AS FLOAT) /
          CAST(COUNT(*) AS FLOAT) * 100, 2) as success_rate
FROM audit_events
WHERE event_type IN ('override_attempt', 'override_success', 'override_failed')
  AND timestamp >= date('now', '-30 days')
GROUP BY DATE(timestamp);

-- Top blocking policies view
CREATE VIEW IF NOT EXISTS top_blocking_policies AS
SELECT
    policy_name,
    COUNT(*) as block_count,
    COUNT(DISTINCT client_ip) as affected_clients
FROM audit_events
WHERE enforcement_action = 'block'
  AND timestamp >= date('now', '-7 days')
GROUP BY policy_name
ORDER BY block_count DESC
LIMIT 10;
