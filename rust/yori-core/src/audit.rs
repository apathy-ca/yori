//! Audit logging primitives for LLM request tracking
//!
//! This module provides structured logging for LLM requests, responses, and policy decisions.
//! Logs are written to SQLite (for persistence) and exposed via Python for the web dashboard.
//!
//! # Design
//!
//! - **Structured**: JSON-formatted logs for easy parsing
//! - **Efficient**: Async writes to avoid blocking proxy
//! - **Privacy-aware**: Configurable PII redaction
//! - **Retention**: Automatic pruning of old logs (default 1 year)

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fmt;

/// Audit event type
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuditEventType {
    /// LLM request intercepted
    RequestReceived,

    /// Policy evaluation completed
    PolicyEvaluated,

    /// Request forwarded to LLM
    RequestForwarded,

    /// Response received from LLM
    ResponseReceived,

    /// Request blocked by policy
    RequestBlocked,

    /// Error during processing
    Error,
}

impl fmt::Display for AuditEventType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AuditEventType::RequestReceived => write!(f, "request_received"),
            AuditEventType::PolicyEvaluated => write!(f, "policy_evaluated"),
            AuditEventType::RequestForwarded => write!(f, "request_forwarded"),
            AuditEventType::ResponseReceived => write!(f, "response_received"),
            AuditEventType::RequestBlocked => write!(f, "request_blocked"),
            AuditEventType::Error => write!(f, "error"),
        }
    }
}

/// Audit event for LLM governance
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditEvent {
    /// Unique event ID
    pub event_id: String,

    /// Event timestamp
    pub timestamp: DateTime<Utc>,

    /// Event type
    pub event_type: AuditEventType,

    /// Client IP address
    pub client_ip: String,

    /// Target LLM endpoint (e.g., "api.openai.com")
    pub endpoint: String,

    /// HTTP method
    pub method: String,

    /// Request path
    pub path: String,

    /// User identifier (from policy or IP)
    pub user: Option<String>,

    /// Prompt preview (first 200 chars, may be redacted)
    pub prompt_preview: Option<String>,

    /// Policy decision (if applicable)
    pub policy_decision: Option<PolicyDecision>,

    /// Response status code (if applicable)
    pub response_status: Option<u16>,

    /// Response duration in milliseconds
    pub duration_ms: Option<u64>,

    /// Estimated token count
    pub tokens: Option<usize>,

    /// Error message (if event_type is Error)
    pub error: Option<String>,

    /// Additional metadata (JSON)
    pub metadata: Option<serde_json::Value>,
}

/// Policy evaluation decision
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyDecision {
    /// Whether request was allowed
    pub allow: bool,

    /// Policy that made the decision
    pub policy: String,

    /// Human-readable reason
    pub reason: String,

    /// Policy mode
    pub mode: String,

    /// Policy evaluation duration (microseconds)
    pub eval_duration_us: u64,
}

impl AuditEvent {
    /// Create a new audit event
    pub fn new(event_type: AuditEventType, client_ip: String, endpoint: String) -> Self {
        AuditEvent {
            event_id: uuid::Uuid::new_v4().to_string(),
            timestamp: Utc::now(),
            event_type,
            client_ip,
            endpoint,
            method: String::new(),
            path: String::new(),
            user: None,
            prompt_preview: None,
            policy_decision: None,
            response_status: None,
            duration_ms: None,
            tokens: None,
            error: None,
            metadata: None,
        }
    }

    /// Create a request received event
    pub fn request_received(
        client_ip: String,
        endpoint: String,
        method: String,
        path: String,
    ) -> Self {
        let mut event = AuditEvent::new(AuditEventType::RequestReceived, client_ip, endpoint);
        event.method = method;
        event.path = path;
        event
    }

    /// Create a policy evaluated event
    pub fn policy_evaluated(
        client_ip: String,
        endpoint: String,
        decision: PolicyDecision,
    ) -> Self {
        let mut event = AuditEvent::new(AuditEventType::PolicyEvaluated, client_ip, endpoint);
        event.policy_decision = Some(decision);
        event
    }

    /// Create a request blocked event
    pub fn request_blocked(client_ip: String, endpoint: String, reason: String) -> Self {
        let mut event = AuditEvent::new(AuditEventType::RequestBlocked, client_ip, endpoint);
        event.error = Some(reason);
        event
    }

    /// Create an error event
    pub fn error(client_ip: String, endpoint: String, error: String) -> Self {
        let mut event = AuditEvent::new(AuditEventType::Error, client_ip, endpoint);
        event.error = Some(error);
        event
    }

    /// Add prompt preview (redacted if necessary)
    pub fn with_prompt(mut self, prompt: String, redact: bool) -> Self {
        if redact {
            // Basic PII redaction (TODO: implement proper PII detection)
            self.prompt_preview = Some(format!("{}...", &prompt[..prompt.len().min(200)]));
        } else {
            self.prompt_preview = Some(prompt[..prompt.len().min(200)].to_string());
        }
        self
    }

    /// Add user identifier
    pub fn with_user(mut self, user: String) -> Self {
        self.user = Some(user);
        self
    }

    /// Add response details
    pub fn with_response(mut self, status: u16, duration_ms: u64, tokens: Option<usize>) -> Self {
        self.response_status = Some(status);
        self.duration_ms = Some(duration_ms);
        self.tokens = tokens;
        self
    }

    /// Convert to JSON string
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }

    /// Convert to JSON value
    pub fn to_json_value(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Audit logger configuration
#[derive(Debug, Clone)]
pub struct AuditConfig {
    /// Enable audit logging
    pub enabled: bool,

    /// Redact PII in prompts
    pub redact_pii: bool,

    /// Log request bodies
    pub log_request_bodies: bool,

    /// Log response bodies
    pub log_response_bodies: bool,

    /// Maximum prompt preview length
    pub max_preview_length: usize,

    /// Retention period in days
    pub retention_days: u32,
}

impl Default for AuditConfig {
    fn default() -> Self {
        AuditConfig {
            enabled: true,
            redact_pii: true,
            log_request_bodies: false,
            log_response_bodies: false,
            max_preview_length: 200,
            retention_days: 365,
        }
    }
}

/// Audit logger (stub implementation)
///
/// TODO: Implement actual logging to SQLite or file
/// For now, this just provides the data structures
pub struct AuditLogger {
    config: AuditConfig,
}

impl AuditLogger {
    /// Create a new audit logger
    pub fn new(config: AuditConfig) -> Self {
        AuditLogger { config }
    }

    /// Log an audit event
    pub fn log(&self, event: &AuditEvent) -> Result<(), Box<dyn std::error::Error>> {
        if !self.config.enabled {
            return Ok(());
        }

        // TODO: Write to SQLite database or file
        // For now, just write to tracing
        tracing::info!(
            event_type = %event.event_type,
            event_id = %event.event_id,
            client_ip = %event.client_ip,
            endpoint = %event.endpoint,
            "Audit event"
        );

        Ok(())
    }

    /// Prune old audit logs based on retention policy
    pub fn prune_old_logs(&self) -> Result<usize, Box<dyn std::error::Error>> {
        // TODO: Implement pruning logic
        Ok(0)
    }

    /// Get audit statistics
    pub fn stats(&self) -> AuditStats {
        // TODO: Implement stats collection
        AuditStats {
            total_events: 0,
            requests_received: 0,
            requests_blocked: 0,
            errors: 0,
            oldest_event: None,
            newest_event: None,
        }
    }
}

/// Audit statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditStats {
    /// Total number of events
    pub total_events: u64,

    /// Number of requests received
    pub requests_received: u64,

    /// Number of requests blocked
    pub requests_blocked: u64,

    /// Number of errors
    pub errors: u64,

    /// Timestamp of oldest event
    pub oldest_event: Option<DateTime<Utc>>,

    /// Timestamp of newest event
    pub newest_event: Option<DateTime<Utc>>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audit_event_creation() {
        let event = AuditEvent::request_received(
            "192.168.1.100".to_string(),
            "api.openai.com".to_string(),
            "POST".to_string(),
            "/v1/chat/completions".to_string(),
        );

        assert_eq!(event.event_type, AuditEventType::RequestReceived);
        assert_eq!(event.client_ip, "192.168.1.100");
        assert_eq!(event.endpoint, "api.openai.com");
        assert_eq!(event.method, "POST");
        assert_eq!(event.path, "/v1/chat/completions");
    }

    #[test]
    fn test_prompt_redaction() {
        let long_prompt = "a".repeat(500);
        let event = AuditEvent::request_received(
            "192.168.1.100".to_string(),
            "api.openai.com".to_string(),
            "POST".to_string(),
            "/v1/chat/completions".to_string(),
        )
        .with_prompt(long_prompt.clone(), true);

        let preview = event.prompt_preview.unwrap();
        assert!(preview.len() <= 203); // 200 chars + "..."
        assert!(preview.ends_with("..."));
    }

    #[test]
    fn test_policy_decision() {
        let decision = PolicyDecision {
            allow: false,
            policy: "bedtime".to_string(),
            reason: "Outside allowed hours".to_string(),
            mode: "enforce".to_string(),
            eval_duration_us: 250,
        };

        let event = AuditEvent::policy_evaluated(
            "192.168.1.100".to_string(),
            "api.openai.com".to_string(),
            decision.clone(),
        );

        assert_eq!(event.event_type, AuditEventType::PolicyEvaluated);
        assert!(event.policy_decision.is_some());

        let stored_decision = event.policy_decision.unwrap();
        assert_eq!(stored_decision.allow, false);
        assert_eq!(stored_decision.policy, "bedtime");
    }

    #[test]
    fn test_audit_event_json() {
        let event = AuditEvent::request_received(
            "192.168.1.100".to_string(),
            "api.openai.com".to_string(),
            "POST".to_string(),
            "/v1/chat/completions".to_string(),
        );

        let json = event.to_json();
        assert!(json.is_ok());

        let json_str = json.unwrap();
        assert!(json_str.contains("request_received"));
        assert!(json_str.contains("192.168.1.100"));
    }

    #[test]
    fn test_audit_logger() {
        let config = AuditConfig::default();
        let logger = AuditLogger::new(config);

        let event = AuditEvent::request_received(
            "192.168.1.100".to_string(),
            "api.openai.com".to_string(),
            "POST".to_string(),
            "/v1/chat/completions".to_string(),
        );

        let result = logger.log(&event);
        assert!(result.is_ok());
    }
}
