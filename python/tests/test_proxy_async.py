"""
Comprehensive async tests for YORI proxy server
Tests with real FastAPI async client and mocked backends
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx

from yori.proxy import ProxyServer
from yori.config import YoriConfig
from yori.models import PolicyDecision, OperationMode, LLMProvider, PolicyResult


@pytest.mark.asyncio
class TestProxyServerLifecycle:
    """Test proxy server startup and shutdown"""

    async def test_startup_initializes_resources(self, test_config):
        """Test that startup initializes all resources"""
        server = ProxyServer(test_config)

        # Before startup
        assert server._client is None
        assert server._audit_logger is None
        assert server._policy_evaluator is None

        # Startup
        await server.startup()

        # After startup
        assert server._client is not None
        assert server._audit_logger is not None
        assert server._policy_evaluator is not None

        # Cleanup
        await server.shutdown()

    async def test_shutdown_closes_client(self, test_config):
        """Test that shutdown closes HTTP client"""
        server = ProxyServer(test_config)
        await server.startup()

        # Client should be open
        assert server._client is not None
        assert not server._client.is_closed

        await server.shutdown()

        # Client should be closed
        assert server._client.is_closed

    async def test_startup_creates_audit_logger(self, test_config):
        """Test that startup creates audit logger"""
        server = ProxyServer(test_config)
        await server.startup()

        assert server._audit_logger is not None
        assert server._audit_logger.db_path == test_config.audit.database

        await server.shutdown()

    async def test_startup_creates_policy_evaluator(self, test_config):
        """Test that startup creates policy evaluator"""
        server = ProxyServer(test_config)
        await server.startup()

        assert server._policy_evaluator is not None

        await server.shutdown()


class TestProxyServerEndpoints:
    """Test proxy server HTTP endpoints"""

    def test_health_endpoint(self, test_config):
        """Test health check endpoint"""
        server = ProxyServer(test_config)
        client = TestClient(server.app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["mode"] == test_config.mode
        assert "endpoints" in data
        assert "uptime_seconds" in data

    def test_stats_endpoint_before_init(self, test_config):
        """Test stats endpoint before initialization"""
        server = ProxyServer(test_config)
        client = TestClient(server.app)

        response = client.get("/api/stats")

        # Should return 503 when audit logger not initialized
        assert response.status_code == 503
        assert "error" in response.json()

    def test_audit_endpoint_before_init(self, test_config):
        """Test audit endpoint before initialization"""
        server = ProxyServer(test_config)
        client = TestClient(server.app)

        response = client.get("/api/audit")

        # Should return 503 when audit logger not initialized
        assert response.status_code == 503


@pytest.mark.asyncio
class TestProxyRequestHandling:
    """Test proxy request handling logic"""

    async def test_is_endpoint_enabled_configured(self, test_config):
        """Test endpoint enabled check for configured endpoints"""
        server = ProxyServer(test_config)

        assert server._is_endpoint_enabled("api.openai.com") == True
        assert server._is_endpoint_enabled("api.anthropic.com") == True

    async def test_is_endpoint_enabled_unknown(self, observe_config):
        """Test unknown endpoint in observe mode"""
        server = ProxyServer(observe_config)

        # In observe mode, unknown endpoints are allowed
        assert server._is_endpoint_enabled("unknown.com") == True

    async def test_is_endpoint_enabled_unknown_enforce(self, enforce_config):
        """Test unknown endpoint in enforce mode"""
        server = ProxyServer(enforce_config)

        # In enforce mode, unknown endpoints are blocked
        assert server._is_endpoint_enabled("unknown.com") == False

    async def test_should_block_request_observe_mode(self, observe_config):
        """Test that observe mode never blocks"""
        server = ProxyServer(observe_config)

        # Even with BLOCK decision, observe mode doesn't block
        policy_result = PolicyResult(
            decision=PolicyDecision.BLOCK,
            policy_name="test_policy",
            reason="Test block",
        )

        assert server._should_block_request(policy_result) == False

    async def test_should_block_request_advisory_mode(self, advisory_config):
        """Test that advisory mode never blocks"""
        server = ProxyServer(advisory_config)

        policy_result = PolicyResult(
            decision=PolicyDecision.BLOCK,
            policy_name="test_policy",
            reason="Test block",
        )

        assert server._should_block_request(policy_result) == False

    async def test_should_block_request_enforce_mode_allow(self, enforce_config):
        """Test enforce mode with allow decision"""
        server = ProxyServer(enforce_config)

        policy_result = PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name="test_policy",
            reason="Test allow",
        )

        assert server._should_block_request(policy_result) == False

    async def test_should_block_request_enforce_mode_block(self, enforce_config):
        """Test enforce mode with block decision"""
        server = ProxyServer(enforce_config)

        policy_result = PolicyResult(
            decision=PolicyDecision.BLOCK,
            policy_name="test_policy",
            reason="Test block",
        )

        assert server._should_block_request(policy_result) == True

    async def test_evaluate_policy_no_evaluator(self, test_config):
        """Test policy evaluation when no evaluator configured"""
        server = ProxyServer(test_config)
        server._policy_evaluator = None

        result = await server._evaluate_policy(
            source_ip="192.168.1.100",
            host="api.openai.com",
            path="/v1/chat/completions",
            method="POST",
            body=b'{"test": "data"}',
            provider=LLMProvider.OPENAI,
        )

        assert result.decision == PolicyDecision.ALLOW
        assert result.policy_name == "default"
        assert "No policy evaluator" in result.reason


@pytest.mark.asyncio
class TestProxyLogging:
    """Test proxy audit logging"""

    async def test_log_successful_request(self, test_config):
        """Test logging successful request"""
        server = ProxyServer(test_config)
        await server.startup()

        policy_result = PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name="default",
            reason="Test allow",
        )

        await server._log_successful_request(
            source_ip="192.168.1.100",
            host="api.openai.com",
            path="v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            request_body=b'{"test": "request"}',
            response_body=b'{"test": "response"}',
            status_code=200,
            latency_ms=15.5,
            policy_result=policy_result,
        )

        # Verify event was logged
        events = await server._audit_logger.get_events(limit=10)
        assert len(events) == 1
        assert events[0].status_code == 200
        assert events[0].latency_ms == 15.5

        await server.shutdown()

    async def test_log_blocked_request(self, test_config):
        """Test logging blocked request"""
        server = ProxyServer(test_config)
        await server.startup()

        policy_result = PolicyResult(
            decision=PolicyDecision.BLOCK,
            policy_name="bedtime",
            reason="After bedtime",
        )

        await server._log_blocked_request(
            source_ip="192.168.1.100",
            host="api.openai.com",
            path="v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            request_body=b'{"test": "request"}',
            start_time=0,
            error="Policy violation",
            policy_result=policy_result,
        )

        events = await server._audit_logger.get_events(limit=10)
        assert len(events) == 1
        assert events[0].policy_decision == PolicyDecision.BLOCK
        assert events[0].policy_name == "bedtime"

        await server.shutdown()

    async def test_log_error_request(self, test_config):
        """Test logging error request"""
        server = ProxyServer(test_config)
        await server.startup()

        policy_result = PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name="default",
            reason="Test",
        )

        await server._log_error_request(
            source_ip="192.168.1.100",
            host="api.openai.com",
            path="v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            request_body=b'{"test": "request"}',
            latency_ms=100.0,
            error="Connection timeout",
            policy_result=policy_result,
        )

        events = await server._audit_logger.get_events(limit=10)
        assert len(events) == 1
        assert events[0].error == "Connection timeout"
        assert events[0].status_code == 502

        await server.shutdown()


@pytest.mark.asyncio
@pytest.mark.skip(reason="TestClient doesn't support lifespan async, needs real server")
class TestProxyIntegration:
    """Integration tests for full proxy flow"""

    async def test_full_request_flow_observe_mode(self, observe_config):
        """Test complete request flow in observe mode"""
        server = ProxyServer(observe_config)
        await server.startup()

        # Mock httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"choices": [{"message": {"content": "Hello!"}}]}'

        server._client.request = AsyncMock(return_value=mock_response)

        # Make test request via TestClient
        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": [{"role": "user", "content": "Hi"}]},
                headers={"host": "api.openai.com"},
            )

            assert response.status_code == 200

        # Verify event was logged
        events = await server._audit_logger.get_events(limit=10)
        assert len(events) == 1
        assert events[0].provider == LLMProvider.OPENAI

        await server.shutdown()

    async def test_disabled_endpoint_blocks(self, test_config):
        """Test that disabled endpoints are blocked"""
        # Disable OpenAI endpoint
        test_config.endpoints[0].enabled = False

        server = ProxyServer(test_config)
        await server.startup()

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": []},
                headers={"host": "api.openai.com"},
            )

            assert response.status_code == 403
            assert "not enabled" in response.json()["error"].lower()

        await server.shutdown()

    async def test_enforce_mode_blocks_violations(self, enforce_config):
        """Test that enforce mode blocks policy violations"""
        server = ProxyServer(enforce_config)
        await server.startup()

        # Mock policy evaluator to return BLOCK
        mock_policy_result = PolicyResult(
            decision=PolicyDecision.BLOCK,
            policy_name="test_policy",
            reason="Test block reason",
        )
        server._policy_evaluator.evaluate = AsyncMock(return_value=mock_policy_result)

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": []},
                headers={"host": "api.openai.com"},
            )

            assert response.status_code == 403
            data = response.json()
            assert "blocked by policy" in data["error"].lower()
            assert data["policy"] == "test_policy"

        await server.shutdown()

    async def test_proxy_forwards_to_backend(self, observe_config):
        """Test that proxy forwards requests to backend"""
        server = ProxyServer(observe_config)
        await server.startup()

        # Mock backend response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json", "x-custom": "value"}
        mock_response.content = b'{"result": "success"}'

        server._client.request = AsyncMock(return_value=mock_response)

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": []},
                headers={"host": "api.openai.com", "authorization": "Bearer test"},
            )

            assert response.status_code == 200
            assert response.json() == {"result": "success"}

            # Verify httpx was called
            server._client.request.assert_called_once()
            call_kwargs = server._client.request.call_args[1]
            assert call_kwargs["method"] == "POST"
            assert "v1/chat/completions" in call_kwargs["url"]

        await server.shutdown()

    async def test_proxy_handles_backend_errors(self, observe_config):
        """Test proxy handles backend errors gracefully"""
        server = ProxyServer(observe_config)
        await server.startup()

        # Mock backend error
        server._client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": []},
                headers={"host": "api.openai.com"},
            )

            assert response.status_code == 502
            assert "failed to forward" in response.json()["error"].lower()

        # Verify error was logged
        events = await server._audit_logger.get_events(limit=10)
        assert len(events) == 1
        assert events[0].error is not None
        assert "Connection refused" in events[0].error

        await server.shutdown()

    async def test_proxy_copies_headers(self, observe_config):
        """Test that proxy copies request headers"""
        server = ProxyServer(observe_config)
        await server.startup()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'{}'

        server._client.request = AsyncMock(return_value=mock_response)

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                headers={
                    "host": "api.openai.com",
                    "authorization": "Bearer test_key",
                    "x-custom-header": "custom_value",
                },
            )

            # Verify headers were passed (minus host and content-length)
            call_kwargs = server._client.request.call_args[1]
            headers = call_kwargs["headers"]

            assert "authorization" in headers
            assert headers["authorization"] == "Bearer test_key"
            assert "x-custom-header" in headers
            assert "host" not in headers  # Should be removed

        await server.shutdown()


class TestProxyServerConfiguration:
    """Test proxy server configuration"""

    def test_server_creation(self, test_config):
        """Test creating proxy server"""
        server = ProxyServer(test_config)

        assert server.config == test_config
        assert server.app is not None
        assert server.app.title == "YORI LLM Gateway"
        assert server.app.version == "0.1.0"

    def test_server_stores_config(self, test_config):
        """Test server stores configuration"""
        server = ProxyServer(test_config)

        assert server.config.mode == "observe"
        assert server.config.listen == "127.0.0.1:8443"
        assert len(server.config.endpoints) == 4

    def test_server_tracks_start_time(self, test_config):
        """Test server tracks start time"""
        server = ProxyServer(test_config)

        assert server._start_time > 0
        assert server._start_time <= __import__('time').time()


@pytest.mark.asyncio
class TestProxyPolicyIntegration:
    """Test policy evaluation integration"""

    async def test_evaluate_policy_calls_evaluator(self, test_config):
        """Test that policy evaluation calls the evaluator"""
        server = ProxyServer(test_config)
        await server.startup()

        # Mock evaluator
        mock_result = PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name="test_policy",
            reason="Test reason",
        )
        server._policy_evaluator.evaluate = AsyncMock(return_value=mock_result)

        result = await server._evaluate_policy(
            source_ip="192.168.1.100",
            host="api.openai.com",
            path="/v1/chat/completions",
            method="POST",
            body=b'{"test": "data"}',
            provider=LLMProvider.OPENAI,
        )

        assert result.decision == PolicyDecision.ALLOW
        assert result.policy_name == "test_policy"

        # Verify evaluator was called
        server._policy_evaluator.evaluate.assert_called_once()

        await server.shutdown()

    async def test_different_operation_modes(self):
        """Test all operation modes"""
        for mode in ["observe", "advisory", "enforce"]:
            config = YoriConfig(mode=mode, listen="127.0.0.1:8443")
            server = ProxyServer(config)

            assert server.config.mode == mode

            # Test blocking behavior
            policy_result = PolicyResult(
                decision=PolicyDecision.BLOCK,
                policy_name="test",
                reason="Test",
            )

            should_block = server._should_block_request(policy_result)

            if mode == "enforce":
                assert should_block == True
            else:
                assert should_block == False


@pytest.mark.asyncio
@pytest.mark.skip(reason="Needs full server with lifespan support")
class TestProxyErrorHandling:
    """Test proxy error handling"""

    async def test_handles_invalid_json(self, observe_config):
        """Test handling invalid JSON in request"""
        server = ProxyServer(observe_config)
        await server.startup()

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {}
        mock_response.content = b'{"error": "invalid json"}'

        server._client.request = AsyncMock(return_value=mock_response)

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                data="invalid json{",  # Invalid JSON
                headers={"host": "api.openai.com", "content-type": "application/json"},
            )

            # Should forward the request even with invalid JSON
            # (provider will reject it)
            assert response.status_code == 400

        await server.shutdown()

    async def test_handles_network_timeout(self, observe_config):
        """Test handling network timeouts"""
        server = ProxyServer(observe_config)
        await server.startup()

        server._client.request = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": []},
                headers={"host": "api.openai.com"},
            )

            assert response.status_code == 502

        # Verify error logged
        events = await server._audit_logger.get_events(limit=10)
        assert len(events) == 1
        assert "Timeout" in events[0].error

        await server.shutdown()

    async def test_handles_dns_failure(self, observe_config):
        """Test handling DNS failures"""
        server = ProxyServer(observe_config)
        await server.startup()

        server._client.request = AsyncMock(
            side_effect=httpx.ConnectError("Name or service not known")
        )

        with TestClient(server.app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4", "messages": []},
                headers={"host": "api.openai.com"},
            )

            assert response.status_code == 502

        await server.shutdown()
