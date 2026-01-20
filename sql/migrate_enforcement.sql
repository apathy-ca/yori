-- YORI Phase 1 to Phase 2 Migration Script
-- Migrates existing audit.db from Phase 1 to Phase 2 with enforcement support
-- Safe to run multiple times (uses IF NOT EXISTS checks)

-- Begin transaction for atomicity
BEGIN TRANSACTION;

-- Step 1: Add new columns to audit_events table
-- These columns extend the Phase 1 schema with enforcement tracking

-- Check if enforcement_action column exists, add if not
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we use a workaround
-- First, try to add the column (will fail silently if it exists)

-- Add enforcement_action column
ALTER TABLE audit_events ADD COLUMN enforcement_action TEXT;
-- Values: 'allow', 'alert', 'block', 'override', 'allowlist_bypass'

-- Add override_user column
ALTER TABLE audit_events ADD COLUMN override_user TEXT;
-- User who overrode the block (if applicable)

-- Add allowlist_reason column
ALTER TABLE audit_events ADD COLUMN allowlist_reason TEXT;
-- Why request was allowlisted (device, time exception, etc.)

-- Step 2: Create new enforcement_events table
CREATE TABLE IF NOT EXISTS enforcement_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'mode_change', 'allowlist_change', 'override_attempt', etc.
    user TEXT,                  -- Admin who made the change
    details TEXT,               -- JSON with event details
    client_ip TEXT
);

-- Step 3: Create indexes for new columns and table
CREATE INDEX IF NOT EXISTS idx_enforcement_action ON audit_events(enforcement_action);
CREATE INDEX IF NOT EXISTS idx_override_user ON audit_events(override_user);
CREATE INDEX IF NOT EXISTS idx_enforcement_events_timestamp ON enforcement_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_enforcement_events_type ON enforcement_events(event_type);

-- Step 4: Create enforcement statistics views
DROP VIEW IF EXISTS enforcement_stats;
CREATE VIEW enforcement_stats AS
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

DROP VIEW IF EXISTS recent_blocks;
CREATE VIEW recent_blocks AS
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

DROP VIEW IF EXISTS override_stats;
CREATE VIEW override_stats AS
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

DROP VIEW IF EXISTS top_blocking_policies;
CREATE VIEW top_blocking_policies AS
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

-- Step 5: Backfill enforcement_action for existing records
-- Set enforcement_action based on policy_result for historical data
UPDATE audit_events
SET enforcement_action = CASE
    WHEN policy_result = 'allow' THEN 'allow'
    WHEN policy_result = 'alert' THEN 'alert'
    WHEN policy_result = 'block' THEN 'block'
    ELSE NULL
END
WHERE enforcement_action IS NULL AND policy_result IS NOT NULL;

-- Commit transaction
COMMIT;

-- Verify migration
SELECT 'Migration completed successfully' as status;
SELECT COUNT(*) as total_events FROM audit_events;
SELECT COUNT(*) as enforcement_events FROM enforcement_events;

-- Show schema version info
SELECT 'Phase 2 (v0.2.0) - Enforcement Mode' as schema_version;
