#!/usr/bin/env python3
"""
Test enforcement report generation
"""

import sqlite3
import tempfile
import json
from pathlib import Path
import sys

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / 'python'))

from yori.audit_enforcement import EnforcementAuditLogger
from yori.reports.enforcement_summary import EnforcementReportGenerator

def test_report_generation():
    """Test report generation functionality"""

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

    # Initialize logger
    logger = EnforcementAuditLogger(db_path)
    report_gen = EnforcementReportGenerator(db_path)

    print("\n1. Generating sample data for report...")

    # Generate 15 block events
    for i in range(15):
        policy = "bedtime.rego" if i < 10 else "privacy.rego"
        logger.log_block_event(
            policy_name=policy,
            client_ip=f"192.168.1.{100 + i % 5}",
            endpoint="api.openai.com",
            reason="Test block for report",
            client_device=f"device-{i % 3}",
            request_id=f"report-block-{i}"
        )

    # Generate 5 overrides
    for i in range(5):
        logger.log_override_attempt(
            policy_name="bedtime.rego",
            client_ip="192.168.1.100",
            endpoint="api.openai.com",
            success=i < 3,  # First 3 succeed, last 2 fail
            override_user="parent" if i < 3 else "child",
            request_id=f"report-override-{i}"
        )

    # Generate 8 bypasses
    for i in range(8):
        logger.log_allowlist_bypass(
            client_ip="192.168.1.50",
            endpoint="api.openai.com",
            allowlist_reason="Allowlist device",
            request_id=f"report-bypass-{i}"
        )

    print("✓ Generated 28 events for report")

    # Test text report generation
    print("\n2. Testing text report generation...")
    text_report = report_gen.generate_text_report(days=7)

    assert "YORI ENFORCEMENT SUMMARY REPORT" in text_report, "Report title missing"
    assert "EXECUTIVE SUMMARY" in text_report, "Executive summary section missing"
    assert "Total Blocks:" in text_report, "Total blocks stat missing"
    assert "Total Overrides:" in text_report, "Total overrides stat missing"
    assert "Total Allowlist Bypasses:" in text_report, "Total bypasses stat missing"
    assert "DAILY TRENDS" in text_report, "Daily trends section missing"
    assert "TOP BLOCKING POLICIES" in text_report, "Top policies section missing"

    # Check that values appear in report
    assert "17" in text_report or "Blocks" in text_report, "Block count not in report"
    assert "3" in text_report or "Overrides" in text_report, "Override count not in report"
    assert "8" in text_report or "Bypasses" in text_report, "Bypass count not in report"

    print("✓ Text report generated successfully")
    print(f"   Report length: {len(text_report)} characters")

    # Test JSON report generation
    print("\n3. Testing JSON report generation...")
    json_report = report_gen.generate_json_report(days=7)

    assert json_report["report_type"] == "enforcement_summary", "Report type mismatch"
    assert "summary" in json_report, "Summary section missing from JSON"
    assert "daily_stats" in json_report, "Daily stats missing from JSON"
    assert "top_policies" in json_report, "Top policies missing from JSON"
    assert "recent_blocks" in json_report, "Recent blocks missing from JSON"

    summary = json_report["summary"]
    assert summary["total_blocks"] == 17, f"Expected 17 blocks (15 direct + 2 failed overrides), got {summary['total_blocks']}"
    assert summary["total_overrides"] == 3, f"Expected 3 overrides, got {summary['total_overrides']}"
    assert summary["total_bypasses"] == 8, f"Expected 8 bypasses, got {summary['total_bypasses']}"

    print("✓ JSON report generated successfully")
    print(f"   Summary blocks: {summary['total_blocks']}")
    print(f"   Summary overrides: {summary['total_overrides']}")
    print(f"   Summary bypasses: {summary['total_bypasses']}")

    # Test saving reports
    print("\n4. Testing report file saving...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Save text report
        text_file = tmpdir_path / "enforcement_report.txt"
        report_gen.save_report(text_file, format="text", days=7)
        assert text_file.exists(), "Text report file not created"
        assert text_file.stat().st_size > 0, "Text report file is empty"
        print(f"✓ Text report saved: {text_file.stat().st_size} bytes")

        # Save JSON report
        json_file = tmpdir_path / "enforcement_report.json"
        report_gen.save_report(json_file, format="json", days=7)
        assert json_file.exists(), "JSON report file not created"
        assert json_file.stat().st_size > 0, "JSON report file is empty"

        # Verify JSON file is valid
        with open(json_file) as f:
            loaded_json = json.load(f)
            assert loaded_json["report_type"] == "enforcement_summary", "Loaded JSON report type mismatch"

        print(f"✓ JSON report saved: {json_file.stat().st_size} bytes")

    # Display sample of text report
    print("\n5. Sample of generated text report:")
    print("   " + "=" * 56)
    for line in text_report.split("\n")[:15]:
        print("   " + line)
    print("   ...")
    print("   " + "=" * 56)

    # Cleanup
    db_path.unlink()
    print(f"\n✓ Test database cleaned up")

    print("\n" + "=" * 60)
    print("REPORT GENERATION TEST: PASSED ✓")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_report_generation()
    exit(0 if success else 1)
