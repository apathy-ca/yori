#!/usr/bin/env python3
"""
Test performance targets for enforcement audit logging
"""

import sqlite3
import tempfile
import time
from pathlib import Path
import sys
import statistics

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / 'python'))

from yori.audit_enforcement import EnforcementAuditLogger
from yori.enforcement_stats import EnforcementStatsCalculator

def test_performance():
    """Test performance targets"""

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

    # Create indexes for performance
    cursor.execute("CREATE INDEX idx_timestamp ON audit_events(timestamp)")
    cursor.execute("CREATE INDEX idx_enforcement_action ON audit_events(enforcement_action)")
    cursor.execute("CREATE INDEX idx_policy_name ON audit_events(policy_name)")

    conn.commit()
    conn.close()

    # Initialize logger and stats
    logger = EnforcementAuditLogger(db_path)
    stats = EnforcementStatsCalculator(db_path)

    # Performance Target 1: Audit writes <5ms
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST 1: Audit Write Speed")
    print("=" * 60)
    print("Target: <5ms per enforcement event write\n")

    write_times = []
    num_writes = 100

    for i in range(num_writes):
        start = time.perf_counter()
        logger.log_block_event(
            policy_name=f"policy-{i % 5}.rego",
            client_ip=f"192.168.1.{100 + i % 50}",
            endpoint="api.openai.com",
            reason=f"Test block {i}",
            request_id=f"perf-block-{i}"
        )
        end = time.perf_counter()
        write_times.append((end - start) * 1000)  # Convert to milliseconds

    avg_write_time = statistics.mean(write_times)
    median_write_time = statistics.median(write_times)
    p95_write_time = sorted(write_times)[int(num_writes * 0.95)]
    max_write_time = max(write_times)

    print(f"Writes completed: {num_writes}")
    print(f"Average write time: {avg_write_time:.3f}ms")
    print(f"Median write time: {median_write_time:.3f}ms")
    print(f"P95 write time: {p95_write_time:.3f}ms")
    print(f"Max write time: {max_write_time:.3f}ms")

    if avg_write_time < 5.0:
        print(f"✓ PASS: Average write time {avg_write_time:.3f}ms < 5ms")
    else:
        print(f"✗ FAIL: Average write time {avg_write_time:.3f}ms >= 5ms")

    if p95_write_time < 5.0:
        print(f"✓ PASS: P95 write time {p95_write_time:.3f}ms < 5ms")
    else:
        print(f"✗ FAIL: P95 write time {p95_write_time:.3f}ms >= 5ms")

    # Add more data for query tests
    print("\nGenerating additional data for query tests...")
    for i in range(100, 500):
        logger.log_block_event(
            policy_name=f"policy-{i % 10}.rego",
            client_ip=f"192.168.1.{100 + i % 100}",
            endpoint="api.openai.com",
            reason=f"Test block {i}",
            request_id=f"perf-block-{i}"
        )
    print(f"✓ Total events in database: 500")

    # Performance Target 2: Dashboard queries <500ms
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST 2: Dashboard Query Speed")
    print("=" * 60)
    print("Target: <500ms for dashboard queries\n")

    # Test enforcement summary query
    start = time.perf_counter()
    summary = stats.get_enforcement_summary(days=30)
    end = time.perf_counter()
    summary_time = (end - start) * 1000

    print(f"Enforcement summary query: {summary_time:.3f}ms")
    if summary_time < 500:
        print(f"✓ PASS: Summary query {summary_time:.3f}ms < 500ms")
    else:
        print(f"✗ FAIL: Summary query {summary_time:.3f}ms >= 500ms")

    # Test recent blocks query
    start = time.perf_counter()
    recent = stats.get_recent_blocks(limit=50)
    end = time.perf_counter()
    recent_time = (end - start) * 1000

    print(f"Recent blocks query (50): {recent_time:.3f}ms")
    if recent_time < 500:
        print(f"✓ PASS: Recent blocks query {recent_time:.3f}ms < 500ms")
    else:
        print(f"✗ FAIL: Recent blocks query {recent_time:.3f}ms >= 500ms")

    # Test top policies query
    start = time.perf_counter()
    top_policies = stats.get_top_blocking_policies(limit=10, days=7)
    end = time.perf_counter()
    policies_time = (end - start) * 1000

    print(f"Top policies query (10): {policies_time:.3f}ms")
    if policies_time < 500:
        print(f"✓ PASS: Top policies query {policies_time:.3f}ms < 500ms")
    else:
        print(f"✗ FAIL: Top policies query {policies_time:.3f}ms >= 500ms")

    # Test daily stats query
    start = time.perf_counter()
    daily = stats.get_daily_stats(days=30)
    end = time.perf_counter()
    daily_time = (end - start) * 1000

    print(f"Daily stats query (30 days): {daily_time:.3f}ms")
    if daily_time < 500:
        print(f"✓ PASS: Daily stats query {daily_time:.3f}ms < 500ms")
    else:
        print(f"✗ FAIL: Daily stats query {daily_time:.3f}ms >= 500ms")

    # Test timeline query
    start = time.perf_counter()
    timeline = stats.get_enforcement_timeline(hours=24, limit=50)
    end = time.perf_counter()
    timeline_time = (end - start) * 1000

    print(f"Timeline query (24h, 50 events): {timeline_time:.3f}ms")
    if timeline_time < 500:
        print(f"✓ PASS: Timeline query {timeline_time:.3f}ms < 500ms")
    else:
        print(f"✗ FAIL: Timeline query {timeline_time:.3f}ms >= 500ms")

    # Calculate overall dashboard load time
    total_dashboard_time = summary_time + recent_time + policies_time
    print(f"\nTotal dashboard load time: {total_dashboard_time:.3f}ms")
    print(f"   (summary + recent blocks + top policies)")

    if total_dashboard_time < 500:
        print(f"✓ PASS: Full dashboard load {total_dashboard_time:.3f}ms < 500ms")
    else:
        print(f"✗ FAIL: Full dashboard load {total_dashboard_time:.3f}ms >= 500ms")

    # Final summary
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 60)

    write_pass = avg_write_time < 5.0 and p95_write_time < 5.0
    query_pass = (summary_time < 500 and recent_time < 500 and
                  policies_time < 500 and daily_time < 500 and
                  timeline_time < 500)

    print(f"\nWrite Performance: {'✓ PASS' if write_pass else '✗ FAIL'}")
    print(f"   Average: {avg_write_time:.3f}ms (target: <5ms)")
    print(f"   P95: {p95_write_time:.3f}ms (target: <5ms)")

    print(f"\nQuery Performance: {'✓ PASS' if query_pass else '✗ FAIL'}")
    print(f"   Summary: {summary_time:.3f}ms (target: <500ms)")
    print(f"   Recent blocks: {recent_time:.3f}ms (target: <500ms)")
    print(f"   Top policies: {policies_time:.3f}ms (target: <500ms)")
    print(f"   Daily stats: {daily_time:.3f}ms (target: <500ms)")
    print(f"   Timeline: {timeline_time:.3f}ms (target: <500ms)")

    print(f"\nOverall: {'✓ ALL TESTS PASSED' if write_pass and query_pass else '✗ SOME TESTS FAILED'}")

    # Cleanup
    db_path.unlink()
    print(f"\n✓ Test database cleaned up")

    return write_pass and query_pass

if __name__ == '__main__':
    success = test_performance()
    exit(0 if success else 1)
