"""
YORI Alert System

Send advisory alerts via multiple channels (email, web, push notifications).
"""

import logging
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import httpx

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Advisory alert from policy evaluation"""
    timestamp: str
    user: str
    device: str
    policy: str
    reason: str
    mode: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class AlertChannel:
    """Base class for alert channels"""

    def send(self, alert: Alert) -> bool:
        """
        Send an alert.

        Args:
            alert: Alert to send

        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError


class EmailAlertChannel(AlertChannel):
    """Send alerts via email (SMTP)"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_addr: str,
        to_addrs: List[str],
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls

    def send(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"YORI Alert: {alert.policy}"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            # Create text and HTML versions
            text_body = self._create_text_body(alert)
            html_body = self._create_html_body(alert)

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            if self.use_tls:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_addr, self.to_addrs, msg.as_string())

            logger.info(f"Email alert sent: {alert.policy}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _create_text_body(self, alert: Alert) -> str:
        """Create plain text email body."""
        return f"""
YORI LLM Gateway Alert

Policy: {alert.policy}
Time: {alert.timestamp}
User: {alert.user}
Device: {alert.device}

Reason: {alert.reason}

Mode: {alert.mode}
"""

    def _create_html_body(self, alert: Alert) -> str:
        """Create HTML email body."""
        return f"""
<html>
<head></head>
<body>
    <h2>YORI LLM Gateway Alert</h2>
    <table border="1" cellpadding="5">
        <tr><th>Policy</th><td>{alert.policy}</td></tr>
        <tr><th>Time</th><td>{alert.timestamp}</td></tr>
        <tr><th>User</th><td>{alert.user}</td></tr>
        <tr><th>Device</th><td>{alert.device}</td></tr>
        <tr><th>Reason</th><td>{alert.reason}</td></tr>
        <tr><th>Mode</th><td>{alert.mode}</td></tr>
    </table>
</body>
</html>
"""


class WebhookAlertChannel(AlertChannel):
    """Send alerts via webhook (HTTP POST)"""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}

    async def send(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=alert.to_dict(),
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                logger.info(f"Webhook alert sent: {alert.policy}")
                return True

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class PushoverAlertChannel(AlertChannel):
    """Send alerts via Pushover"""

    def __init__(self, api_token: str, user_key: str):
        self.api_token = api_token
        self.user_key = user_key
        self.api_url = "https://api.pushover.net/1/messages.json"

    async def send(self, alert: Alert) -> bool:
        """Send alert via Pushover."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    data={
                        "token": self.api_token,
                        "user": self.user_key,
                        "title": f"YORI: {alert.policy}",
                        "message": alert.reason,
                        "priority": 0,  # Normal priority
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                logger.info(f"Pushover alert sent: {alert.policy}")
                return True

        except Exception as e:
            logger.error(f"Failed to send Pushover alert: {e}")
            return False


class GotifyAlertChannel(AlertChannel):
    """Send alerts via Gotify (self-hosted push notifications)"""

    def __init__(self, server_url: str, app_token: str):
        self.server_url = server_url.rstrip("/")
        self.app_token = app_token

    async def send(self, alert: Alert) -> bool:
        """Send alert via Gotify."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/message",
                    params={"token": self.app_token},
                    json={
                        "title": f"YORI: {alert.policy}",
                        "message": alert.reason,
                        "priority": 5,  # Normal priority
                        "extras": {
                            "client::display": {
                                "contentType": "text/plain"
                            }
                        },
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                logger.info(f"Gotify alert sent: {alert.policy}")
                return True

        except Exception as e:
            logger.error(f"Failed to send Gotify alert: {e}")
            return False


class WebUIAlertChannel(AlertChannel):
    """Store alerts for display in web UI"""

    def __init__(self, alerts_file: Path):
        self.alerts_file = alerts_file
        self.alerts_file.parent.mkdir(parents=True, exist_ok=True)

    def send(self, alert: Alert) -> bool:
        """Store alert in JSON file for web UI."""
        try:
            # Load existing alerts
            alerts = []
            if self.alerts_file.exists():
                with open(self.alerts_file, "r") as f:
                    alerts = json.load(f)

            # Add new alert
            alerts.append(alert.to_dict())

            # Keep only last 100 alerts
            alerts = alerts[-100:]

            # Save back
            with open(self.alerts_file, "w") as f:
                json.dump(alerts, f, indent=2)

            logger.info(f"Web UI alert stored: {alert.policy}")
            return True

        except Exception as e:
            logger.error(f"Failed to store web UI alert: {e}")
            return False


class AlertManager:
    """Manage and dispatch alerts to multiple channels"""

    def __init__(self):
        self.channels: List[AlertChannel] = []

    def add_channel(self, channel: AlertChannel):
        """Add an alert channel."""
        self.channels.append(channel)

    async def send_alert(
        self,
        user: str,
        device: str,
        policy: str,
        reason: str,
        mode: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Send alert to all configured channels.

        Args:
            user: User identifier
            device: Device identifier
            policy: Policy name
            reason: Alert reason
            mode: Policy mode
            metadata: Optional metadata

        Returns:
            Number of channels that successfully sent the alert
        """
        alert = Alert(
            timestamp=datetime.utcnow().isoformat(),
            user=user,
            device=device,
            policy=policy,
            reason=reason,
            mode=mode,
            metadata=metadata,
        )

        success_count = 0
        for channel in self.channels:
            try:
                # Handle both sync and async channels
                if hasattr(channel.send, "__await__"):
                    result = await channel.send(alert)
                else:
                    result = channel.send(alert)

                if result:
                    success_count += 1
            except Exception as e:
                logger.error(f"Alert channel error: {e}")

        logger.info(
            f"Alert sent to {success_count}/{len(self.channels)} channels: {policy}"
        )
        return success_count


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


async def send_alert(
    user: str,
    device: str,
    policy: str,
    reason: str,
    mode: str = "advisory",
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Convenience function to send alert using global manager.

    Returns:
        Number of successful deliveries
    """
    manager = get_alert_manager()
    return await manager.send_alert(user, device, policy, reason, mode, metadata)
