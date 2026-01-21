"""
Integration tests for block page and override flow

Tests the complete end-to-end flow:
1. Request blocked by policy → block page displayed
2. Correct override password → request allowed
3. Wrong override password → block page shown again
4. Rate limiting → lockout after N attempts
5. Emergency override → all policies bypassed
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from yori.config import YoriConfig, EnforcementConfig
from yori.proxy import ProxyServer
from yori.enforcement import EnforcementDecision
from yori.override import hash_password, reset_override_rate_limit


@pytest.fixture
def test_config():
    """Create test configuration"""
    config = YoriConfig(
        mode="enforce",
        listen="127.0.0.1:8443",
    )

    # Set up enforcement config
    config.enforcement = EnforcementConfig(
        override_enabled=True,
        override_password_hash=hash_password("test123"),
        override_rate_limit=3,
        admin_token_hash=hash_password("admin_emergency"),
        custom_messages={
            "bedtime.rego": "LLM access is restricted after bedtime. Please try again tomorrow."
        }
    )

    return config


@pytest.fixture
def proxy_server(test_config):
    """Create proxy server instance"""
    server = ProxyServer(test_config)
    return server


@pytest.fixture
def client(proxy_server):
    """Create test client"""
    return TestClient(proxy_server.app)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limits before each test"""
    reset_override_rate_limit("testclient")
    yield
    reset_override_rate_limit("testclient")


class TestBlockPageFlow:
    """Test block page display and rendering"""

    @patch('yori.proxy.should_enforce_policy')
    def test_request_blocked_shows_block_page(self, mock_enforce, client):
        """Test that blocked request returns block page HTML"""
        # Mock enforcement decision to block
        mock_enforce.return_value = EnforcementDecision(
            should_block=True,
            policy_name="bedtime.rego",
            reason="LLM access not allowed after 21:00",
            timestamp=datetime.now(),
            allow_override=True,
        )

        # Send request
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
        )

        # Verify response
        assert response.status_code == 403
        assert "Request Blocked by YORI" in response.text
        assert "bedtime.rego" in response.text
        assert "LLM access not allowed after 21:00" in response.text
        assert "Override This Block" in response.text

    @patch('yori.proxy.should_enforce_policy')
    def test_allowed_request_no_block_page(self, mock_enforce, client):
        """Test that allowed request does not show block page"""
        # Mock enforcement decision to allow
        mock_enforce.return_value = EnforcementDecision(
            should_block=False,
            policy_name="allow.rego",
            reason="Request allowed",
            timestamp=datetime.now(),
            allow_override=False,
        )

        # Send request
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
        )

        # Verify no block page
        assert response.status_code == 200
        assert "Request Blocked by YORI" not in response.text

    @patch('yori.proxy.should_enforce_policy')
    def test_block_page_without_override_option(self, mock_enforce, client):
        """Test block page when override is not allowed"""
        # Mock enforcement decision to block without override
        mock_enforce.return_value = EnforcementDecision(
            should_block=True,
            policy_name="strict.rego",
            reason="Strict policy - no overrides allowed",
            timestamp=datetime.now(),
            allow_override=False,
        )

        # Send request
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
        )

        # Verify block page without override form
        assert response.status_code == 403
        assert "Request Blocked by YORI" in response.text
        assert "Override This Block" not in response.text
        assert 'name="password"' not in response.text


class TestOverrideFlow:
    """Test override password functionality"""

    def test_override_with_correct_password(self, client):
        """Test successful override with correct password"""
        response = client.post(
            "/yori/override",
            json={
                "password": "test123",
                "request_id": "test-request-123",
                "policy_name": "bedtime.rego",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successful" in data["message"].lower()

    def test_override_with_wrong_password(self, client):
        """Test failed override with wrong password"""
        response = client.post(
            "/yori/override",
            json={
                "password": "wrong_password",
                "request_id": "test-request-456",
                "policy_name": "bedtime.rego",
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "invalid" in data["message"].lower()

    def test_override_rate_limiting(self, client):
        """Test rate limiting on override attempts"""
        # Make 3 failed attempts (should all go through)
        for i in range(3):
            response = client.post(
                "/yori/override",
                json={
                    "password": "wrong",
                    "request_id": f"test-{i}",
                    "policy_name": "bedtime.rego",
                }
            )
            assert response.status_code == 401

        # 4th attempt should be rate limited
        response = client.post(
            "/yori/override",
            json={
                "password": "wrong",
                "request_id": "test-rate-limit",
                "policy_name": "bedtime.rego",
            }
        )

        assert response.status_code == 429
        data = response.json()
        assert data["success"] is False
        assert "too many" in data["message"].lower()

    def test_successful_override_resets_rate_limit(self, client):
        """Test that successful override resets rate limit"""
        # Make 2 failed attempts
        for i in range(2):
            client.post(
                "/yori/override",
                json={
                    "password": "wrong",
                    "request_id": f"test-{i}",
                    "policy_name": "bedtime.rego",
                }
            )

        # Successful override should reset counter
        response = client.post(
            "/yori/override",
            json={
                "password": "test123",
                "request_id": "test-success",
                "policy_name": "bedtime.rego",
            }
        )
        assert response.status_code == 200

        # Should be able to make more attempts now
        response = client.post(
            "/yori/override",
            json={
                "password": "wrong",
                "request_id": "test-after-reset",
                "policy_name": "bedtime.rego",
            }
        )
        assert response.status_code == 401  # Not rate limited


class TestEmergencyOverride:
    """Test emergency admin override functionality"""

    def test_emergency_override_with_correct_token(self, client):
        """Test successful emergency override"""
        response = client.post(
            "/yori/override",
            json={
                "password": "admin_emergency",
                "request_id": "emergency-123",
                "policy_name": "strict.rego",
                "emergency": True,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "emergency" in data["message"].lower()

    def test_emergency_override_with_wrong_token(self, client):
        """Test failed emergency override with wrong token"""
        response = client.post(
            "/yori/override",
            json={
                "password": "wrong_admin_token",
                "request_id": "emergency-456",
                "policy_name": "strict.rego",
                "emergency": True,
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False


class TestOverrideHeader:
    """Test X-YORI-Override header functionality"""

    @patch('yori.proxy.should_enforce_policy')
    def test_request_with_valid_override_header_allowed(self, mock_enforce, client):
        """Test that request with valid override header is allowed"""
        # Mock enforcement to block
        mock_enforce.return_value = EnforcementDecision(
            should_block=True,
            policy_name="bedtime.rego",
            reason="Blocked",
            timestamp=datetime.now(),
            allow_override=True,
        )

        # Send request with override header
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]},
            headers={"X-YORI-Override": "test123"}
        )

        # Should not be blocked
        assert response.status_code == 200
        assert "Request Blocked by YORI" not in response.text

    @patch('yori.proxy.should_enforce_policy')
    def test_request_with_invalid_override_header_blocked(self, mock_enforce, client):
        """Test that request with invalid override header is blocked"""
        # Mock enforcement to block
        mock_enforce.return_value = EnforcementDecision(
            should_block=True,
            policy_name="bedtime.rego",
            reason="Blocked",
            timestamp=datetime.now(),
            allow_override=True,
        )

        # Send request with invalid override header
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]},
            headers={"X-YORI-Override": "wrong_password"}
        )

        # Should be blocked
        assert response.status_code == 403
        assert "Request Blocked by YORI" in response.text


class TestCustomMessages:
    """Test custom block messages per policy"""

    @patch('yori.proxy.should_enforce_policy')
    def test_custom_message_displayed(self, mock_enforce, client):
        """Test that custom message for policy is displayed"""
        mock_enforce.return_value = EnforcementDecision(
            should_block=True,
            policy_name="bedtime.rego",
            reason="LLM access not allowed after 21:00",
            timestamp=datetime.now(),
            allow_override=True,
        )

        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
        )

        assert response.status_code == 403
        # Custom message should be in the response
        assert "bedtime" in response.text.lower() or "tomorrow" in response.text.lower()


class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_check_returns_status(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["mode"] == "enforce"
