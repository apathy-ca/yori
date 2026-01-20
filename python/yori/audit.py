"""
SQLite audit logging for YORI

Handles persistent logging of all LLM traffic to SQLite database.
"""

import aiosqlite
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from yori.models import AuditEvent, StatsResponse

logger = logging.getLogger(__name__)


class AuditLogger:
    """SQLite-based audit logger"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path) if not isinstance(db_path, Path) else db_path
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure database directory exists"""
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize database schema"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    source_ip TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    method TEXT NOT NULL,
                    request_preview TEXT,
                    response_preview TEXT,
                    status_code INTEGER,
                    policy_decision TEXT NOT NULL,
                    policy_name TEXT,
                    mode TEXT NOT NULL,
                    latency_ms REAL,
                    error TEXT,
                    metadata TEXT
                )
                """
            )

            # Create indexes for common queries
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider ON audit_events(provider)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_decision ON audit_events(policy_decision)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_ip ON audit_events(source_ip)"
            )

            # Create view for daily statistics
            await db.execute(
                """
                CREATE VIEW IF NOT EXISTS daily_stats AS
                SELECT
                    DATE(timestamp) as date,
                    provider,
                    policy_decision,
                    COUNT(*) as request_count,
                    AVG(latency_ms) as avg_latency_ms
                FROM audit_events
                GROUP BY DATE(timestamp), provider, policy_decision
                """
            )

            await db.commit()
            logger.info(f"Audit database initialized at {self.db_path}")

    async def log_event(self, event: AuditEvent) -> int:
        """
        Log an audit event to the database.

        Args:
            event: AuditEvent to log

        Returns:
            ID of the inserted record
        """
        import json

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO audit_events (
                    timestamp, user_id, source_ip, destination, endpoint,
                    provider, method, request_preview, response_preview,
                    status_code, policy_decision, policy_name, mode,
                    latency_ms, error, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp.isoformat(),
                    event.user_id,
                    event.source_ip,
                    event.destination,
                    event.endpoint,
                    event.provider.value,
                    event.method,
                    event.request_preview,
                    event.response_preview,
                    event.status_code,
                    event.policy_decision.value,
                    event.policy_name,
                    event.mode.value,
                    event.latency_ms,
                    event.error,
                    json.dumps(event.metadata) if event.metadata else None,
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        provider: Optional[str] = None,
        decision: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """
        Query audit events with filters.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            provider: Filter by provider
            decision: Filter by policy decision
            start_time: Filter events after this time
            end_time: Filter events before this time

        Returns:
            List of AuditEvent objects
        """
        import json

        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if provider:
            query += " AND provider = ?"
            params.append(provider)

        if decision:
            query += " AND policy_decision = ?"
            params.append(decision)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        events = []
        for row in rows:
            row_dict = dict(row)
            # Parse JSON metadata
            if row_dict.get("metadata"):
                row_dict["metadata"] = json.loads(row_dict["metadata"])
            else:
                row_dict["metadata"] = {}
            events.append(AuditEvent(**row_dict))

        return events

    async def get_stats(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> StatsResponse:
        """
        Get aggregated statistics for the dashboard.

        Args:
            start_time: Start of period (defaults to 24 hours ago)
            end_time: End of period (defaults to now)

        Returns:
            StatsResponse with aggregated data
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=1)
        if not end_time:
            end_time = datetime.utcnow()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Total requests
            async with db.execute(
                "SELECT COUNT(*) as count FROM audit_events WHERE timestamp >= ? AND timestamp <= ?",
                (start_time.isoformat(), end_time.isoformat()),
            ) as cursor:
                total = (await cursor.fetchone())["count"]

            # Requests by provider
            async with db.execute(
                "SELECT provider, COUNT(*) as count FROM audit_events "
                "WHERE timestamp >= ? AND timestamp <= ? GROUP BY provider",
                (start_time.isoformat(), end_time.isoformat()),
            ) as cursor:
                by_provider = {row["provider"]: row["count"] async for row in cursor}

            # Requests by decision
            async with db.execute(
                "SELECT policy_decision, COUNT(*) as count FROM audit_events "
                "WHERE timestamp >= ? AND timestamp <= ? GROUP BY policy_decision",
                (start_time.isoformat(), end_time.isoformat()),
            ) as cursor:
                by_decision = {row["policy_decision"]: row["count"] async for row in cursor}

            # Average latency
            async with db.execute(
                "SELECT AVG(latency_ms) as avg_latency FROM audit_events "
                "WHERE timestamp >= ? AND timestamp <= ? AND latency_ms IS NOT NULL",
                (start_time.isoformat(), end_time.isoformat()),
            ) as cursor:
                avg_latency = (await cursor.fetchone())["avg_latency"] or 0.0

        return StatsResponse(
            total_requests=total,
            requests_by_provider=by_provider,
            requests_by_decision=by_decision,
            average_latency_ms=avg_latency,
            period_start=start_time,
            period_end=end_time,
        )

    async def cleanup_old_events(self, retention_days: int = 365):
        """
        Delete events older than retention period.

        Args:
            retention_days: Number of days to keep events
        """
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM audit_events WHERE timestamp < ?",
                (cutoff.isoformat(),),
            )
            await db.commit()
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} audit events older than {retention_days} days")

        return deleted
