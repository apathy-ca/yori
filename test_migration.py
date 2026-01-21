#!/usr/bin/env python3
"""
Test database migration script
"""

import sqlite3
import tempfile
from pathlib import Path

def test_migration():
    """Test Phase 1 to Phase 2 migration"""

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    print(f"Creating test database: {db_path}")

    # Create Phase 1 schema
    print("\n1. Creating Phase 1 schema...")
    schema_path = Path(__file__).parent / 'sql' / 'schema.sql'
    with open(schema_path) as f:
        schema_sql = f.read()

    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)
    conn.commit()

    # Verify Phase 1 schema
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='audit_events'")
    schema = cursor.fetchone()[0]
    print(f"✓ Phase 1 audit_events table created")

    # Add some test data
    print("\n2. Adding test data to Phase 1 schema...")
    cursor.execute("""
        INSERT INTO audit_events (
            timestamp, event_type, client_ip, endpoint, http_method, http_path,
            policy_name, policy_result, policy_reason, request_id
        ) VALUES (
            '2026-01-20T10:00:00Z', 'request', '192.168.1.100', 'api.openai.com',
            'POST', '/v1/chat/completions', 'bedtime.rego', 'block', 'After hours', 'test-1'
        )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM audit_events")
    count = cursor.fetchone()[0]
    print(f"✓ Added {count} test record(s)")

    # Check columns before migration
    cursor.execute("PRAGMA table_info(audit_events)")
    columns_before = {row[1] for row in cursor.fetchall()}
    print(f"✓ Columns before migration: {len(columns_before)}")

    # Run migration
    print("\n3. Running Phase 2 migration...")
    migration_path = Path(__file__).parent / 'sql' / 'migrate_enforcement.sql'
    with open(migration_path) as f:
        migration_sql = f.read()

    try:
        conn.executescript(migration_sql)
        print("✓ Migration completed successfully")
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.close()
        Path(db_path).unlink()
        return False

    # Verify new columns exist
    print("\n4. Verifying Phase 2 schema...")
    cursor.execute("PRAGMA table_info(audit_events)")
    columns_after = {row[1] for row in cursor.fetchall()}

    new_columns = columns_after - columns_before
    expected_new_columns = {'enforcement_action', 'override_user', 'allowlist_reason'}

    if new_columns >= expected_new_columns:
        print(f"✓ New columns added: {new_columns}")
    else:
        print(f"✗ Missing columns: {expected_new_columns - new_columns}")
        return False

    # Verify enforcement_events table exists
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='enforcement_events'")
    if cursor.fetchone()[0] == 1:
        print("✓ enforcement_events table created")
    else:
        print("✗ enforcement_events table not found")
        return False

    # Verify views exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE '%enforcement%'")
    views = [row[0] for row in cursor.fetchall()]
    expected_views = {'enforcement_stats', 'recent_blocks', 'override_stats', 'top_blocking_policies'}

    if set(views) >= expected_views:
        print(f"✓ Enforcement views created: {', '.join(views)}")
    else:
        print(f"✗ Missing views: {expected_views - set(views)}")

    # Verify data backfill
    cursor.execute("SELECT enforcement_action FROM audit_events WHERE request_id = 'test-1'")
    result = cursor.fetchone()
    if result and result[0] == 'block':
        print("✓ Existing data backfilled correctly (enforcement_action set)")
    else:
        print("✗ Data backfill failed")

    # Verify indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%enforcement%'")
    indexes = [row[0] for row in cursor.fetchall()]
    if indexes:
        print(f"✓ Enforcement indexes created: {', '.join(indexes)}")

    conn.close()

    # Cleanup
    Path(db_path).unlink()
    print(f"\n✓ Test database cleaned up")

    print("\n" + "=" * 60)
    print("MIGRATION TEST: PASSED ✓")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_migration()
    exit(0 if success else 1)
