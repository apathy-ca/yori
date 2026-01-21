"""
Integration tests for YORI enforcement logging

Tests the complete enforcement logging flow including:
- Block events
- Override events
- Allowlist bypasses
- Mode changes
- Statistics calculation
- Report generation
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from yori.audit_enforcement import EnforcementAuditLogger
from yori.enforcement_stats import EnforcementStatsCalculator
from yori.reports.enforcement_summary import EnforcementReportGenerator


@pytest.fixture
def test_database():
    """Create test database with full schema"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Initialize with full schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create audit_events table with all columns
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

    # Create indexes
    cursor.execute("CREATE INDEX idx_timestamp ON audit_events(timestamp)")
    cursor.execute("CREATE INDEX idx_enforcement_action ON audit_events(enforcement_action)")

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink()


class TestEnforcementLoggingIntegration:
    """Integration tests for enforcement logging"""

    def test_complete_enforcement_flow(self, test_database):
        """Test complete enforcement flow with multiple events"""
        logger = EnforcementAuditLogger(test_database)

        # Scenario: User tries to access LLM after bedtime
        # 1. Request is blocked
        block_id = logger.log_block_event(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            reason="After hours access (10:30 PM)",
            client_device="child-laptop",
            request_id="req-001",
        )
        assert block_id > 0

        # 2. User attempts override with wrong password
        failed_override_id = logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=False,
            override_user="child",
            request_id="req-002",
        )
        assert failed_override_id > 0

        # 3. User attempts override with correct password
        success_override_id = logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=True,
            override_user="parent",
            request_id="req-003",
        )
        assert success_override_id > 0

        # Verify all events were logged
        conn = sqlite3.connect(str(test_database))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_events")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 3

    def test_statistics_calculation(self, test_database):
        """Test statistics calculation with sample data"""
        logger = EnforcementAuditLogger(test_database)
        stats = EnforcementStatsCalculator(test_database)

        # Generate sample enforcement events
        # 10 blocks
        for i in range(10):
            logger.log_block_event(
                policy_name="bedtime.rego" if i < 5 else "privacy.rego",
                client_ip=f"192.168.1.{100 + i}",
                endpoint="api.openai.com",
                reason="Test block",
                request_id=f"block-{i}",
            )

        # 3 successful overrides
        for i in range(3):
            logger.log_override_attempt(
                policy_name="bedtime.rego",
                client_ip="192.168.1.100",
                endpoint="api.openai.com",
                success=True,
                override_user="parent",
                request_id=f"override-success-{i}",
            )

        # 2 failed overrides
        for i in range(2):
            logger.log_override_attempt(
                policy_name="bedtime.rego",
                client_ip="192.168.1.100",
                endpoint="api.openai.com",
                success=False,
                override_user="child",
                request_id=f"override-fail-{i}",
            )

        # 5 allowlist bypasses
        for i in range(5):
            logger.log_allowlist_bypass(
                client_ip="192.168.1.50",
                endpoint="api.openai.com",
                allowlist_reason="Device on allowlist",
                request_id=f"bypass-{i}",
            )

        # Get summary
        summary = stats.get_enforcement_summary(days=1)

        assert summary.total_blocks == 12  # 10 blocks + 2 failed overrides
        assert summary.total_overrides == 3
        assert summary.total_bypasses == 5
        assert summary.override_success_rate == 60.0  # 3 success / 5 total * 100

    def test_top_policies_calculation(self, test_database):
        """Test top blocking policies calculation"""
        logger = EnforcementAuditLogger(test_database)
        stats = EnforcementStatsCalculator(test_database)

        # bedtime.rego blocks 8 times
        for i in range(8):
            logger.log_block_event(
                policy_name="bedtime.rego",
                client_ip=f"192.168.1.{100 + i % 3}",  # 3 different clients
                endpoint="api.openai.com",
                reason="After hours",
                request_id=f"bedtime-{i}",
            )

        # privacy.rego blocks 4 times
        for i in range(4):
            logger.log_block_event(
                policy_name="privacy.rego",
                client_ip=f"192.168.1.{110 + i % 2}",  # 2 different clients
                endpoint="api.anthropic.com",
                reason="PII detected",
                request_id=f"privacy-{i}",
            )

        # Get top policies
        top_policies = stats.get_top_blocking_policies(limit=10, days=1)

        assert len(top_policies) == 2
        assert top_policies[0].policy_name == "bedtime.rego"
        assert top_policies[0].block_count == 8
        assert top_policies[0].affected_clients == 3
        assert top_policies[1].policy_name == "privacy.rego"
        assert top_policies[1].block_count == 4
        assert top_policies[1].affected_clients == 2

    def test_recent_blocks_retrieval(self, test_database):
        """Test recent blocks retrieval"""
        logger = EnforcementAuditLogger(test_database)
        stats = EnforcementStatsCalculator(test_database)

        # Log 15 blocks
        for i in range(15):
            logger.log_block_event(
                policy_name=f"policy-{i}.rego",
                client_ip="192.168.1.100",
                endpoint="api.openai.com",
                reason=f"Block reason {i}",
                request_id=f"block-{i}",
            )

        # Get recent blocks (limit 10)
        recent_blocks = stats.get_recent_blocks(limit=10)

        assert len(recent_blocks) == 10
        # Most recent block should be last one logged (block-14)
        assert recent_blocks[0].policy_name == "policy-14.rego"

    def test_enforcement_timeline(self, test_database):
        """Test enforcement timeline generation"""
        logger = EnforcementAuditLogger(test_database)
        stats = EnforcementStatsCalculator(test_database)

        # Log various events
        logger.log_block_event(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            reason="After hours",
            request_id="timeline-1",
        )

        logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=True,
            override_user="parent",
            request_id="timeline-2",
        )

        logger.log_allowlist_bypass(
            client_ip="192.168.1.50",
            endpoint="api.openai.com",
            allowlist_reason="Device allowlisted",
            request_id="timeline-3",
        )

        # Get timeline
        timeline = stats.get_enforcement_timeline(hours=1, limit=50)

        assert len(timeline) == 3
        assert all("icon" in event for event in timeline)
        assert all("display_text" in event for event in timeline)

    def test_mode_change_tracking(self, test_database):
        """Test enforcement mode change tracking"""
        logger = EnforcementAuditLogger(test_database)
        stats = EnforcementStatsCalculator(test_database)

        # Log mode changes
        logger.log_mode_change(
            new_mode="advisory",
            user="admin",
            client_ip="192.168.1.1",
            details={"old_mode": "observe", "reason": "Testing advisory"},
        )

        logger.log_mode_change(
            new_mode="enforce",
            user="admin",
            client_ip="192.168.1.1",
            details={"old_mode": "advisory", "reason": "Enabling enforcement"},
        )

        # Get mode history
        history = stats.get_enforcement_mode_history(limit=10)

        assert len(history) == 2
        assert history[0]["user"] == "admin"
        assert "old_mode" in history[0]["details"]

    def test_report_generation(self, test_database):
        """Test enforcement report generation"""
        logger = EnforcementAuditLogger(test_database)
        report_gen = EnforcementReportGenerator(test_database)

        # Generate sample data
        for i in range(5):
            logger.log_block_event(
                policy_name="bedtime.rego",
                client_ip="192.168.1.100",
                endpoint="api.openai.com",
                reason="After hours",
                request_id=f"report-block-{i}",
            )

        # Generate text report
        text_report = report_gen.generate_text_report(days=1)
        assert "ENFORCEMENT SUMMARY REPORT" in text_report
        assert "Total Blocks:" in text_report
        assert "5" in text_report

        # Generate JSON report
        json_report = report_gen.generate_json_report(days=1)
        assert json_report["summary"]["total_blocks"] == 5
        assert json_report["report_type"] == "enforcement_summary"

    def test_daily_stats_aggregation(self, test_database):
        """Test daily statistics aggregation"""
        logger = EnforcementAuditLogger(test_database)
        stats = EnforcementStatsCalculator(test_database)

        # Log events for today
        for i in range(3):
            logger.log_block_event(
                policy_name="bedtime.rego",
                client_ip="192.168.1.100",
                endpoint="api.openai.com",
                reason="Test",
                request_id=f"daily-{i}",
            )

        # Get daily stats
        daily_stats = stats.get_daily_stats(days=7)

        assert len(daily_stats) >= 1
        # Today's stats should show 3 blocks
        today_stats = daily_stats[0]
        assert today_stats.blocks == 3
