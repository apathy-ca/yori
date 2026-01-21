-- YORI Audit Database Schema (Phase 1)
-- SQLite database for LLM traffic audit logging

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601
    event_type TEXT NOT NULL,          -- 'request' | 'response' | 'block'

    -- Request details
    client_ip TEXT NOT NULL,
    client_device TEXT,                -- Device name (from DHCP)
    endpoint TEXT NOT NULL,            -- 'api.openai.com'
    http_method TEXT NOT NULL,         -- 'POST'
    http_path TEXT NOT NULL,           -- '/v1/chat/completions'

    -- Prompt analysis (privacy-aware)
    prompt_preview TEXT,               -- First 200 chars (optional)
    prompt_tokens INTEGER,
    contains_sensitive BOOLEAN,        -- PII detected

    -- Response
    response_status INTEGER,
    response_tokens INTEGER,
    response_duration_ms INTEGER,

    -- Policy
    policy_name TEXT,
    policy_result TEXT,                -- 'allow' | 'alert' | 'block'
    policy_reason TEXT,

    -- Metadata
    user_agent TEXT,
    request_id TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_client_ip ON audit_events(client_ip);
CREATE INDEX IF NOT EXISTS idx_endpoint ON audit_events(endpoint);
CREATE INDEX IF NOT EXISTS idx_policy_result ON audit_events(policy_result);

-- Statistics view
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
