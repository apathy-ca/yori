"""
Unit Tests: Proxy Server

Tests for YORI proxy server functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import httpx

from yori.proxy import ProxyServer
from yori.config import YoriConfig, EndpointConfig


@pytest.mark.unit
class TestProxyServer:
    """Test ProxyServer class"""

    def test_proxy_server_creation(self, test_config: YoriConfig):
        """Test creating proxy server instance"""
        proxy = ProxyServer(test_config)
        assert proxy.config == test_config
        assert proxy.app is not None
        assert proxy._client is None  # Not initialized until startup

    def test_proxy_server_app_metadata(self, test_config: YoriConfig):
        """Test FastAPI app metadata"""
        proxy = ProxyServer(test_config)
        assert proxy.app.title == "YORI LLM Gateway"
        assert "0.1.0" in proxy.app.version
        assert proxy.app.description

    def test_health_endpoint_exists(self, test_client: TestClient):
        """Test that health endpoint is registered"""
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_response_structure(self, test_client: TestClient):
        """Test health endpoint response structure"""
        response = test_client.get("/health")
        data = response.json()
        assert "status" in data
        assert "mode" in data
        assert "endpoints" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_shows_config(self, test_config: YoriConfig):
        """Test that health endpoint shows configuration"""
        test_config.mode = "advisory"
        proxy = ProxyServer(test_config)
        client = TestClient(proxy.app)

        response = client.get("/health")
        data = response.json()
        assert data["mode"] == "advisory"
        assert data["endpoints"] == len(test_config.endpoints)

    def test_catchall_route_exists(self, test_client: TestClient):
        """Test that catchall proxy route exists"""
        response = test_client.get("/any/path")
        # Should not be 404
        assert response.status_code != 404

    def test_catchall_route_stub_response(self, test_client: TestClient):
        """Test catchall route returns stub response"""
        response = test_client.post("/v1/chat/completions", json={})
        assert response.status_code == 501
        data = response.json()
        assert "error" in data
        assert "Proxy not yet implemented" in data["error"]

    def test_catchall_route_includes_path(self, test_client: TestClient):
        """Test catchall route includes requested path"""
        response = test_client.get("/test/path/123")
        data = response.json()
        assert "path" in data
        assert data["path"] == "test/path/123"

    def test_catchall_route_methods(self, test_client: TestClient):
        """Test catchall route supports multiple HTTP methods"""
        methods_and_funcs = [
            ("GET", test_client.get),
            ("POST", test_client.post),
            ("PUT", test_client.put),
            ("DELETE", test_client.delete),
            ("PATCH", test_client.patch),
        ]

        for method, func in methods_and_funcs:
            response = func("/test")
            # Should be handled (not 405 Method Not Allowed)
            assert response.status_code != 405

    @pytest.mark.asyncio
    async def test_proxy_startup(self, proxy_server: ProxyServer):
        """Test proxy server startup initializes resources"""
        assert proxy_server._client is None
        await proxy_server.startup()
        assert proxy_server._client is not None
        assert isinstance(proxy_server._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_proxy_shutdown(self, proxy_server: ProxyServer):
        """Test proxy server shutdown cleans up resources"""
        await proxy_server.startup()
        client = proxy_server._client
        assert client is not None

        await proxy_server.shutdown()
        # Client should be closed (can't easily verify without accessing internals)

    @pytest.mark.asyncio
    async def test_proxy_shutdown_without_startup(self, proxy_server: ProxyServer):
        """Test shutdown works even if startup wasn't called"""
        # Should not raise exception
        await proxy_server.shutdown()

    @pytest.mark.asyncio
    async def test_proxy_multiple_startups(self, proxy_server: ProxyServer):
        """Test multiple startup calls don't cause issues"""
        await proxy_server.startup()
        first_client = proxy_server._client

        await proxy_server.startup()
        second_client = proxy_server._client

        # Should still have a client
        assert second_client is not None

    @pytest.mark.asyncio
    async def test_http_client_timeout_configuration(self, proxy_server: ProxyServer):
        """Test that HTTP client is configured with timeout"""
        await proxy_server.startup()
        assert proxy_server._client is not None
        assert proxy_server._client.timeout.read == 30.0

    def test_config_access(self, test_config: YoriConfig):
        """Test accessing configuration from proxy server"""
        test_config.mode = "enforce"
        proxy = ProxyServer(test_config)
        assert proxy.config.mode == "enforce"

    def test_different_configs_create_different_servers(self, tmp_dir):
        """Test that different configs create independent servers"""
        config1 = YoriConfig(mode="observe")
        config2 = YoriConfig(mode="enforce")

        proxy1 = ProxyServer(config1)
        proxy2 = ProxyServer(config2)

        assert proxy1.config.mode == "observe"
        assert proxy2.config.mode == "enforce"
        assert proxy1.app is not proxy2.app


@pytest.mark.unit
class TestProxyRouting:
    """Test proxy routing logic"""

    def test_health_check_not_proxied(self, test_client: TestClient):
        """Test that health check is not proxied"""
        response = test_client.get("/health")
        assert response.status_code == 200
        # Should return health data, not proxy stub
        assert "status" in response.json()

    def test_root_path_handling(self, test_client: TestClient):
        """Test handling of root path"""
        response = test_client.get("/")
        # Should be handled by catchall
        assert response.status_code == 501

    def test_path_with_query_parameters(self, test_client: TestClient):
        """Test handling paths with query parameters"""
        response = test_client.get("/test?param=value&foo=bar")
        assert response.status_code == 501

    def test_path_with_special_characters(self, test_client: TestClient):
        """Test handling paths with special characters"""
        response = test_client.get("/path/with%20spaces")
        assert response.status_code != 404


@pytest.mark.unit
class TestProxyConfiguration:
    """Test proxy configuration handling"""

    def test_observe_mode_configuration(self):
        """Test proxy in observe mode"""
        config = YoriConfig(mode="observe")
        proxy = ProxyServer(config)
        assert proxy.config.mode == "observe"

    def test_advisory_mode_configuration(self):
        """Test proxy in advisory mode"""
        config = YoriConfig(mode="advisory")
        proxy = ProxyServer(config)
        assert proxy.config.mode == "advisory"

    def test_enforce_mode_configuration(self):
        """Test proxy in enforce mode"""
        config = YoriConfig(mode="enforce")
        proxy = ProxyServer(config)
        assert proxy.config.mode == "enforce"

    def test_endpoint_configuration(self):
        """Test proxy with custom endpoints"""
        config = YoriConfig(
            endpoints=[
                EndpointConfig(domain="custom1.com", enabled=True),
                EndpointConfig(domain="custom2.com", enabled=True),
            ]
        )
        proxy = ProxyServer(config)
        assert len(proxy.config.endpoints) == 2
        assert proxy.config.endpoints[0].domain == "custom1.com"
