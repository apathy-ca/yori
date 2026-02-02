"""
YORI Token Tracking Module

Extracts token usage from LLM API responses and stores in database.
Supports OpenAI, Anthropic, Google, and Mistral API formats.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Token cost per 1K tokens (in cents) - approximate pricing as of 2024
TOKEN_COSTS = {
    "api.openai.com": {
        "gpt-4": {"input": 3.0, "output": 6.0},
        "gpt-4-turbo": {"input": 1.0, "output": 3.0},
        "gpt-4o": {"input": 0.5, "output": 1.5},
        "gpt-4o-mini": {"input": 0.015, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.05, "output": 0.15},
        "default": {"input": 0.5, "output": 1.5},
    },
    "api.anthropic.com": {
        "claude-3-opus": {"input": 1.5, "output": 7.5},
        "claude-3-sonnet": {"input": 0.3, "output": 1.5},
        "claude-3-haiku": {"input": 0.025, "output": 0.125},
        "claude-3.5-sonnet": {"input": 0.3, "output": 1.5},
        "default": {"input": 0.3, "output": 1.5},
    },
    "generativelanguage.googleapis.com": {
        "gemini-pro": {"input": 0.05, "output": 0.15},
        "gemini-1.5-pro": {"input": 0.125, "output": 0.375},
        "gemini-1.5-flash": {"input": 0.0075, "output": 0.03},
        "default": {"input": 0.05, "output": 0.15},
    },
    "api.mistral.ai": {
        "mistral-large": {"input": 0.4, "output": 1.2},
        "mistral-medium": {"input": 0.27, "output": 0.81},
        "mistral-small": {"input": 0.1, "output": 0.3},
        "default": {"input": 0.1, "output": 0.3},
    },
}


class TokenTracker:
    """Tracks token usage from LLM API responses"""

    def __init__(self, db_path: str = "/var/db/yori/audit.db"):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure token tracking tables exist"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Token usage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    request_id TEXT,
                    client_ip TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    model TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost_cents REAL DEFAULT 0,
                    request_path TEXT,
                    UNIQUE(request_id)
                )
            """)

            # Daily aggregates for fast queries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    client_ip TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    model TEXT,
                    total_requests INTEGER DEFAULT 0,
                    total_input_tokens INTEGER DEFAULT 0,
                    total_output_tokens INTEGER DEFAULT 0,
                    total_cost_cents REAL DEFAULT 0,
                    UNIQUE(date, client_ip, endpoint, model)
                )
            """)

            # Budgets table
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

            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON token_usage(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_client ON token_usage(client_ip)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_daily_date ON token_daily_stats(date)")

            conn.commit()
            logger.info("Token tracking schema initialized")
        finally:
            conn.close()

    def extract_tokens_from_response(
        self, endpoint: str, response_body: bytes, request_path: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Extract token usage from LLM API response body.

        Returns dict with: model, input_tokens, output_tokens, total_tokens
        """
        try:
            data = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        # OpenAI format
        if "api.openai.com" in endpoint:
            return self._extract_openai_tokens(data)

        # Anthropic format
        if "api.anthropic.com" in endpoint:
            return self._extract_anthropic_tokens(data)

        # Google format
        if "googleapis.com" in endpoint:
            return self._extract_google_tokens(data)

        # Mistral format
        if "api.mistral.ai" in endpoint:
            return self._extract_mistral_tokens(data)

        return None

    def _extract_openai_tokens(self, data: Dict) -> Optional[Dict[str, Any]]:
        """Extract tokens from OpenAI API response"""
        usage = data.get("usage", {})
        if not usage:
            return None

        model = data.get("model", "unknown")
        return {
            "model": model,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

    def _extract_anthropic_tokens(self, data: Dict) -> Optional[Dict[str, Any]]:
        """Extract tokens from Anthropic API response"""
        usage = data.get("usage", {})
        if not usage:
            return None

        model = data.get("model", "unknown")
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

    def _extract_google_tokens(self, data: Dict) -> Optional[Dict[str, Any]]:
        """Extract tokens from Google Gemini API response"""
        usage = data.get("usageMetadata", {})
        if not usage:
            return None

        model = data.get("modelVersion", "gemini")
        return {
            "model": model,
            "input_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        }

    def _extract_mistral_tokens(self, data: Dict) -> Optional[Dict[str, Any]]:
        """Extract tokens from Mistral API response"""
        usage = data.get("usage", {})
        if not usage:
            return None

        model = data.get("model", "mistral")
        return {
            "model": model,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

    def calculate_cost(
        self, endpoint: str, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost in cents based on token usage"""
        # Find endpoint pricing
        endpoint_pricing = TOKEN_COSTS.get(endpoint, {})
        if not endpoint_pricing:
            # Use default OpenAI pricing
            endpoint_pricing = TOKEN_COSTS["api.openai.com"]

        # Find model pricing
        model_pricing = None
        model_lower = model.lower() if model else ""

        for model_key, pricing in endpoint_pricing.items():
            if model_key != "default" and model_key in model_lower:
                model_pricing = pricing
                break

        if not model_pricing:
            model_pricing = endpoint_pricing.get("default", {"input": 0.5, "output": 1.5})

        # Calculate cost (price is per 1K tokens)
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]

        return round(input_cost + output_cost, 4)

    def record_usage(
        self,
        client_ip: str,
        endpoint: str,
        token_info: Dict[str, Any],
        request_id: Optional[str] = None,
        request_path: Optional[str] = None,
    ) -> bool:
        """Record token usage to database"""
        if not token_info:
            return False

        model = token_info.get("model", "unknown")
        input_tokens = token_info.get("input_tokens", 0)
        output_tokens = token_info.get("output_tokens", 0)
        total_tokens = token_info.get("total_tokens", 0)

        cost_cents = self.calculate_cost(endpoint, model, input_tokens, output_tokens)
        timestamp = datetime.now().isoformat()
        date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Insert usage record
            cursor.execute(
                """
                INSERT OR REPLACE INTO token_usage
                (timestamp, request_id, client_ip, endpoint, model,
                 input_tokens, output_tokens, total_tokens, cost_cents, request_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    request_id,
                    client_ip,
                    endpoint,
                    model,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    cost_cents,
                    request_path,
                ),
            )

            # Update daily stats
            cursor.execute(
                """
                INSERT INTO token_daily_stats
                (date, client_ip, endpoint, model, total_requests,
                 total_input_tokens, total_output_tokens, total_cost_cents)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(date, client_ip, endpoint, model) DO UPDATE SET
                    total_requests = total_requests + 1,
                    total_input_tokens = total_input_tokens + excluded.total_input_tokens,
                    total_output_tokens = total_output_tokens + excluded.total_output_tokens,
                    total_cost_cents = total_cost_cents + excluded.total_cost_cents
            """,
                (date, client_ip, endpoint, model, input_tokens, output_tokens, cost_cents),
            )

            conn.commit()
            logger.debug(
                f"Recorded {total_tokens} tokens ({cost_cents}c) for {client_ip} -> {endpoint}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record token usage: {e}")
            return False
        finally:
            conn.close()

    def get_usage_stats(
        self, client_ip: Optional[str] = None, days: int = 7
    ) -> Dict[str, Any]:
        """Get token usage statistics"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            # Build query
            where = "WHERE date >= ?"
            params: List[Any] = [since]

            if client_ip:
                where += " AND client_ip = ?"
                params.append(client_ip)

            # Total stats
            cursor.execute(
                f"""
                SELECT
                    SUM(total_requests) as requests,
                    SUM(total_input_tokens) as input_tokens,
                    SUM(total_output_tokens) as output_tokens,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                {where}
            """,
                params,
            )
            row = cursor.fetchone()

            # By endpoint
            cursor.execute(
                f"""
                SELECT
                    endpoint,
                    SUM(total_requests) as requests,
                    SUM(total_input_tokens + total_output_tokens) as tokens,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                {where}
                GROUP BY endpoint
                ORDER BY cost_cents DESC
            """,
                params,
            )
            by_endpoint = [
                {
                    "endpoint": r[0],
                    "requests": r[1],
                    "tokens": r[2],
                    "cost_cents": round(r[3], 2),
                }
                for r in cursor.fetchall()
            ]

            # By day
            cursor.execute(
                f"""
                SELECT
                    date,
                    SUM(total_requests) as requests,
                    SUM(total_input_tokens + total_output_tokens) as tokens,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                {where}
                GROUP BY date
                ORDER BY date
            """,
                params,
            )
            by_day = [
                {
                    "date": r[0],
                    "requests": r[1],
                    "tokens": r[2],
                    "cost_cents": round(r[3], 2),
                }
                for r in cursor.fetchall()
            ]

            return {
                "period_days": days,
                "total_requests": row[0] or 0,
                "total_input_tokens": row[1] or 0,
                "total_output_tokens": row[2] or 0,
                "total_cost_cents": round(row[3] or 0, 2),
                "by_endpoint": by_endpoint,
                "by_day": by_day,
            }

        finally:
            conn.close()

    def get_device_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get usage breakdown by device"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            cursor.execute(
                """
                SELECT
                    client_ip,
                    SUM(total_requests) as requests,
                    SUM(total_input_tokens + total_output_tokens) as tokens,
                    SUM(total_cost_cents) as cost_cents
                FROM token_daily_stats
                WHERE date >= ?
                GROUP BY client_ip
                ORDER BY cost_cents DESC
            """,
                (since,),
            )

            return [
                {
                    "client_ip": r[0],
                    "requests": r[1],
                    "tokens": r[2],
                    "cost_cents": round(r[3], 2),
                }
                for r in cursor.fetchall()
            ]

        finally:
            conn.close()

    def get_today_usage(self, client_ip: Optional[str] = None) -> Dict[str, Any]:
        """Get today's usage for policy evaluation"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")

            if client_ip:
                cursor.execute(
                    """
                    SELECT
                        SUM(total_requests),
                        SUM(total_input_tokens + total_output_tokens),
                        SUM(total_cost_cents)
                    FROM token_daily_stats
                    WHERE date = ? AND client_ip = ?
                """,
                    (today, client_ip),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        SUM(total_requests),
                        SUM(total_input_tokens + total_output_tokens),
                        SUM(total_cost_cents)
                    FROM token_daily_stats
                    WHERE date = ?
                """,
                    (today,),
                )

            row = cursor.fetchone()
            return {
                "daily_request_count": row[0] or 0,
                "daily_tokens": row[1] or 0,
                "daily_cost_cents": round(row[2] or 0, 2),
            }

        finally:
            conn.close()


# Global instance
_tracker: Optional[TokenTracker] = None


def get_token_tracker(db_path: str = "/var/db/yori/audit.db") -> TokenTracker:
    """Get or create global token tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = TokenTracker(db_path)
    return _tracker
