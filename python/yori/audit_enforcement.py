"""
YORI Enforcement Audit Logging

Enhanced audit logging for Phase 2 enforcement mode.
Captures blocks, overrides, allowlist bypasses, and enforcement events.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EnforcementAuditLogger:
    """Handles enforcement-specific audit logging to SQLite"""

    def __init__(self, database_path: Path):
        """
        Initialize enforcement audit logger.

        Args:
            database_path: Path to SQLite audit database
        """
        self.database_path = database_path
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Ensure database directory exists"""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.database_path))
        conn.row_factory = sqlite3.Row
        return conn

    def log_enforcement_event(
        self,
        event_type: str,
        policy_name: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_device: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: str = "POST",
        http_path: str = "/",
        enforcement_action: str = "allow",
        override_user: Optional[str] = None,
        allowlist_reason: Optional[str] = None,
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> int:
        """
        Log an enforcement-related event to audit_events table.

        Args:
            event_type: Type of event ('request_blocked', 'override_success', etc.)
            policy_name: Name of policy that triggered the event
            client_ip: IP address of client
            client_device: Device name (from DHCP)
            endpoint: LLM endpoint (e.g., 'api.openai.com')
            http_method: HTTP method
            http_path: HTTP path
            enforcement_action: Action taken ('allow', 'alert', 'block', 'override', 'allowlist_bypass')
            override_user: User who performed override (if applicable)
            allowlist_reason: Reason for allowlist bypass (if applicable)
            reason: Human-readable reason for the action
            request_id: Unique request ID
            user_agent: User agent string

        Returns:
            ID of inserted record
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_events (
                    timestamp,
                    event_type,
                    client_ip,
                    client_device,
                    endpoint,
                    http_method,
                    http_path,
                    policy_name,
                    policy_result,
                    policy_reason,
                    enforcement_action,
                    override_user,
                    allowlist_reason,
                    user_agent,
                    request_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    event_type,
                    client_ip or "unknown",
                    client_device,
                    endpoint or "unknown",
                    http_method,
                    http_path,
                    policy_name,
                    enforcement_action,  # policy_result matches enforcement_action
                    reason,
                    enforcement_action,
                    override_user,
                    allowlist_reason,
                    user_agent,
                    request_id,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid

        logger.info(
            f"Enforcement event logged: {event_type} - {enforcement_action} "
            f"(policy: {policy_name}, client: {client_ip})"
        )
        return event_id

    def log_block_event(
        self,
        policy_name: str,
        client_ip: str,
        endpoint: str,
        reason: str,
        client_device: Optional[str] = None,
        http_path: str = "/v1/chat/completions",
        request_id: Optional[str] = None,
    ) -> int:
        """
        Log a request block event.

        Args:
            policy_name: Name of policy that blocked the request
            client_ip: IP address of client
            endpoint: LLM endpoint
            reason: Reason for block
            client_device: Device name
            http_path: HTTP path
            request_id: Unique request ID

        Returns:
            ID of inserted record
        """
        return self.log_enforcement_event(
            event_type="request_blocked",
            policy_name=policy_name,
            client_ip=client_ip,
            client_device=client_device,
            endpoint=endpoint,
            http_path=http_path,
            enforcement_action="block",
            reason=reason,
            request_id=request_id,
        )

    def log_override_attempt(
        self,
        policy_name: str,
        client_ip: str,
        endpoint: str,
        success: bool,
        override_user: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> int:
        """
        Log an override attempt.

        Args:
            policy_name: Name of policy being overridden
            client_ip: IP address of client
            endpoint: LLM endpoint
            success: Whether override was successful
            override_user: User who attempted override
            request_id: Unique request ID

        Returns:
            ID of inserted record
        """
        event_type = "override_success" if success else "override_failed"
        enforcement_action = "override" if success else "block"

        return self.log_enforcement_event(
            event_type=event_type,
            policy_name=policy_name,
            client_ip=client_ip,
            endpoint=endpoint,
            enforcement_action=enforcement_action,
            override_user=override_user,
            reason=f"Override {'successful' if success else 'failed'}",
            request_id=request_id,
        )

    def log_allowlist_bypass(
        self,
        client_ip: str,
        endpoint: str,
        allowlist_reason: str,
        client_device: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> int:
        """
        Log an allowlist bypass event.

        Args:
            client_ip: IP address of client
            endpoint: LLM endpoint
            allowlist_reason: Reason for bypass (device, time exception, etc.)
            client_device: Device name
            request_id: Unique request ID

        Returns:
            ID of inserted record
        """
        return self.log_enforcement_event(
            event_type="allowlist_bypassed",
            client_ip=client_ip,
            client_device=client_device,
            endpoint=endpoint,
            enforcement_action="allowlist_bypass",
            allowlist_reason=allowlist_reason,
            reason=f"Allowlist bypass: {allowlist_reason}",
            request_id=request_id,
        )

    def log_mode_change(
        self,
        new_mode: str,
        user: Optional[str] = None,
        client_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Log an enforcement mode change event.

        Args:
            new_mode: New enforcement mode ('observe', 'advisory', 'enforce')
            user: Admin user who made the change
            client_ip: IP address of admin
            details: Additional details (old mode, reason, etc.)

        Returns:
            ID of inserted record
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        details_json = json.dumps(details) if details else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO enforcement_events (
                    timestamp,
                    event_type,
                    user,
                    details,
                    client_ip
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    "enforcement_mode_change",
                    user,
                    details_json,
                    client_ip,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid

        logger.info(f"Mode change logged: {new_mode} by {user or 'unknown'}")
        return event_id

    def log_allowlist_change(
        self,
        change_type: str,
        device_or_ip: str,
        user: Optional[str] = None,
        client_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Log an allowlist change event.

        Args:
            change_type: Type of change ('added', 'removed')
            device_or_ip: Device name or IP being added/removed
            user: Admin user who made the change
            client_ip: IP address of admin
            details: Additional details (time exceptions, etc.)

        Returns:
            ID of inserted record
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        details_json = json.dumps(details) if details else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO enforcement_events (
                    timestamp,
                    event_type,
                    user,
                    details,
                    client_ip
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    f"allowlist_{change_type}",
                    user,
                    details_json,
                    client_ip,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid

        logger.info(
            f"Allowlist change logged: {change_type} {device_or_ip} by {user or 'unknown'}"
        )
        return event_id

    def log_emergency_override(
        self,
        user: str,
        client_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Log an emergency override activation.

        Args:
            user: Admin user who activated emergency override
            client_ip: IP address of admin
            details: Additional details (duration, reason, etc.)

        Returns:
            ID of inserted record
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        details_json = json.dumps(details) if details else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO enforcement_events (
                    timestamp,
                    event_type,
                    user,
                    details,
                    client_ip
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    "emergency_override",
                    user,
                    details_json,
                    client_ip,
                ),
            )
            conn.commit()
            event_id = cursor.lastrowid

        logger.warning(f"Emergency override logged by {user}")
        return event_id

    def log_request(
        self,
        client_ip: str,
        request_path: str,
        request_method: str,
        upstream_host: str,
        headers: Optional[Dict[str, str]] = None,
        body_preview: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log a proxied request event.

        Args:
            client_ip: IP address of client
            request_path: HTTP path being requested
            request_method: HTTP method (GET, POST, etc.)
            upstream_host: Upstream host being proxied to
            headers: Request headers dictionary
            body_preview: Preview of request body
            request_id: Unique request ID

        Returns:
            ID of inserted record, or None if logging fails
        """
        try:
            user_agent = headers.get("user-agent") if headers else None

            return self.log_enforcement_event(
                event_type="request_forwarded",
                client_ip=client_ip,
                endpoint=upstream_host,
                http_method=request_method,
                http_path=request_path,
                enforcement_action="allow",
                reason="Request forwarded to upstream",
                request_id=request_id,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"Failed to log request event: {e}")
            return None

    def log_response(
        self,
        client_ip: str,
        status_code: int,
        duration_ms: float,
        upstream_host: str,
        request_path: str = "/",
        request_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log a response event after proxying to upstream.

        Args:
            client_ip: IP address of client
            status_code: HTTP status code from upstream
            duration_ms: Request duration in milliseconds
            upstream_host: Upstream host that responded
            request_path: HTTP path that was requested
            request_id: Unique request ID

        Returns:
            ID of inserted record, or None if logging fails
        """
        try:
            reason = f"Response received: {status_code} ({duration_ms:.2f}ms)"

            return self.log_enforcement_event(
                event_type="response_received",
                client_ip=client_ip,
                endpoint=upstream_host,
                http_path=request_path,
                enforcement_action="allow",
                reason=reason,
                request_id=request_id,
            )
        except Exception as e:
            logger.error(f"Failed to log response event: {e}")
            return None

    def log_block(
        self,
        client_ip: str,
        policy_name: str,
        reason: str,
        request_path: str,
        request_method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        body_preview: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log a request block event.

        Args:
            client_ip: IP address of client
            policy_name: Name of policy that blocked the request
            reason: Reason for block
            request_path: HTTP path that was blocked
            request_method: HTTP method
            headers: Request headers dictionary
            body_preview: Preview of request body
            request_id: Unique request ID

        Returns:
            ID of inserted record, or None if logging fails
        """
        try:
            user_agent = headers.get("user-agent") if headers else None

            return self.log_enforcement_event(
                event_type="request_blocked",
                policy_name=policy_name,
                client_ip=client_ip,
                endpoint="blocked",
                http_method=request_method,
                http_path=request_path,
                enforcement_action="block",
                reason=reason,
                request_id=request_id,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"Failed to log block event: {e}")
            return None
