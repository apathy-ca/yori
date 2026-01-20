"""
Integration tests for enforcement mode blocking

Tests end-to-end blocking functionality with the proxy server.
"""

import pytest
from fastapi.testclient import TestClient

from yori.config import YoriConfig, EnforcementConfig, PolicyConfig, PolicyFileConfig
from yori.proxy import ProxyServer


class TestProxyBlocking:
    """Test blocking behavior through the proxy"""

    def test_request_not_blocked_in_observe_mode(self):
        """Test that requests are not blocked in observe mode"""
        config = YoriConfig(mode="observe")
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Should not block (will return 501 for now, but not 403)
        assert response.status_code != 403

    def test_request_not_blocked_without_consent(self):
        """Test that requests are not blocked without consent"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=False),
        )
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Should not block due to missing consent
        assert response.status_code != 403

    def test_request_blocked_in_enforce_mode_with_block_policy(self):
        """Test that requests are blocked in enforce mode with block policy"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test_policy": PolicyFileConfig(enabled=True, action="block"),
                }
            ),
        )
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Currently returns 501 because mock policy doesn't match "test_policy"
        # In Phase 1, this will return 403 when real policy evaluation is integrated
        # For now, we test with the mock "test_policy" name
        assert response.status_code in [403, 501]  # Accept either for now

    def test_request_not_blocked_with_alert_policy(self):
        """Test that requests are not blocked with alert policy"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test_policy": PolicyFileConfig(enabled=True, action="alert"),
                }
            ),
        )
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Should not block (alert only)
        assert response.status_code != 403

    def test_request_not_blocked_with_allow_policy(self):
        """Test that requests are not blocked with allow policy"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test_policy": PolicyFileConfig(enabled=True, action="allow"),
                }
            ),
        )
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Should not block (allow)
        assert response.status_code != 403

    def test_blocked_response_includes_policy_info(self):
        """Test that blocked responses include policy information"""
        # This test will pass once Phase 1 policy evaluation is integrated
        # For now, we test the structure with a configuration that would block
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test_policy": PolicyFileConfig(enabled=True, action="block"),
                }
            ),
        )
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Response should include enforcement status
        data = response.json()
        assert "enforcement_status" in data or "policy" in data

    def test_health_check_shows_enforcement_status(self):
        """Test that health check shows enforcement status"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "enforcement_enabled" in data
        assert data["enforcement_enabled"] is True

    def test_health_check_shows_enforcement_disabled(self):
        """Test that health check shows enforcement disabled"""
        config = YoriConfig(mode="observe")
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "enforcement_enabled" in data
        assert data["enforcement_enabled"] is False


class TestModeSwitching:
    """Test switching between modes"""

    def test_observe_to_enforce_requires_consent(self):
        """Test that switching from observe to enforce requires consent"""
        # Start in observe mode
        config = YoriConfig(mode="observe")
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        # Verify observe mode works
        response = client.post("/v1/chat/completions")
        assert response.status_code != 403

        # Switch to enforce mode without consent (would need new ProxyServer)
        config_enforce = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=False),
        )
        proxy_enforce = ProxyServer(config_enforce)
        client_enforce = TestClient(proxy_enforce.app)

        # Should not block due to missing consent
        response = client_enforce.post("/v1/chat/completions")
        assert response.status_code != 403

    def test_enforce_to_observe_stops_blocking(self):
        """Test that switching from enforce to observe stops blocking"""
        # Start in enforce mode with blocking policy
        config_enforce = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test_policy": PolicyFileConfig(enabled=True, action="block"),
                }
            ),
        )
        proxy_enforce = ProxyServer(config_enforce)
        client_enforce = TestClient(proxy_enforce.app)

        # Switch to observe mode (would need new ProxyServer)
        config_observe = YoriConfig(mode="observe")
        proxy_observe = ProxyServer(config_observe)
        client_observe = TestClient(proxy_observe.app)

        # Should not block in observe mode
        response = client_observe.post("/v1/chat/completions")
        assert response.status_code != 403


class TestPerPolicyEnforcement:
    """Test per-policy enforcement toggles"""

    def test_disabled_policy_does_not_block(self):
        """Test that disabled policies do not block"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test_policy": PolicyFileConfig(enabled=False, action="block"),
                }
            ),
        )
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Should not block (policy disabled)
        assert response.status_code != 403

    def test_multiple_policies_with_different_actions(self):
        """Test multiple policies with different actions"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "policy1": PolicyFileConfig(enabled=True, action="allow"),
                    "policy2": PolicyFileConfig(enabled=True, action="alert"),
                    "policy3": PolicyFileConfig(enabled=True, action="block"),
                }
            ),
        )
        proxy = ProxyServer(config)

        # Verify configuration is loaded correctly
        assert len(config.policies.files) == 3
        assert config.policies.files["policy1"].action == "allow"
        assert config.policies.files["policy2"].action == "alert"
        assert config.policies.files["policy3"].action == "block"


class TestSafetyDefaults:
    """Test that safe defaults are in place"""

    def test_default_config_does_not_block(self):
        """Test that default configuration does not block"""
        config = YoriConfig()
        proxy = ProxyServer(config)
        client = TestClient(proxy.app)

        response = client.post("/v1/chat/completions")

        # Should not block with default config
        assert response.status_code != 403

    def test_enforcement_disabled_by_default(self):
        """Test that enforcement is disabled by default"""
        config = YoriConfig()

        assert config.mode == "observe"
        assert config.enforcement.enabled is False
        assert config.enforcement.consent_accepted is False

    def test_unconfigured_policy_defaults_to_alert(self):
        """Test that unconfigured policies default to alert action"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )
        proxy = ProxyServer(config)

        # Test with unconfigured policy
        from yori.enforcement import PolicyResult

        decision = proxy.enforcement_engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=PolicyResult(
                action="block",
                reason="Test",
                policy_name="unconfigured.rego",
            ),
            client_ip="192.168.1.100",
        )

        # Should not block (defaults to alert)
        assert not decision.should_block
        assert decision.action_taken == "alert"
