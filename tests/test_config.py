"""Tests for configuration loading"""

import pytest
from pathlib import Path
import tempfile
import yaml

from yori.config import YoriConfig, EndpointConfig


def test_default_config():
    """Test default configuration values"""
    config = YoriConfig()
    assert config.mode == "observe"
    assert config.listen == "0.0.0.0:8443"
    assert len(config.endpoints) == 4
    assert config.audit.retention_days == 365


def test_config_from_yaml():
    """Test loading configuration from YAML file"""
    config_data = {
        "mode": "enforce",
        "listen": "127.0.0.1:9443",
        "endpoints": [
            {"domain": "api.openai.com", "enabled": True},
            {"domain": "api.anthropic.com", "enabled": False},
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = YoriConfig.from_yaml(config_path)
        assert config.mode == "enforce"
        assert config.listen == "127.0.0.1:9443"
        assert len(config.endpoints) == 2
        assert config.endpoints[1].enabled is False
    finally:
        config_path.unlink()


def test_endpoint_config():
    """Test endpoint configuration"""
    endpoint = EndpointConfig(domain="api.openai.com", enabled=True)
    assert endpoint.domain == "api.openai.com"
    assert endpoint.enabled is True

    endpoint2 = EndpointConfig(domain="api.anthropic.com")
    assert endpoint2.enabled is True  # Default value
