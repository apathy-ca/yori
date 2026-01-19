"""
Tests for YORI alert system
"""

import pytest
import asyncio
from pathlib import Path
from yori.alerts import (
    Alert,
    AlertManager,
    WebUIAlertChannel,
    EmailAlertChannel,
)


class TestAlert:
    """Test Alert dataclass"""

    def test_alert_creation(self):
        """Test creating an alert"""
        alert = Alert(
            timestamp="2026-01-19T21:00:00Z",
            user="alice",
            device="iphone",
            policy="bedtime",
            reason="Late night usage",
            mode="advisory",
            metadata={"hour": 21},
        )

        assert alert.user == "alice"
        assert alert.policy == "bedtime"
        assert alert.metadata["hour"] == 21

    def test_alert_to_dict(self):
        """Test converting alert to dictionary"""
        alert = Alert(
            timestamp="2026-01-19T21:00:00Z",
            user="bob",
            device="laptop",
            policy="high_usage",
            reason="Exceeded threshold",
            mode="advisory",
        )

        alert_dict = alert.to_dict()
        assert alert_dict["user"] == "bob"
        assert alert_dict["policy"] == "high_usage"
        assert "timestamp" in alert_dict


class TestWebUIAlertChannel:
    """Test web UI alert channel"""

    def test_send_alert(self, tmp_path):
        """Test sending alert to web UI (file storage)"""
        alerts_file = tmp_path / "alerts.json"
        channel = WebUIAlertChannel(alerts_file)

        alert = Alert(
            timestamp="2026-01-19T21:00:00Z",
            user="test",
            device="test",
            policy="test_policy",
            reason="Test alert",
            mode="advisory",
        )

        result = channel.send(alert)
        assert result is True
        assert alerts_file.exists()

    def test_multiple_alerts(self, tmp_path):
        """Test storing multiple alerts"""
        import json

        alerts_file = tmp_path / "alerts.json"
        channel = WebUIAlertChannel(alerts_file)

        # Send multiple alerts
        for i in range(5):
            alert = Alert(
                timestamp=f"2026-01-19T21:{i:02d}:00Z",
                user=f"user{i}",
                device="device",
                policy="test",
                reason=f"Alert {i}",
                mode="advisory",
            )
            channel.send(alert)

        # Read and verify
        with open(alerts_file) as f:
            stored = json.load(f)

        assert len(stored) == 5
        assert stored[0]["user"] == "user0"
        assert stored[4]["user"] == "user4"

    def test_alert_limit(self, tmp_path):
        """Test that only last 100 alerts are kept"""
        import json

        alerts_file = tmp_path / "alerts.json"
        channel = WebUIAlertChannel(alerts_file)

        # Send 150 alerts
        for i in range(150):
            alert = Alert(
                timestamp=f"2026-01-19T21:00:{i:02d}Z",
                user=f"user{i}",
                device="device",
                policy="test",
                reason=f"Alert {i}",
                mode="advisory",
            )
            channel.send(alert)

        # Should only keep last 100
        with open(alerts_file) as f:
            stored = json.load(f)

        assert len(stored) == 100
        # Should have alerts 50-149
        assert stored[0]["user"] == "user50"
        assert stored[99]["user"] == "user149"


class TestAlertManager:
    """Test alert manager"""

    @pytest.mark.asyncio
    async def test_send_alert(self, tmp_path):
        """Test sending alert through manager"""
        manager = AlertManager()

        # Add web UI channel
        alerts_file = tmp_path / "alerts.json"
        channel = WebUIAlertChannel(alerts_file)
        manager.add_channel(channel)

        # Send alert
        count = await manager.send_alert(
            user="alice",
            device="iphone",
            policy="bedtime",
            reason="Late night usage",
            mode="advisory",
            metadata={"hour": 22},
        )

        assert count == 1
        assert alerts_file.exists()

    @pytest.mark.asyncio
    async def test_multiple_channels(self, tmp_path):
        """Test sending to multiple channels"""
        manager = AlertManager()

        # Add multiple web UI channels (simulating different outputs)
        channel1 = WebUIAlertChannel(tmp_path / "alerts1.json")
        channel2 = WebUIAlertChannel(tmp_path / "alerts2.json")
        manager.add_channel(channel1)
        manager.add_channel(channel2)

        # Send alert
        count = await manager.send_alert(
            user="bob",
            device="laptop",
            policy="privacy",
            reason="PII detected",
            mode="advisory",
        )

        assert count == 2
        assert (tmp_path / "alerts1.json").exists()
        assert (tmp_path / "alerts2.json").exists()

    @pytest.mark.asyncio
    async def test_channel_failure(self, tmp_path):
        """Test handling channel failures"""
        manager = AlertManager()

        # Add one good channel and one that will fail
        good_channel = WebUIAlertChannel(tmp_path / "alerts.json")
        manager.add_channel(good_channel)

        # Add a channel that will fail (read-only dir)
        bad_path = tmp_path / "readonly" / "alerts.json"
        bad_path.parent.mkdir()
        bad_path.parent.chmod(0o444)  # Read-only
        bad_channel = WebUIAlertChannel(bad_path)
        manager.add_channel(bad_channel)

        # Send alert - should succeed for good channel
        count = await manager.send_alert(
            user="test",
            device="test",
            policy="test",
            reason="test",
            mode="advisory",
        )

        # At least one channel should succeed
        assert count >= 1

        # Clean up
        bad_path.parent.chmod(0o755)


class TestEmailAlertChannel:
    """Test email alert channel"""

    def test_email_creation(self):
        """Test email alert channel creation"""
        channel = EmailAlertChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_addr="yori@example.com",
            to_addrs=["admin@example.com"],
        )

        assert channel.smtp_host == "smtp.example.com"
        assert channel.smtp_port == 587

    def test_email_body_creation(self):
        """Test email body formatting"""
        channel = EmailAlertChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
        )

        alert = Alert(
            timestamp="2026-01-19T21:00:00Z",
            user="alice",
            device="iphone",
            policy="bedtime",
            reason="Late night usage",
            mode="advisory",
        )

        text = channel._create_text_body(alert)
        html = channel._create_html_body(alert)

        assert "alice" in text
        assert "bedtime" in text
        assert "alice" in html
        assert "<table" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
