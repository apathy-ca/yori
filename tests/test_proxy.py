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


def test_proxy_not_implemented(client):
    """Test that proxy routes return not implemented"""
    # This will be replaced with actual proxy logic later
    response = client.post("/v1/chat/completions")
    assert response.status_code == 501
    data = response.json()
    assert "error" in data
