"""
YORI Analytics Module

Provides enhanced analytics, reports, and export functionality.
"""

import csv
import io
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class Analytics:
    """Advanced analytics and reporting for YORI"""

    def __init__(self, db_path: str = "/var/db/yori/audit.db"):
        self.db_path = db_path

    def get_usage_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "day",
    ) -> Dict[str, Any]:
        """
        Generate comprehensive usage report.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            group_by: Grouping - "day", "week", "month", "endpoint", "device"
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Default date range
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            report = {
                "period": {"start": start_date, "end": end_date},
                "generated_at": datetime.now().isoformat(),
                "summary": {},
                "breakdown": [],
                "top_users": [],
                "top_endpoints": [],
                "hourly_pattern": [],
            }

            # Summary statistics
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_requests,
                    COUNT(DISTINCT client_ip) as unique_devices,
                    COUNT(DISTINCT endpoint) as unique_endpoints,
                    SUM(CASE WHEN policy_result = 'block' THEN 1 ELSE 0 END) as blocked,
                    SUM(CASE WHEN policy_result = 'alert' THEN 1 ELSE 0 END) as alerts
                FROM audit_events
                WHERE timestamp >= ? AND timestamp <= ?
            """,
                (start_date, end_date + " 23:59:59"),
            )
            row = cursor.fetchone()
            report["summary"] = {
                "total_requests": row[0] or 0,
                "unique_devices": row[1] or 0,
                "unique_endpoints": row[2] or 0,
                "blocked_requests": row[3] or 0,
                "alert_count": row[4] or 0,
            }

            # Token/cost summary if available
            cursor.execute(
                """
                SELECT
                    SUM(total_input_tokens) as input_tokens,
                    SUM(total_output_tokens) as output_tokens,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                WHERE date >= ? AND date <= ?
            """,
                (start_date, end_date),
            )
            row = cursor.fetchone()
            if row[0]:
                report["summary"]["total_input_tokens"] = row[0] or 0
                report["summary"]["total_output_tokens"] = row[1] or 0
                report["summary"]["total_cost_cents"] = round(row[2] or 0, 2)
                report["summary"]["total_cost_dollars"] = round((row[2] or 0) / 100, 2)

            # Breakdown by grouping
            if group_by == "day":
                cursor.execute(
                    """
                    SELECT
                        DATE(timestamp) as period,
                        COUNT(*) as requests,
                        COUNT(DISTINCT client_ip) as devices
                    FROM audit_events
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY period
                """,
                    (start_date, end_date + " 23:59:59"),
                )
            elif group_by == "endpoint":
                cursor.execute(
                    """
                    SELECT
                        endpoint as period,
                        COUNT(*) as requests,
                        COUNT(DISTINCT client_ip) as devices
                    FROM audit_events
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY endpoint
                    ORDER BY requests DESC
                """,
                    (start_date, end_date + " 23:59:59"),
                )
            elif group_by == "device":
                cursor.execute(
                    """
                    SELECT
                        client_ip as period,
                        COUNT(*) as requests,
                        COUNT(DISTINCT endpoint) as endpoints
                    FROM audit_events
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY client_ip
                    ORDER BY requests DESC
                """,
                    (start_date, end_date + " 23:59:59"),
                )
            else:  # week
                cursor.execute(
                    """
                    SELECT
                        strftime('%Y-W%W', timestamp) as period,
                        COUNT(*) as requests,
                        COUNT(DISTINCT client_ip) as devices
                    FROM audit_events
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY strftime('%Y-W%W', timestamp)
                    ORDER BY period
                """,
                    (start_date, end_date + " 23:59:59"),
                )

            report["breakdown"] = [
                {"period": r[0], "requests": r[1], "secondary": r[2]}
                for r in cursor.fetchall()
            ]

            # Top users
            cursor.execute(
                """
                SELECT
                    client_ip,
                    client_device,
                    COUNT(*) as requests
                FROM audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY client_ip
                ORDER BY requests DESC
                LIMIT 10
            """,
                (start_date, end_date + " 23:59:59"),
            )
            report["top_users"] = [
                {"ip": r[0], "device": r[1], "requests": r[2]}
                for r in cursor.fetchall()
            ]

            # Top endpoints
            cursor.execute(
                """
                SELECT
                    endpoint,
                    COUNT(*) as requests
                FROM audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY endpoint
                ORDER BY requests DESC
                LIMIT 10
            """,
                (start_date, end_date + " 23:59:59"),
            )
            report["top_endpoints"] = [
                {"endpoint": r[0], "requests": r[1]} for r in cursor.fetchall()
            ]

            # Hourly pattern (aggregated across all days)
            cursor.execute(
                """
                SELECT
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as requests
                FROM audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            """,
                (start_date, end_date + " 23:59:59"),
            )
            report["hourly_pattern"] = [
                {"hour": int(r[0]), "requests": r[1]} for r in cursor.fetchall()
            ]

            return report

        finally:
            conn.close()

    def get_enforcement_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate enforcement-focused report"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            report = {
                "period": {"start": start_date, "end": end_date},
                "generated_at": datetime.now().isoformat(),
                "summary": {},
                "by_policy": [],
                "by_action": [],
                "recent_blocks": [],
            }

            # Summary
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN policy_result = 'allow' THEN 1 ELSE 0 END) as allowed,
                    SUM(CASE WHEN policy_result = 'alert' THEN 1 ELSE 0 END) as alerts,
                    SUM(CASE WHEN policy_result = 'block' THEN 1 ELSE 0 END) as blocked
                FROM audit_events
                WHERE timestamp >= ? AND timestamp <= ?
            """,
                (start_date, end_date + " 23:59:59"),
            )
            row = cursor.fetchone()
            report["summary"] = {
                "total_evaluated": row[0] or 0,
                "allowed": row[1] or 0,
                "alerts": row[2] or 0,
                "blocked": row[3] or 0,
                "block_rate": round((row[3] or 0) / (row[0] or 1) * 100, 2),
            }

            # By policy
            cursor.execute(
                """
                SELECT
                    policy_name,
                    policy_result,
                    COUNT(*) as count
                FROM audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                    AND policy_name IS NOT NULL
                GROUP BY policy_name, policy_result
                ORDER BY count DESC
            """,
                (start_date, end_date + " 23:59:59"),
            )
            report["by_policy"] = [
                {"policy": r[0], "result": r[1], "count": r[2]}
                for r in cursor.fetchall()
            ]

            # By action over time
            cursor.execute(
                """
                SELECT
                    DATE(timestamp) as date,
                    policy_result,
                    COUNT(*) as count
                FROM audit_events
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY DATE(timestamp), policy_result
                ORDER BY date
            """,
                (start_date, end_date + " 23:59:59"),
            )
            report["by_action"] = [
                {"date": r[0], "result": r[1], "count": r[2]}
                for r in cursor.fetchall()
            ]

            # Recent blocks
            cursor.execute(
                """
                SELECT
                    timestamp,
                    client_ip,
                    endpoint,
                    policy_name,
                    policy_reason
                FROM audit_events
                WHERE policy_result = 'block'
                    AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 20
            """,
                (start_date, end_date + " 23:59:59"),
            )
            report["recent_blocks"] = [
                {
                    "timestamp": r[0],
                    "client_ip": r[1],
                    "endpoint": r[2],
                    "policy": r[3],
                    "reason": r[4],
                }
                for r in cursor.fetchall()
            ]

            return report

        finally:
            conn.close()

    def get_cost_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate cost-focused report"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            report = {
                "period": {"start": start_date, "end": end_date},
                "generated_at": datetime.now().isoformat(),
                "summary": {},
                "by_day": [],
                "by_device": [],
                "by_endpoint": [],
                "by_model": [],
            }

            # Summary
            cursor.execute(
                """
                SELECT
                    SUM(total_requests) as requests,
                    SUM(total_input_tokens) as input_tokens,
                    SUM(total_output_tokens) as output_tokens,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                WHERE date >= ? AND date <= ?
            """,
                (start_date, end_date),
            )
            row = cursor.fetchone()
            report["summary"] = {
                "total_requests": row[0] or 0,
                "total_input_tokens": row[1] or 0,
                "total_output_tokens": row[2] or 0,
                "total_tokens": (row[1] or 0) + (row[2] or 0),
                "total_cost_cents": round(row[3] or 0, 2),
                "total_cost_dollars": round((row[3] or 0) / 100, 2),
            }

            # Calculate averages
            days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
            report["summary"]["avg_daily_cost_cents"] = round((row[3] or 0) / max(days, 1), 2)
            report["summary"]["avg_cost_per_request_cents"] = round((row[3] or 0) / max(row[0] or 1, 1), 4)

            # By day
            cursor.execute(
                """
                SELECT
                    date,
                    SUM(total_requests) as requests,
                    SUM(total_input_tokens + total_output_tokens) as tokens,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                WHERE date >= ? AND date <= ?
                GROUP BY date
                ORDER BY date
            """,
                (start_date, end_date),
            )
            report["by_day"] = [
                {
                    "date": r[0],
                    "requests": r[1],
                    "tokens": r[2],
                    "cost_cents": round(r[3], 2),
                }
                for r in cursor.fetchall()
            ]

            # By device
            cursor.execute(
                """
                SELECT
                    client_ip,
                    SUM(total_requests) as requests,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                WHERE date >= ? AND date <= ?
                GROUP BY client_ip
                ORDER BY cost_cents DESC
                LIMIT 10
            """,
                (start_date, end_date),
            )
            report["by_device"] = [
                {"ip": r[0], "requests": r[1], "cost_cents": round(r[2], 2)}
                for r in cursor.fetchall()
            ]

            # By endpoint
            cursor.execute(
                """
                SELECT
                    endpoint,
                    SUM(total_requests) as requests,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                WHERE date >= ? AND date <= ?
                GROUP BY endpoint
                ORDER BY cost_cents DESC
            """,
                (start_date, end_date),
            )
            report["by_endpoint"] = [
                {"endpoint": r[0], "requests": r[1], "cost_cents": round(r[2], 2)}
                for r in cursor.fetchall()
            ]

            # By model
            cursor.execute(
                """
                SELECT
                    model,
                    SUM(total_requests) as requests,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                WHERE date >= ? AND date <= ?
                GROUP BY model
                ORDER BY cost_cents DESC
            """,
                (start_date, end_date),
            )
            report["by_model"] = [
                {"model": r[0], "requests": r[1], "cost_cents": round(r[2], 2)}
                for r in cursor.fetchall()
            ]

            return report

        finally:
            conn.close()

    def export_to_csv(
        self,
        report_type: str = "usage",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """Export report data to CSV format"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            output = io.StringIO()
            writer = csv.writer(output)

            if report_type == "usage":
                writer.writerow([
                    "Timestamp", "Client IP", "Device", "Endpoint", "Method",
                    "Path", "Policy Result", "Policy Name"
                ])
                cursor.execute(
                    """
                    SELECT timestamp, client_ip, client_device, endpoint,
                           http_method, http_path, policy_result, policy_name
                    FROM audit_events
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp
                """,
                    (start_date, end_date + " 23:59:59"),
                )
                for row in cursor.fetchall():
                    writer.writerow(row)

            elif report_type == "tokens":
                writer.writerow([
                    "Date", "Client IP", "Endpoint", "Model", "Requests",
                    "Input Tokens", "Output Tokens", "Cost (cents)"
                ])
                cursor.execute(
                    """
                    SELECT date, client_ip, endpoint, model, total_requests,
                           total_input_tokens, total_output_tokens, total_cost_cents
                    FROM token_daily_stats
                    WHERE date >= ? AND date <= ?
                    ORDER BY date, client_ip
                """,
                    (start_date, end_date),
                )
                for row in cursor.fetchall():
                    writer.writerow(row)

            elif report_type == "cost":
                writer.writerow([
                    "Date", "Total Requests", "Total Tokens", "Cost (cents)", "Cost ($)"
                ])
                cursor.execute(
                    """
                    SELECT
                        date,
                        SUM(total_requests),
                        SUM(total_input_tokens + total_output_tokens),
                        SUM(total_cost_cents)
                    FROM token_daily_stats
                    WHERE date >= ? AND date <= ?
                    GROUP BY date
                    ORDER BY date
                """,
                    (start_date, end_date),
                )
                for row in cursor.fetchall():
                    writer.writerow([
                        row[0], row[1], row[2],
                        round(row[3], 2), round(row[3] / 100, 2)
                    ])

            return output.getvalue()

        finally:
            conn.close()

    def export_to_json(
        self,
        report_type: str = "usage",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """Export report data to JSON format"""
        if report_type == "usage":
            report = self.get_usage_report(start_date, end_date)
        elif report_type == "enforcement":
            report = self.get_enforcement_report(start_date, end_date)
        elif report_type == "cost":
            report = self.get_cost_report(start_date, end_date)
        else:
            report = {"error": f"Unknown report type: {report_type}"}

        return json.dumps(report, indent=2)


# Global instance
_analytics: Optional[Analytics] = None


def get_analytics(db_path: str = "/var/db/yori/audit.db") -> Analytics:
    """Get or create global analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = Analytics(db_path)
    return _analytics
