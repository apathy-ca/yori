#!/usr/bin/env python3
"""
Test enforcement statistics calculation
"""

import sqlite3
import tempfile
from pathlib import Path
import sys

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / 'python'))

from yori.audit_enforcement import EnforcementAuditLogger
from yori.enforcement_stats import EnforcementStatsCalculator

def test_statistics():
    """Test statistics calculation functionality"""

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    print(f"Creating test database: {db_path}")

    # Initialize schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

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

    # Initialize logger and stats calculator
    logger = EnforcementAuditLogger(db_path)
    stats = EnforcementStatsCalculator(db_path)

    print("\n1. Generating sample enforcement events...")

    # Generate 10 block events
    for i in range(10):
        policy = "bedtime.rego" if i < 6 else "privacy.rego"
        logger.log_block_event(
            policy_name=policy,
            client_ip=f"192.168.1.{100 + i % 3}",
            endpoint="api.openai.com",
            reason=f"Test block {i}",
            request_id=f"block-{i}"
        )

    # Generate 3 successful overrides
    for i in range(3):
        logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=True,
            override_user="parent",
            request_id=f"override-success-{i}"
        )

    # Generate 2 failed overrides
    for i in range(2):
        logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=False,
            override_user="child",
            request_id=f"override-fail-{i}"
        )

    # Generate 5 allowlist bypasses
    for i in range(5):
        logger.log_allowlist_bypass(
            client_ip="192.168.1.50",
            endpoint="api.openai.com",
            allowlist_reason="Device on allowlist",
            request_id=f"bypass-{i}"
        )

    print("✓ Generated 20 enforcement events")

    # Test enforcement summary
    print("\n2. Testing enforcement summary...")
    summary = stats.get_enforcement_summary(days=1)

    print(f"   Total blocks: {summary.total_blocks}")
    print(f"   Total overrides: {summary.total_overrides}")
    print(f"   Total bypasses: {summary.total_bypasses}")
    print(f"   Override success rate: {summary.override_success_rate}%")

    assert summary.total_blocks == 12, f"Expected 12 blocks (10 + 2 failed overrides), got {summary.total_blocks}"
    assert summary.total_overrides == 3, f"Expected 3 overrides, got {summary.total_overrides}"
    assert summary.total_bypasses == 5, f"Expected 5 bypasses, got {summary.total_bypasses}"
    assert summary.override_success_rate == 60.0, f"Expected 60% success rate, got {summary.override_success_rate}"
    print("✓ Enforcement summary verified")

    # Test top policies
    print("\n3. Testing top blocking policies...")
    top_policies = stats.get_top_blocking_policies(limit=10, days=1)

    print(f"   Found {len(top_policies)} policies")
    for i, policy in enumerate(top_policies, 1):
        print(f"   {i}. {policy.policy_name}: {policy.block_count} blocks, {policy.affected_clients} clients")

    assert len(top_policies) == 2, f"Expected 2 policies, got {len(top_policies)}"
    assert top_policies[0].policy_name == "bedtime.rego", "Top policy should be bedtime.rego"
    assert top_policies[0].block_count == 8, f"Expected 8 blocks for bedtime.rego (6 direct + 2 failed overrides), got {top_policies[0].block_count}"
    assert top_policies[1].policy_name == "privacy.rego", "Second policy should be privacy.rego"
    assert top_policies[1].block_count == 4, f"Expected 4 blocks for privacy.rego, got {top_policies[1].block_count}"
    print("✓ Top blocking policies verified")

    # Test recent blocks
    print("\n4. Testing recent blocks retrieval...")
    recent_blocks = stats.get_recent_blocks(limit=10)

    print(f"   Retrieved {len(recent_blocks)} recent blocks")
    assert len(recent_blocks) == 10, f"Expected 10 blocks, got {len(recent_blocks)}"
    print("✓ Recent blocks retrieval verified")

    # Test daily stats
    print("\n5. Testing daily statistics...")
    daily_stats = stats.get_daily_stats(days=7)

    print(f"   Retrieved {len(daily_stats)} days of statistics")
    if daily_stats:
        today_stats = daily_stats[0]
        print(f"   Today's stats: {today_stats.blocks} blocks, {today_stats.overrides} overrides, {today_stats.bypasses} bypasses")
        assert today_stats.blocks == 12, f"Expected 12 blocks today, got {today_stats.blocks}"
        assert today_stats.overrides == 3, f"Expected 3 overrides today, got {today_stats.overrides}"
        assert today_stats.bypasses == 5, f"Expected 5 bypasses today, got {today_stats.bypasses}"
    print("✓ Daily statistics verified")

    # Test enforcement timeline
    print("\n6. Testing enforcement timeline...")
    timeline = stats.get_enforcement_timeline(hours=24, limit=50)

    print(f"   Retrieved {len(timeline)} timeline events")
    assert len(timeline) == 20, f"Expected 20 timeline events, got {len(timeline)}"

    # Verify all events have icons
    for event in timeline:
        assert 'icon' in event, "Timeline event missing icon"
        assert 'display_text' in event, "Timeline event missing display_text"

    print("✓ Enforcement timeline verified")

    # Test mode change history
    print("\n7. Testing mode change history...")
    logger.log_mode_change(
        new_mode="enforce",
        user="admin",
        client_ip="192.168.1.1",
        details={"old_mode": "advisory"}
    )

    history = stats.get_enforcement_mode_history(limit=10)
    print(f"   Retrieved {len(history)} mode changes")
    assert len(history) == 1, f"Expected 1 mode change, got {len(history)}"
    assert history[0]['user'] == 'admin', "Mode change user mismatch"
    print("✓ Mode change history verified")

    # Cleanup
    db_path.unlink()
    print(f"\n✓ Test database cleaned up")

    print("\n" + "=" * 60)
    print("STATISTICS CALCULATION TEST: PASSED ✓")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_statistics()
    exit(0 if success else 1)
