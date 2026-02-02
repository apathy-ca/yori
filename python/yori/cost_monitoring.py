"""
YORI Cost Monitoring Module

Manages budgets, alerts, and cost tracking for LLM usage.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class BudgetType(str, Enum):
    """Types of budgets"""
    GLOBAL = "global"          # Applies to all usage
    DEVICE = "device"          # Per-device budget
    ENDPOINT = "endpoint"      # Per-endpoint budget
    DEVICE_ENDPOINT = "device_endpoint"  # Per device+endpoint combination


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CostMonitor:
    """Monitors LLM costs and manages budgets"""

    def __init__(self, db_path: str = "/var/db/yori/audit.db"):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure cost monitoring tables exist"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Budgets table (may already exist from token_tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    budget_type TEXT NOT NULL,
                    target TEXT,
                    daily_limit_cents REAL,
                    monthly_limit_cents REAL,
                    alert_threshold_percent INTEGER DEFAULT 80,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # Budget alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budget_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    budget_name TEXT NOT NULL,
                    alert_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    current_spend_cents REAL,
                    budget_limit_cents REAL,
                    percent_used REAL,
                    acknowledged INTEGER DEFAULT 0,
                    acknowledged_at TEXT,
                    acknowledged_by TEXT
                )
            """)

            # Cost projections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cost_projections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    actual_cost_cents REAL,
                    projected_daily_cents REAL,
                    projected_monthly_cents REAL,
                    avg_cost_per_request REAL,
                    trend TEXT
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget_alerts_ts ON budget_alerts(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget_alerts_level ON budget_alerts(alert_level)")

            conn.commit()
            logger.info("Cost monitoring schema initialized")
        finally:
            conn.close()

    def create_budget(
        self,
        name: str,
        budget_type: BudgetType,
        daily_limit_cents: Optional[float] = None,
        monthly_limit_cents: Optional[float] = None,
        target: Optional[str] = None,
        alert_threshold_percent: int = 80,
    ) -> bool:
        """Create a new budget"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO token_budgets
                (name, budget_type, target, daily_limit_cents, monthly_limit_cents,
                 alert_threshold_percent, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
                (
                    name,
                    budget_type.value,
                    target,
                    daily_limit_cents,
                    monthly_limit_cents,
                    alert_threshold_percent,
                    now,
                    now,
                ),
            )
            conn.commit()
            logger.info(f"Created budget: {name}")
            return True

        except sqlite3.IntegrityError:
            logger.warning(f"Budget already exists: {name}")
            return False
        finally:
            conn.close()

    def update_budget(self, name: str, **kwargs) -> bool:
        """Update an existing budget"""
        allowed_fields = {
            "daily_limit_cents",
            "monthly_limit_cents",
            "alert_threshold_percent",
            "enabled",
            "target",
        }

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [name]

            cursor.execute(
                f"UPDATE token_budgets SET {set_clause} WHERE name = ?", values
            )
            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def delete_budget(self, name: str) -> bool:
        """Delete a budget"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM token_budgets WHERE name = ?", (name,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_budgets(self) -> List[Dict[str, Any]]:
        """Get all budgets"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM token_budgets ORDER BY name")
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_budget(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific budget"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM token_budgets WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                columns = [d[0] for d in cursor.description]
                return dict(zip(columns, row))
            return None
        finally:
            conn.close()

    def check_budgets(self) -> List[Dict[str, Any]]:
        """Check all budgets and return any that need alerts"""
        alerts = []
        budgets = self.get_budgets()

        for budget in budgets:
            if not budget.get("enabled"):
                continue

            status = self._check_budget(budget)
            if status.get("needs_alert"):
                alerts.append(status)

        return alerts

    def _check_budget(self, budget: Dict[str, Any]) -> Dict[str, Any]:
        """Check a single budget against current spending"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            budget_type = budget.get("budget_type")
            target = budget.get("target")
            daily_limit = budget.get("daily_limit_cents")
            monthly_limit = budget.get("monthly_limit_cents")
            threshold = budget.get("alert_threshold_percent", 80)

            today = datetime.now().strftime("%Y-%m-%d")
            month_start = datetime.now().strftime("%Y-%m-01")

            # Build query based on budget type
            where_clause = ""
            params: List[Any] = []

            if budget_type == "device":
                where_clause = "WHERE client_ip = ?"
                params = [target]
            elif budget_type == "endpoint":
                where_clause = "WHERE endpoint = ?"
                params = [target]
            elif budget_type == "device_endpoint":
                parts = target.split(":") if target else ["", ""]
                where_clause = "WHERE client_ip = ? AND endpoint = ?"
                params = parts[:2]

            # Get daily spend
            daily_spend = 0
            if daily_limit:
                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(total_cost_cents), 0)
                    FROM token_daily_stats
                    {where_clause}
                    {"AND" if where_clause else "WHERE"} date = ?
                """,
                    params + [today],
                )
                daily_spend = cursor.fetchone()[0] or 0

            # Get monthly spend
            monthly_spend = 0
            if monthly_limit:
                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(total_cost_cents), 0)
                    FROM token_daily_stats
                    {where_clause}
                    {"AND" if where_clause else "WHERE"} date >= ?
                """,
                    params + [month_start],
                )
                monthly_spend = cursor.fetchone()[0] or 0

            # Check if alert needed
            needs_alert = False
            alert_level = AlertLevel.INFO
            message = ""

            if daily_limit and daily_spend > 0:
                daily_percent = (daily_spend / daily_limit) * 100
                if daily_percent >= 100:
                    needs_alert = True
                    alert_level = AlertLevel.CRITICAL
                    message = f"Daily budget exceeded: ${daily_spend/100:.2f} / ${daily_limit/100:.2f}"
                elif daily_percent >= threshold:
                    needs_alert = True
                    alert_level = AlertLevel.WARNING
                    message = f"Daily budget at {daily_percent:.0f}%: ${daily_spend/100:.2f} / ${daily_limit/100:.2f}"

            if monthly_limit and monthly_spend > 0:
                monthly_percent = (monthly_spend / monthly_limit) * 100
                if monthly_percent >= 100:
                    needs_alert = True
                    alert_level = AlertLevel.CRITICAL
                    message = f"Monthly budget exceeded: ${monthly_spend/100:.2f} / ${monthly_limit/100:.2f}"
                elif monthly_percent >= threshold and alert_level != AlertLevel.CRITICAL:
                    needs_alert = True
                    alert_level = AlertLevel.WARNING
                    message = f"Monthly budget at {monthly_percent:.0f}%: ${monthly_spend/100:.2f} / ${monthly_limit/100:.2f}"

            return {
                "budget_name": budget.get("name"),
                "budget_type": budget_type,
                "target": target,
                "daily_spend_cents": round(daily_spend, 2),
                "daily_limit_cents": daily_limit,
                "daily_percent": round((daily_spend / daily_limit * 100) if daily_limit else 0, 1),
                "monthly_spend_cents": round(monthly_spend, 2),
                "monthly_limit_cents": monthly_limit,
                "monthly_percent": round((monthly_spend / monthly_limit * 100) if monthly_limit else 0, 1),
                "needs_alert": needs_alert,
                "alert_level": alert_level.value if needs_alert else None,
                "message": message,
            }

        finally:
            conn.close()

    def record_alert(
        self,
        budget_name: str,
        alert_level: AlertLevel,
        message: str,
        current_spend: float,
        budget_limit: float,
    ) -> int:
        """Record a budget alert"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            percent_used = (current_spend / budget_limit * 100) if budget_limit else 0

            cursor.execute(
                """
                INSERT INTO budget_alerts
                (timestamp, budget_name, alert_level, message,
                 current_spend_cents, budget_limit_cents, percent_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().isoformat(),
                    budget_name,
                    alert_level.value,
                    message,
                    current_spend,
                    budget_limit,
                    percent_used,
                ),
            )
            conn.commit()
            return cursor.lastrowid

        finally:
            conn.close()

    def get_alerts(
        self,
        days: int = 7,
        unacknowledged_only: bool = False,
        level: Optional[AlertLevel] = None,
    ) -> List[Dict[str, Any]]:
        """Get budget alerts"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).isoformat()

            where = ["timestamp >= ?"]
            params: List[Any] = [since]

            if unacknowledged_only:
                where.append("acknowledged = 0")

            if level:
                where.append("alert_level = ?")
                params.append(level.value)

            cursor.execute(
                f"""
                SELECT * FROM budget_alerts
                WHERE {" AND ".join(where)}
                ORDER BY timestamp DESC
                LIMIT 100
            """,
                params,
            )

            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

        finally:
            conn.close()

    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "admin") -> bool:
        """Acknowledge an alert"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE budget_alerts
                SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), acknowledged_by, alert_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get cost summary with projections"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            today = datetime.now().strftime("%Y-%m-%d")

            # Total spend
            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT date) as days_with_data,
                    SUM(total_cost_cents) as total_cost,
                    SUM(total_requests) as total_requests
                FROM token_daily_stats
                WHERE date >= ?
            """,
                (since,),
            )
            row = cursor.fetchone()
            days_with_data = row[0] or 1
            total_cost = row[1] or 0
            total_requests = row[2] or 0

            # Today's spend
            cursor.execute(
                """
                SELECT SUM(total_cost_cents) FROM token_daily_stats WHERE date = ?
            """,
                (today,),
            )
            today_cost = cursor.fetchone()[0] or 0

            # Calculate projections
            avg_daily = total_cost / days_with_data if days_with_data > 0 else 0
            avg_per_request = total_cost / total_requests if total_requests > 0 else 0

            # Days remaining in month
            now = datetime.now()
            days_in_month = 30  # Approximate
            days_remaining = days_in_month - now.day

            projected_monthly = (total_cost / days_with_data * days_in_month) if days_with_data > 0 else 0

            # Trend calculation (compare last 7 days vs previous 7)
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

            cursor.execute(
                """
                SELECT SUM(total_cost_cents) FROM token_daily_stats
                WHERE date >= ? AND date < ?
            """,
                (week_ago, today),
            )
            last_week = cursor.fetchone()[0] or 0

            cursor.execute(
                """
                SELECT SUM(total_cost_cents) FROM token_daily_stats
                WHERE date >= ? AND date < ?
            """,
                (two_weeks_ago, week_ago),
            )
            prev_week = cursor.fetchone()[0] or 0

            if prev_week > 0:
                trend_percent = ((last_week - prev_week) / prev_week) * 100
                trend = "up" if trend_percent > 5 else ("down" if trend_percent < -5 else "stable")
            else:
                trend_percent = 0
                trend = "stable"

            return {
                "period_days": days,
                "total_cost_cents": round(total_cost, 2),
                "total_cost_dollars": round(total_cost / 100, 2),
                "today_cost_cents": round(today_cost, 2),
                "total_requests": total_requests,
                "avg_daily_cost_cents": round(avg_daily, 2),
                "avg_cost_per_request_cents": round(avg_per_request, 4),
                "projected_monthly_cents": round(projected_monthly, 2),
                "projected_monthly_dollars": round(projected_monthly / 100, 2),
                "trend": trend,
                "trend_percent": round(trend_percent, 1),
            }

        finally:
            conn.close()

    def setup_default_budgets(self):
        """Create default budgets if none exist"""
        budgets = self.get_budgets()
        if budgets:
            return

        # Global daily budget: $10
        self.create_budget(
            name="global_daily",
            budget_type=BudgetType.GLOBAL,
            daily_limit_cents=1000,  # $10
            alert_threshold_percent=80,
        )

        # Global monthly budget: $100
        self.create_budget(
            name="global_monthly",
            budget_type=BudgetType.GLOBAL,
            monthly_limit_cents=10000,  # $100
            alert_threshold_percent=80,
        )

        logger.info("Default budgets created")


# Global instance
_monitor: Optional[CostMonitor] = None


def get_cost_monitor(db_path: str = "/var/db/yori/audit.db") -> CostMonitor:
    """Get or create global cost monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = CostMonitor(db_path)
    return _monitor
