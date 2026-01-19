"""Tests for proxy server"""

import pytest
from fastapi.testclient import TestClient

from yori.config import YoriConfig
from yori.proxy import ProxyServer


@pytest.fixture
def proxy_server():
    """Create a proxy server for testing"""
    config = YoriConfig()
    return ProxyServer(config)


@pytest.fixture
def client(proxy_server):
    """Create a test client"""
    return TestClient(proxy_server.app)


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mode"] == "observe"
    assert data["endpoints"] == 4


def test_health_check_structure(client):
    """Test health check response structure"""
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "mode" in data
    assert "endpoints" in data


def test_proxy_endpoint_exists(client):
    """Test that proxy routes exist and handle requests"""
    # Make a proxy request (will fail without backend but should not return 404)
    response = client.post("/v1/chat/completions")
    # Should get 403 (disabled endpoint) or 502 (backend error), not 404 or 501
    assert response.status_code in [403, 502]
    data = response.json()
    assert "error" in data
