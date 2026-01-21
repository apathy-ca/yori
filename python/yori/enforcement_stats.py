"""
YORI Enforcement Statistics

Calculates and retrieves enforcement statistics for dashboard and reports.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class EnforcementSummary:
    """Summary of enforcement activity"""

    total_blocks: int
    total_overrides: int
    total_bypasses: int
    total_alerts: int
    total_allows: int
    override_success_rate: float
    top_blocking_policy: Optional[str]
    most_blocked_client: Optional[str]


@dataclass
class DailyEnforcementStats:
    """Daily enforcement statistics"""

    date: str
    blocks: int
    overrides: int
    bypasses: int
    alerts: int
    allows: int


@dataclass
class BlockEvent:
    """Recent block event"""

    timestamp: str
    client_ip: str
    client_device: Optional[str]
    endpoint: str
    policy_name: str
    reason: str
    enforcement_action: str
    override_user: Optional[str]


@dataclass
class PolicyStats:
    """Statistics for a specific policy"""

    policy_name: str
    block_count: int
    affected_clients: int


class EnforcementStatsCalculator:
    """Calculates enforcement statistics from audit database"""

    def __init__(self, database_path: Path):
        """
        Initialize stats calculator.

        Args:
            database_path: Path to SQLite audit database
        """
        self.database_path = database_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.database_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_enforcement_summary(self, days: int = 30) -> EnforcementSummary:
        """
        Get overall enforcement summary for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            EnforcementSummary object
        """
        since_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get action counts
            cursor.execute(
                """
                SELECT
                    COUNT(CASE WHEN enforcement_action = 'block' THEN 1 END) as blocks,
                    COUNT(CASE WHEN enforcement_action = 'override' THEN 1 END) as overrides,
                    COUNT(CASE WHEN enforcement_action = 'allowlist_bypass' THEN 1 END) as bypasses,
                    COUNT(CASE WHEN enforcement_action = 'alert' THEN 1 END) as alerts,
                    COUNT(CASE WHEN enforcement_action = 'allow' THEN 1 END) as allows
                FROM audit_events
                WHERE DATE(timestamp) >= ?
                """,
                (since_date,),
            )
            row = cursor.fetchone()

            total_blocks = row["blocks"] or 0
            total_overrides = row["overrides"] or 0
            total_bypasses = row["bypasses"] or 0
            total_alerts = row["alerts"] or 0
            total_allows = row["allows"] or 0

            # Calculate override success rate
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN enforcement_action = 'override' THEN 1 END) as successful
                FROM audit_events
                WHERE event_type IN ('override_attempt', 'override_success', 'override_failed')
                  AND DATE(timestamp) >= ?
                """,
                (since_date,),
            )
            row = cursor.fetchone()
            total_attempts = row["total_attempts"] or 0
            successful = row["successful"] or 0
            override_success_rate = (
                (successful / total_attempts * 100) if total_attempts > 0 else 0.0
            )

            # Get top blocking policy
            cursor.execute(
                """
                SELECT policy_name, COUNT(*) as count
                FROM audit_events
                WHERE enforcement_action = 'block'
                  AND DATE(timestamp) >= ?
                  AND policy_name IS NOT NULL
                GROUP BY policy_name
                ORDER BY count DESC
                LIMIT 1
                """,
                (since_date,),
            )
            row = cursor.fetchone()
            top_blocking_policy = row["policy_name"] if row else None

            # Get most blocked client
            cursor.execute(
                """
                SELECT client_ip, COUNT(*) as count
                FROM audit_events
                WHERE enforcement_action = 'block'
                  AND DATE(timestamp) >= ?
                GROUP BY client_ip
                ORDER BY count DESC
                LIMIT 1
                """,
                (since_date,),
            )
            row = cursor.fetchone()
            most_blocked_client = row["client_ip"] if row else None

        return EnforcementSummary(
            total_blocks=total_blocks,
            total_overrides=total_overrides,
            total_bypasses=total_bypasses,
            total_alerts=total_alerts,
            total_allows=total_allows,
            override_success_rate=round(override_success_rate, 2),
            top_blocking_policy=top_blocking_policy,
            most_blocked_client=most_blocked_client,
        )

    def get_daily_stats(self, days: int = 30) -> List[DailyEnforcementStats]:
        """
        Get daily enforcement statistics for the last N days.

        Args:
            days: Number of days to retrieve

        Returns:
            List of DailyEnforcementStats objects
        """
        since_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    DATE(timestamp) as date,
                    COUNT(CASE WHEN enforcement_action = 'block' THEN 1 END) as blocks,
                    COUNT(CASE WHEN enforcement_action = 'override' THEN 1 END) as overrides,
                    COUNT(CASE WHEN enforcement_action = 'allowlist_bypass' THEN 1 END) as bypasses,
                    COUNT(CASE WHEN enforcement_action = 'alert' THEN 1 END) as alerts,
                    COUNT(CASE WHEN enforcement_action = 'allow' THEN 1 END) as allows
                FROM audit_events
                WHERE DATE(timestamp) >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                """,
                (since_date,),
            )

            stats = []
            for row in cursor.fetchall():
                stats.append(
                    DailyEnforcementStats(
                        date=row["date"],
                        blocks=row["blocks"] or 0,
                        overrides=row["overrides"] or 0,
                        bypasses=row["bypasses"] or 0,
                        alerts=row["alerts"] or 0,
                        allows=row["allows"] or 0,
                    )
                )

        return stats

    def get_recent_blocks(self, limit: int = 50) -> List[BlockEvent]:
        """
        Get recent block events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of BlockEvent objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    timestamp,
                    client_ip,
                    client_device,
                    endpoint,
                    policy_name,
                    policy_reason,
                    enforcement_action,
                    override_user
                FROM audit_events
                WHERE enforcement_action IN ('block', 'override')
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            blocks = []
            for row in cursor.fetchall():
                blocks.append(
                    BlockEvent(
                        timestamp=row["timestamp"],
                        client_ip=row["client_ip"],
                        client_device=row["client_device"],
                        endpoint=row["endpoint"],
                        policy_name=row["policy_name"] or "unknown",
                        reason=row["policy_reason"] or "No reason provided",
                        enforcement_action=row["enforcement_action"],
                        override_user=row["override_user"],
                    )
                )

        return blocks

    def get_top_blocking_policies(self, limit: int = 10, days: int = 7) -> List[PolicyStats]:
        """
        Get policies that block most frequently.

        Args:
            limit: Maximum number of policies to return
            days: Number of days to analyze

        Returns:
            List of PolicyStats objects
        """
        since_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    policy_name,
                    COUNT(*) as block_count,
                    COUNT(DISTINCT client_ip) as affected_clients
                FROM audit_events
                WHERE enforcement_action = 'block'
                  AND DATE(timestamp) >= ?
                  AND policy_name IS NOT NULL
                GROUP BY policy_name
                ORDER BY block_count DESC
                LIMIT ?
                """,
                (since_date, limit),
            )

            policies = []
            for row in cursor.fetchall():
                policies.append(
                    PolicyStats(
                        policy_name=row["policy_name"],
                        block_count=row["block_count"],
                        affected_clients=row["affected_clients"],
                    )
                )

        return policies

    def get_enforcement_timeline(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get enforcement timeline for the last N hours.

        Args:
            hours: Number of hours to retrieve
            limit: Maximum number of events to return

        Returns:
            List of timeline events
        """
        since_timestamp = (
            datetime.utcnow() - timedelta(hours=hours)
        ).isoformat() + "Z"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    timestamp,
                    event_type,
                    enforcement_action,
                    policy_name,
                    client_ip,
                    client_device,
                    policy_reason,
                    override_user,
                    allowlist_reason
                FROM audit_events
                WHERE timestamp >= ?
                  AND enforcement_action IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (since_timestamp, limit),
            )

            timeline = []
            for row in cursor.fetchall():
                # Determine icon based on action
                icon_map = {
                    "block": "🚫",
                    "override": "✓",
                    "allowlist_bypass": "→",
                    "alert": "⚠",
                    "allow": "•",
                }
                icon = icon_map.get(row["enforcement_action"], "•")

                timeline.append(
                    {
                        "timestamp": row["timestamp"],
                        "event_type": row["event_type"],
                        "enforcement_action": row["enforcement_action"],
                        "policy_name": row["policy_name"],
                        "client_ip": row["client_ip"],
                        "client_device": row["client_device"],
                        "reason": row["policy_reason"] or row["allowlist_reason"] or "N/A",
                        "override_user": row["override_user"],
                        "icon": icon,
                        "display_text": f"{icon} {row['enforcement_action'].replace('_', ' ').title()}",
                    }
                )

        return timeline

    def get_enforcement_mode_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get enforcement mode change history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of mode change events
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    timestamp,
                    event_type,
                    user,
                    details,
                    client_ip
                FROM enforcement_events
                WHERE event_type = 'enforcement_mode_change'
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            history = []
            for row in cursor.fetchall():
                history.append(
                    {
                        "timestamp": row["timestamp"],
                        "event_type": row["event_type"],
                        "user": row["user"],
                        "details": row["details"],
                        "client_ip": row["client_ip"],
                    }
                )

        return history
