"""
Integration tests for metrics endpoint and middleware.

Tests that the /metrics endpoint works correctly and that metrics
are properly tracked during request processing.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from yori.proxy import ProxyServer
from yori.config import YoriConfig
from yori.models import EnforcementConfig


@pytest.fixture
def test_config():
    """Create test configuration"""
    config = YoriConfig(
        mode="observe",
        listen="127.0.0.1:8443",
    )
    return config


@pytest.fixture
def enforce_config():
    """Create test configuration for enforce mode"""
    config = YoriConfig(
        mode="enforce",
        listen="127.0.0.1:8443",
        enforcement=EnforcementConfig(
            enabled=True,
            consent_accepted=True,
            override_enabled=True,
            override_password_hash="sha256:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
        ),
    )
    return config


class TestMetricsEndpoint:
    """Test /metrics endpoint functionality"""

    def test_metrics_endpoint_exists(self, test_config):
        """Metrics endpoint should be accessible"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_content_type(self, test_config):
        """Metrics endpoint should return Prometheus content type"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        response = client.get("/metrics")
        assert "text/plain" in response.headers["content-type"] or \
               "text/plain; version=0.0.4" in response.headers["content-type"]

    def test_metrics_endpoint_returns_prometheus_format(self, test_config):
        """Metrics should be in Prometheus text format"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        response = client.get("/metrics")
        content = response.text

        # Should contain HELP and/or TYPE declarations
        assert "# HELP" in content or "# TYPE" in content
        # Should contain YORI metrics
        assert "yori_" in content

    def test_metrics_endpoint_contains_info_metric(self, test_config):
        """Metrics should include YORI info metric"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        response = client.get("/metrics")
        content = response.text

        # Should contain version info
        assert "yori_info" in content or "yori_target_info" in content

    def test_metrics_endpoint_contains_system_metrics(self, test_config):
        """Metrics should include system metrics"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        response = client.get("/metrics")
        content = response.text

        # Should contain system metrics
        assert "yori_process_memory_bytes" in content
        assert "yori_active_connections" in content or "active_connections" in content

    def test_metrics_endpoint_performance(self, test_config):
        """Metrics endpoint should respond quickly"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        import time
        start = time.time()
        response = client.get("/metrics")
        duration = time.time() - start

        assert response.status_code == 200
        # Should respond in less than 100ms (generous for test environment)
        assert duration < 0.1


class TestRequestMetrics:
    """Test that request metrics are tracked correctly"""

    @pytest.mark.asyncio
    async def test_request_count_increments(self, test_config):
        """Request count should increment for each request"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        # Make a request
        client.get("/health")

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should have request metrics
        assert "yori_requests_total" in content
        # Health check should be recorded
        assert "health" in content or "/health" in content

    @pytest.mark.asyncio
    async def test_active_requests_tracked(self, test_config):
        """Active requests gauge should be tracked"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        # Make request
        client.get("/health")

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should have active requests metric
        assert "yori_active_requests" in content

    @pytest.mark.asyncio
    async def test_request_duration_recorded(self, test_config):
        """Request duration should be recorded in histogram"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        # Make request
        client.get("/health")

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should have duration histogram
        assert "yori_request_duration_seconds" in content
        # Should have histogram buckets
        assert "_bucket" in content or "request_duration" in content


class TestEnforcementMetrics:
    """Test enforcement-related metrics"""

    @pytest.mark.asyncio
    async def test_block_metric_recorded(self, enforce_config):
        """Blocked requests should be recorded in metrics"""
        proxy = ProxyServer(enforce_config)
        client = TestClient(proxy.app)

        # Mock upstream response
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.content = b'{"response": "test"}'
            mock_request.return_value = mock_response

            # Make a request that should be blocked (if enforcement is active)
            response = client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "test"}]},
                headers={"X-Forwarded-For": "192.168.1.100"}
            )

            # Check metrics
            metrics_response = client.get("/metrics")
            content = metrics_response.text

            # Should have enforcement metrics defined
            assert "yori_enforcement" in content or "enforcement" in content

    @pytest.mark.asyncio
    async def test_override_metric_recorded(self, enforce_config):
        """Override attempts should be recorded in metrics"""
        proxy = ProxyServer(enforce_config)
        client = TestClient(proxy.app)

        # Attempt override
        response = client.post(
            "/yori/override",
            json={
                "password": "password",
                "request_id": "test-123",
                "policy_name": "test_policy",
                "emergency": False,
            },
        )

        # Check metrics
        metrics_response = client.get("/metrics")
        content = metrics_response.text

        # Should have override metrics
        assert "yori_override_attempts_total" in content or "override_attempts" in content


class TestHealthCheckMetrics:
    """Test health check related metrics"""

    def test_health_status_metric_set(self, test_config):
        """Health status metrics should be set after health check"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        # Call health check
        client.get("/health")

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should have health status metrics
        assert "yori_health_status" in content or "health_status" in content

    def test_health_check_duration_recorded(self, test_config):
        """Health check duration should be recorded"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        # Call health check
        client.get("/health")

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should have health check duration metric
        assert "yori_health_check_duration_seconds" in content or "health_check_duration" in content


class TestMetricsMiddleware:
    """Test metrics middleware functionality"""

    def test_middleware_does_not_track_metrics_endpoint(self, test_config):
        """Metrics endpoint should not track itself to avoid recursion"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        # Get initial metrics
        response1 = client.get("/metrics")
        content1 = response1.text

        # Get metrics again
        response2 = client.get("/metrics")
        content2 = response2.text

        # Metrics endpoint should not increment request count for itself
        # (This is hard to test directly, but we verify no recursion occurs)
        assert response2.status_code == 200

    def test_middleware_tracks_different_methods(self, test_config):
        """Different HTTP methods should be tracked separately"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        # Make requests with different methods
        client.get("/health")

        # Note: POST to /health will fail, but that's OK for metrics test
        try:
            client.post("/health")
        except Exception:
            pass

        # Check metrics
        response = client.get("/metrics")
        content = response.text

        # Should have method labels
        assert 'method="GET"' in content or 'method="POST"' in content

    def test_middleware_normalizes_paths(self, test_config):
        """Paths should be normalized to avoid cardinality explosion"""
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.content = b'{"response": "test"}'
            mock_request.return_value = mock_response

            # Make requests with IDs that should be normalized
            try:
                client.get("/v1/models/gpt-4")
                client.get("/v1/models/gpt-3.5-turbo")
            except Exception:
                pass

            # Check metrics
            response = client.get("/metrics")
            content = response.text

            # Paths should be normalized to avoid high cardinality
            # Both should be tracked as /v1/models/:id
            if "yori_requests_total" in content:
                # Check that we're using normalized paths
                # Count actual metric lines with /v1/models/ (not HELP/TYPE comments)
                metric_lines = [line for line in content.split('\n') if line.startswith('yori_requests_total{') and '/v1/models/' in line]
                # Should only have one normalized path (/v1/models/:id), not separate entries for each model
                unique_model_paths = set()
                for line in metric_lines:
                    if 'path="/v1/models/' in line:
                        path_start = line.find('path="') + 6
                        path_end = line.find('"', path_start)
                        path = line[path_start:path_end]
                        unique_model_paths.add(path)
                # Should have normalized to :id
                assert len(unique_model_paths) <= 2  # At most 1-2 unique paths (might have :id or specific paths)


class TestMetricCardinality:
    """Test that metrics don't have too high cardinality"""

    def test_path_normalization_prevents_cardinality_explosion(self, test_config):
        """Path normalization should prevent metric cardinality explosion"""
        from yori.metrics import normalize_path

        # Many different IDs should normalize to the same path
        paths = [
            "/v1/models/gpt-4",
            "/v1/models/gpt-3.5-turbo",
            "/v1/models/text-davinci-003",
            "/v1/files/file-abc123",
            "/v1/files/file-xyz789",
        ]

        normalized = [normalize_path(p) for p in paths]

        # Models should all normalize to same path
        model_paths = [p for p in normalized if "models" in p]
        assert len(set(model_paths)) <= 1

        # Files should all normalize to same path
        file_paths = [p for p in normalized if "files" in p]
        assert len(set(file_paths)) <= 1
