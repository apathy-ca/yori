-- YORI SQLite Audit Database Schema
-- Path: /var/db/yori/audit.db
-- Purpose: Store LLM API request/response audit events for dashboard and reporting

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601 format
    event_type TEXT NOT NULL,          -- 'request' | 'response' | 'block'

    -- Request details
    client_ip TEXT NOT NULL,
    client_device TEXT,                -- Device name (from DHCP if available)
    endpoint TEXT NOT NULL,            -- e.g., 'api.openai.com'
    http_method TEXT NOT NULL,         -- 'POST', 'GET', etc.
    http_path TEXT NOT NULL,           -- e.g., '/v1/chat/completions'

    -- Prompt analysis (privacy-aware)
    prompt_preview TEXT,               -- First 200 chars (optional, can be disabled)
    prompt_tokens INTEGER,
    contains_sensitive BOOLEAN DEFAULT 0,  -- PII detected flag

    -- Response details
    response_status INTEGER,
    response_tokens INTEGER,
    response_duration_ms INTEGER,

    -- Policy evaluation
    policy_name TEXT,
    policy_result TEXT,                -- 'allow' | 'alert' | 'block'
    policy_reason TEXT,

    -- Metadata
    user_agent TEXT,
    request_id TEXT UNIQUE
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_client_ip ON audit_events(client_ip);
CREATE INDEX IF NOT EXISTS idx_endpoint ON audit_events(endpoint);
CREATE INDEX IF NOT EXISTS idx_policy_result ON audit_events(policy_result);
CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type);

-- Statistics view for efficient dashboard queries
CREATE VIEW IF NOT EXISTS daily_stats AS
SELECT
    DATE(timestamp) as date,
    endpoint,
    COUNT(*) as request_count,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(response_tokens) as total_response_tokens,
    AVG(response_duration_ms) as avg_duration_ms
FROM audit_events
WHERE event_type = 'request'
GROUP BY DATE(timestamp), endpoint;

-- Hourly statistics view for 24-hour charts
CREATE VIEW IF NOT EXISTS hourly_stats AS
SELECT
    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
    endpoint,
    COUNT(*) as request_count,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(response_tokens) as total_response_tokens,
    AVG(response_duration_ms) as avg_duration_ms
FROM audit_events
WHERE event_type = 'request'
GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp), endpoint;

-- Device statistics view
CREATE VIEW IF NOT EXISTS device_stats AS
SELECT
    client_ip,
    COALESCE(client_device, client_ip) as device_name,
    COUNT(*) as request_count,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(response_tokens) as total_response_tokens,
    MAX(timestamp) as last_seen
FROM audit_events
WHERE event_type = 'request'
GROUP BY client_ip, client_device;

-- Endpoint distribution view
CREATE VIEW IF NOT EXISTS endpoint_stats AS
SELECT
    endpoint,
    COUNT(*) as request_count,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(response_tokens) as total_response_tokens,
    AVG(response_duration_ms) as avg_duration_ms
FROM audit_events
WHERE event_type = 'request'
GROUP BY endpoint;

-- Alert events view
CREATE VIEW IF NOT EXISTS alert_events AS
SELECT
    id,
    timestamp,
    client_ip,
    endpoint,
    policy_name,
    policy_reason,
    prompt_preview
FROM audit_events
WHERE policy_result IN ('alert', 'block')
ORDER BY timestamp DESC;
