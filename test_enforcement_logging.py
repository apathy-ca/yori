#!/usr/bin/env python3
"""
Test enforcement logging functionality end-to-end
"""

import sqlite3
import tempfile
from pathlib import Path
import sys

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / 'python'))

from yori.audit_enforcement import EnforcementAuditLogger

def test_enforcement_logging():
    """Test enforcement logging functionality"""

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    print(f"Creating test database: {db_path}")

    # Initialize schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create audit_events table with enforcement columns
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

    print("\n1. Testing EnforcementAuditLogger initialization...")
    logger = EnforcementAuditLogger(db_path)
    print("✓ Logger initialized")

    # Test block event logging
    print("\n2. Testing block event logging...")
    block_id = logger.log_block_event(
        policy_name="bedtime.rego",
        client_ip="192.168.1.100",
        endpoint="api.openai.com",
        reason="After hours access (10:30 PM)",
        client_device="child-laptop",
        request_id="test-block-1"
    )
    print(f"✓ Block event logged (ID: {block_id})")

    # Verify block event
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_events WHERE id = ?", (block_id,))
    row = cursor.fetchone()

    assert row['event_type'] == 'request_blocked', "Event type mismatch"
    assert row['enforcement_action'] == 'block', "Enforcement action mismatch"
    assert row['policy_name'] == 'bedtime.rego', "Policy name mismatch"
    print("✓ Block event verified in database")

    # Test override attempt (success)
    print("\n3. Testing successful override...")
    override_id = logger.log_override_attempt(
        policy_name="bedtime.rego",
        client_ip="192.168.1.100",
        endpoint="api.openai.com",
        success=True,
        override_user="parent",
        request_id="test-override-1"
    )
    print(f"✓ Override success logged (ID: {override_id})")

    cursor.execute("SELECT * FROM audit_events WHERE id = ?", (override_id,))
    row = cursor.fetchone()
    assert row['event_type'] == 'override_success', "Override success event type mismatch"
    assert row['enforcement_action'] == 'override', "Override action mismatch"
    assert row['override_user'] == 'parent', "Override user mismatch"
    print("✓ Override success verified")

    # Test override attempt (failure)
    print("\n4. Testing failed override...")
    failed_id = logger.log_override_attempt(
        policy_name="bedtime.rego",
        client_ip="192.168.1.100",
        endpoint="api.openai.com",
        success=False,
        override_user="child",
        request_id="test-override-fail-1"
    )
    print(f"✓ Override failure logged (ID: {failed_id})")

    cursor.execute("SELECT * FROM audit_events WHERE id = ?", (failed_id,))
    row = cursor.fetchone()
    assert row['event_type'] == 'override_failed', "Override failed event type mismatch"
    assert row['enforcement_action'] == 'block', "Failed override should remain blocked"
    print("✓ Override failure verified")

    # Test allowlist bypass
    print("\n5. Testing allowlist bypass...")
    bypass_id = logger.log_allowlist_bypass(
        client_ip="192.168.1.50",
        endpoint="api.openai.com",
        allowlist_reason="Device on allowlist",
        client_device="parent-phone",
        request_id="test-bypass-1"
    )
    print(f"✓ Allowlist bypass logged (ID: {bypass_id})")

    cursor.execute("SELECT * FROM audit_events WHERE id = ?", (bypass_id,))
    row = cursor.fetchone()
    assert row['event_type'] == 'allowlist_bypassed', "Bypass event type mismatch"
    assert row['enforcement_action'] == 'allowlist_bypass', "Bypass action mismatch"
    assert row['allowlist_reason'] == 'Device on allowlist', "Bypass reason mismatch"
    print("✓ Allowlist bypass verified")

    # Test mode change
    print("\n6. Testing mode change logging...")
    mode_id = logger.log_mode_change(
        new_mode="enforce",
        user="admin",
        client_ip="192.168.1.1",
        details={"old_mode": "advisory", "reason": "Testing enforcement mode"}
    )
    print(f"✓ Mode change logged (ID: {mode_id})")

    cursor.execute("SELECT * FROM enforcement_events WHERE id = ?", (mode_id,))
    row = cursor.fetchone()
    assert row['event_type'] == 'enforcement_mode_change', "Mode change event type mismatch"
    assert row['user'] == 'admin', "Mode change user mismatch"
    print("✓ Mode change verified")

    # Test allowlist change
    print("\n7. Testing allowlist change logging...")
    allowlist_change_id = logger.log_allowlist_change(
        change_type="added",
        device_or_ip="parent-phone",
        user="admin",
        client_ip="192.168.1.1",
        details={"mac_address": "00:11:22:33:44:55"}
    )
    print(f"✓ Allowlist change logged (ID: {allowlist_change_id})")

    cursor.execute("SELECT * FROM enforcement_events WHERE id = ?", (allowlist_change_id,))
    row = cursor.fetchone()
    assert row['event_type'] == 'allowlist_added', "Allowlist change event type mismatch"
    print("✓ Allowlist change verified")

    # Test emergency override
    print("\n8. Testing emergency override logging...")
    emergency_id = logger.log_emergency_override(
        user="admin",
        client_ip="192.168.1.1",
        details={"duration_minutes": 30, "reason": "System maintenance"}
    )
    print(f"✓ Emergency override logged (ID: {emergency_id})")

    cursor.execute("SELECT * FROM enforcement_events WHERE id = ?", (emergency_id,))
    row = cursor.fetchone()
    assert row['event_type'] == 'emergency_override', "Emergency override event type mismatch"
    print("✓ Emergency override verified")

    # Summary
    print("\n9. Verifying event summary...")
    cursor.execute("SELECT COUNT(*) FROM audit_events")
    audit_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM enforcement_events")
    enforcement_count = cursor.fetchone()[0]

    print(f"✓ Total audit_events: {audit_count}")
    print(f"✓ Total enforcement_events: {enforcement_count}")

    assert audit_count == 4, f"Expected 4 audit events, got {audit_count}"
    assert enforcement_count == 3, f"Expected 3 enforcement events, got {enforcement_count}"

    conn.close()

    # Cleanup
    db_path.unlink()
    print(f"\n✓ Test database cleaned up")

    print("\n" + "=" * 60)
    print("ENFORCEMENT LOGGING TEST: PASSED ✓")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_enforcement_logging()
    exit(0 if success else 1)
