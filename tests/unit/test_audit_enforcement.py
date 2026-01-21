"""
Unit tests for YORI enforcement audit logging
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime

from yori.audit_enforcement import EnforcementAuditLogger


@pytest.fixture
def temp_db():
    """Create temporary test database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Initialize schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create basic audit_events table
    cursor.execute("""
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            client_ip TEXT NOT NULL,
            client_device TEXT,
            endpoint TEXT NOT NULL,
            http_method TEXT NOT NULL,
            http_path TEXT NOT NULL,
            policy_name TEXT,
            policy_result TEXT,
            policy_reason TEXT,
            enforcement_action TEXT,
            override_user TEXT,
            allowlist_reason TEXT,
            user_agent TEXT,
            request_id TEXT UNIQUE,
            prompt_preview TEXT,
            prompt_tokens INTEGER,
            contains_sensitive BOOLEAN,
            response_status INTEGER,
            response_tokens INTEGER,
            response_duration_ms INTEGER
        )
    """)

    # Create enforcement_events table
    cursor.execute("""
        CREATE TABLE enforcement_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            user TEXT,
            details TEXT,
            client_ip TEXT
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink()


class TestEnforcementAuditLogger:
    """Test enforcement audit logger"""

    def test_init(self, temp_db):
        """Test logger initialization"""
        logger = EnforcementAuditLogger(temp_db)
        assert logger.database_path == temp_db

    def test_log_block_event(self, temp_db):
        """Test logging a block event"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_block_event(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            reason="After hours access",
            client_device="child-laptop",
            request_id="test-123",
        )

        assert event_id > 0

        # Verify event was logged
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["event_type"] == "request_blocked"
        assert row["enforcement_action"] == "block"
        assert row["policy_name"] == "bedtime.rego"
        assert row["client_ip"] == "192.168.1.100"
        assert row["client_device"] == "child-laptop"
        assert row["endpoint"] == "api.openai.com"
        assert row["policy_reason"] == "After hours access"
        assert row["request_id"] == "test-123"

    def test_log_override_success(self, temp_db):
        """Test logging a successful override"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=True,
            override_user="parent",
            request_id="test-456",
        )

        assert event_id > 0

        # Verify event
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["event_type"] == "override_success"
        assert row["enforcement_action"] == "override"
        assert row["override_user"] == "parent"

    def test_log_override_failed(self, temp_db):
        """Test logging a failed override"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=False,
            override_user="child",
            request_id="test-789",
        )

        assert event_id > 0

        # Verify event
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["event_type"] == "override_failed"
        assert row["enforcement_action"] == "block"

    def test_log_allowlist_bypass(self, temp_db):
        """Test logging allowlist bypass"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_allowlist_bypass(
            client_ip="192.168.1.50",
            endpoint="api.openai.com",
            allowlist_reason="Device on allowlist",
            client_device="parent-phone",
            request_id="test-bypass-1",
        )

        assert event_id > 0

        # Verify event
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["event_type"] == "allowlist_bypassed"
        assert row["enforcement_action"] == "allowlist_bypass"
        assert row["allowlist_reason"] == "Device on allowlist"

    def test_log_mode_change(self, temp_db):
        """Test logging enforcement mode change"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_mode_change(
            new_mode="enforce",
            user="admin",
            client_ip="192.168.1.1",
            details={"old_mode": "advisory", "reason": "Testing enforcement"},
        )

        assert event_id > 0

        # Verify event
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM enforcement_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["event_type"] == "enforcement_mode_change"
        assert row["user"] == "admin"
        assert "old_mode" in row["details"]

    def test_log_allowlist_change(self, temp_db):
        """Test logging allowlist change"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_allowlist_change(
            change_type="added",
            device_or_ip="parent-phone",
            user="admin",
            client_ip="192.168.1.1",
            details={"mac_address": "00:11:22:33:44:55"},
        )

        assert event_id > 0

        # Verify event
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM enforcement_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["event_type"] == "allowlist_added"
        assert row["user"] == "admin"

    def test_log_emergency_override(self, temp_db):
        """Test logging emergency override"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_emergency_override(
            user="admin",
            client_ip="192.168.1.1",
            details={"duration_minutes": 30, "reason": "System maintenance"},
        )

        assert event_id > 0

        # Verify event
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM enforcement_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["event_type"] == "emergency_override"
        assert row["user"] == "admin"

    def test_log_enforcement_event_generic(self, temp_db):
        """Test generic enforcement event logging"""
        logger = EnforcementAuditLogger(temp_db)

        event_id = logger.log_enforcement_event(
            event_type="custom_event",
            policy_name="custom.rego",
            client_ip="192.168.1.200",
            endpoint="api.anthropic.com",
            enforcement_action="alert",
            reason="Custom test reason",
        )

        assert event_id > 0

        # Verify event
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_events WHERE id = ?", (event_id,)
        )
        row = cursor.fetchone()
        conn.close()

        assert row["event_type"] == "custom_event"
        assert row["enforcement_action"] == "alert"
