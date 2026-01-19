-- YORI Audit Database Schema
-- SQLite schema for audit logging and statistics

-- Main audit events table
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT,
    source_ip TEXT NOT NULL,
    destination TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    provider TEXT NOT NULL,
    method TEXT NOT NULL,
    request_preview TEXT,
    response_preview TEXT,
    status_code INTEGER,
    policy_decision TEXT NOT NULL,
    policy_name TEXT,
    mode TEXT NOT NULL,
    latency_ms REAL,
    error TEXT,
    metadata TEXT  -- JSON blob for additional data
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_provider ON audit_events(provider);
CREATE INDEX IF NOT EXISTS idx_decision ON audit_events(policy_decision);
CREATE INDEX IF NOT EXISTS idx_source_ip ON audit_events(source_ip);
CREATE INDEX IF NOT EXISTS idx_user_id ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_endpoint ON audit_events(endpoint);

-- View for daily statistics (used by dashboard)
CREATE VIEW IF NOT EXISTS daily_stats AS
SELECT
    DATE(timestamp) as date,
    provider,
    policy_decision,
    COUNT(*) as request_count,
    AVG(latency_ms) as avg_latency_ms,
    COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as error_count
FROM audit_events
GROUP BY DATE(timestamp), provider, policy_decision;

-- View for hourly statistics
CREATE VIEW IF NOT EXISTS hourly_stats AS
SELECT
    STRFTIME('%Y-%m-%d %H:00:00', timestamp) as hour,
    provider,
    policy_decision,
    COUNT(*) as request_count,
    AVG(latency_ms) as avg_latency_ms
FROM audit_events
GROUP BY STRFTIME('%Y-%m-%d %H:00:00', timestamp), provider, policy_decision;

-- View for top endpoints
CREATE VIEW IF NOT EXISTS top_endpoints AS
SELECT
    endpoint,
    provider,
    COUNT(*) as request_count,
    AVG(latency_ms) as avg_latency_ms,
    COUNT(CASE WHEN policy_decision = 'block' THEN 1 END) as blocked_count
FROM audit_events
GROUP BY endpoint, provider
ORDER BY request_count DESC;

-- View for recent blocked requests
CREATE VIEW IF NOT EXISTS recent_blocks AS
SELECT
    timestamp,
    source_ip,
    user_id,
    endpoint,
    provider,
    policy_name,
    request_preview
FROM audit_events
WHERE policy_decision = 'block'
ORDER BY timestamp DESC
LIMIT 100;
