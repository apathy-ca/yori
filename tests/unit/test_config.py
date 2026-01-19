"""
Unit Tests: Configuration Management

Tests for YORI configuration loading, validation, and management.
"""

import pytest
from pathlib import Path
import yaml
import tempfile

from yori.config import (
    YoriConfig,
    EndpointConfig,
    AuditConfig,
    PolicyConfig,
)


@pytest.mark.unit
class TestEndpointConfig:
    """Test endpoint configuration"""

    def test_endpoint_config_creation(self):
        """Test creating endpoint configuration"""
        config = EndpointConfig(domain="api.openai.com", enabled=True)
        assert config.domain == "api.openai.com"
        assert config.enabled is True

    def test_endpoint_config_disabled(self):
        """Test creating disabled endpoint"""
        config = EndpointConfig(domain="api.anthropic.com", enabled=False)
        assert config.domain == "api.anthropic.com"
        assert config.enabled is False

    def test_endpoint_config_default_enabled(self):
        """Test that endpoints are enabled by default"""
        config = EndpointConfig(domain="test.com")
        assert config.enabled is True


@pytest.mark.unit
class TestAuditConfig:
    """Test audit configuration"""

    def test_audit_config_defaults(self):
        """Test audit configuration with defaults"""
        config = AuditConfig()
        assert config.database == Path("/var/db/yori/audit.db")
        assert config.retention_days == 365

    def test_audit_config_custom_path(self, tmp_dir: Path):
        """Test audit configuration with custom database path"""
        db_path = tmp_dir / "custom_audit.db"
        config = AuditConfig(database=db_path)
        assert config.database == db_path

    def test_audit_config_custom_retention(self):
        """Test audit configuration with custom retention"""
        config = AuditConfig(retention_days=90)
        assert config.retention_days == 90


@pytest.mark.unit
class TestPolicyConfig:
    """Test policy configuration"""

    def test_policy_config_defaults(self):
        """Test policy configuration with defaults"""
        config = PolicyConfig()
        assert config.directory == Path("/usr/local/etc/yori/policies")
        assert config.default == "home_default.rego"

    def test_policy_config_custom_directory(self, tmp_dir: Path):
        """Test policy configuration with custom directory"""
        policy_dir = tmp_dir / "policies"
        config = PolicyConfig(directory=policy_dir)
        assert config.directory == policy_dir

    def test_policy_config_custom_default(self):
        """Test policy configuration with custom default policy"""
        config = PolicyConfig(default="custom.rego")
        assert config.default == "custom.rego"


@pytest.mark.unit
class TestYoriConfig:
    """Test main YORI configuration"""

    def test_config_defaults(self):
        """Test configuration with all defaults"""
        config = YoriConfig()
        assert config.mode == "observe"
        assert config.listen == "0.0.0.0:8443"
        assert len(config.endpoints) == 4
        assert config.audit.retention_days == 365
        assert config.policies.default == "home_default.rego"

    def test_config_observe_mode(self):
        """Test observe mode configuration"""
        config = YoriConfig(mode="observe")
        assert config.mode == "observe"

    def test_config_advisory_mode(self):
        """Test advisory mode configuration"""
        config = YoriConfig(mode="advisory")
        assert config.mode == "advisory"

    def test_config_enforce_mode(self):
        """Test enforce mode configuration"""
        config = YoriConfig(mode="enforce")
        assert config.mode == "enforce"

    def test_config_custom_listen_address(self):
        """Test custom listen address"""
        config = YoriConfig(listen="127.0.0.1:9000")
        assert config.listen == "127.0.0.1:9000"

    def test_config_custom_endpoints(self):
        """Test custom endpoint configuration"""
        endpoints = [
            EndpointConfig(domain="api.openai.com", enabled=True),
            EndpointConfig(domain="custom.ai", enabled=True),
        ]
        config = YoriConfig(endpoints=endpoints)
        assert len(config.endpoints) == 2
        assert config.endpoints[1].domain == "custom.ai"

    def test_config_default_endpoints(self):
        """Test that default endpoints include major LLM providers"""
        config = YoriConfig()
        domains = [ep.domain for ep in config.endpoints]
        assert "api.openai.com" in domains
        assert "api.anthropic.com" in domains
        assert "gemini.google.com" in domains
        assert "api.mistral.ai" in domains

    def test_config_from_yaml(self, tmp_dir: Path):
        """Test loading configuration from YAML file"""
        config_file = tmp_dir / "yori.conf"
        config_data = {
            "mode": "enforce",
            "listen": "192.168.1.1:8443",
            "endpoints": [
                {"domain": "api.openai.com", "enabled": True},
            ],
            "audit": {
                "database": str(tmp_dir / "audit.db"),
                "retention_days": 90,
            },
            "policies": {
                "directory": str(tmp_dir / "policies"),
                "default": "test.rego",
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = YoriConfig.from_yaml(config_file)
        assert config.mode == "enforce"
        assert config.listen == "192.168.1.1:8443"
        assert len(config.endpoints) == 1
        assert config.audit.retention_days == 90
        assert config.policies.default == "test.rego"

    def test_config_from_yaml_file_not_found(self, tmp_dir: Path):
        """Test loading configuration from non-existent file"""
        config_file = tmp_dir / "nonexistent.conf"
        with pytest.raises(FileNotFoundError):
            YoriConfig.from_yaml(config_file)

    def test_config_from_yaml_invalid_yaml(self, tmp_dir: Path):
        """Test loading configuration from invalid YAML"""
        config_file = tmp_dir / "invalid.conf"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            YoriConfig.from_yaml(config_file)

    def test_config_from_default_locations_no_config(self, tmp_dir: Path, monkeypatch):
        """Test loading from default locations when no config exists"""
        # Change to temp directory where no config exists
        monkeypatch.chdir(tmp_dir)
        config = YoriConfig.from_default_locations()
        # Should return default configuration
        assert config.mode == "observe"

    def test_config_from_default_locations_local_config(self, tmp_dir: Path, monkeypatch):
        """Test loading from local yori.conf"""
        monkeypatch.chdir(tmp_dir)

        # Create local config
        config_file = tmp_dir / "yori.conf"
        config_data = {"mode": "advisory"}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = YoriConfig.from_default_locations()
        assert config.mode == "advisory"

    def test_config_validation_invalid_mode(self):
        """Test that invalid mode raises validation error"""
        with pytest.raises(Exception):  # Pydantic validation error
            YoriConfig(mode="invalid_mode")

    def test_config_serialization(self):
        """Test configuration can be serialized"""
        config = YoriConfig(mode="enforce")
        data = config.model_dump()
        assert data["mode"] == "enforce"
        assert "listen" in data
        assert "endpoints" in data

    def test_config_nested_structure(self):
        """Test accessing nested configuration"""
        config = YoriConfig()
        assert isinstance(config.audit, AuditConfig)
        assert isinstance(config.policies, PolicyConfig)
        assert isinstance(config.endpoints[0], EndpointConfig)

    def test_config_endpoint_filter_enabled(self):
        """Test filtering enabled endpoints"""
        config = YoriConfig(
            endpoints=[
                EndpointConfig(domain="enabled1.com", enabled=True),
                EndpointConfig(domain="disabled.com", enabled=False),
                EndpointConfig(domain="enabled2.com", enabled=True),
            ]
        )
        enabled = [ep for ep in config.endpoints if ep.enabled]
        assert len(enabled) == 2
        assert all(ep.enabled for ep in enabled)

    def test_config_immutability(self):
        """Test that configuration can be modified after creation"""
        config = YoriConfig(mode="observe")
        # Pydantic models are mutable by default
        config.mode = "enforce"
        assert config.mode == "enforce"

    def test_config_yaml_round_trip(self, tmp_dir: Path):
        """Test saving and loading configuration preserves data"""
        original = YoriConfig(
            mode="advisory",
            listen="10.0.0.1:9443",
        )

        # Save to YAML
        config_file = tmp_dir / "roundtrip.conf"
        with open(config_file, "w") as f:
            yaml.dump(original.model_dump(), f)

        # Load back
        loaded = YoriConfig.from_yaml(config_file)
        assert loaded.mode == original.mode
        assert loaded.listen == original.listen
