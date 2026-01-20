"""
Pytest fixtures for YORI test suite
Provides common fixtures for async testing
"""
import pytest
import sys
import tempfile
import os
from pathlib import Path

# Add python directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

from yori.config import YoriConfig, EndpointConfig, AuditConfig, PolicyConfig
from yori.models import LLMProvider


@pytest.fixture
def temp_db():
    """Create temporary database file"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield Path(path)
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def test_config(temp_db):
    """Create test configuration"""
    return YoriConfig(
        mode="observe",
        listen="127.0.0.1:8443",
        endpoints=[
            EndpointConfig(domain="api.openai.com", enabled=True),
            EndpointConfig(domain="api.anthropic.com", enabled=True),
            EndpointConfig(domain="generativelanguage.googleapis.com", enabled=True),
            EndpointConfig(domain="api.mistral.ai", enabled=True),
        ],
        audit=AuditConfig(database=temp_db, retention_days=365),
        policies=PolicyConfig(directory=Path("/tmp/policies"), default="default.rego"),
    )


@pytest.fixture
def observe_config(test_config):
    """Config in observe mode"""
    test_config.mode = "observe"
    return test_config


@pytest.fixture
def advisory_config(test_config):
    """Config in advisory mode"""
    test_config.mode = "advisory"
    return test_config


@pytest.fixture
def enforce_config(test_config):
    """Config in enforce mode"""
    test_config.mode = "enforce"
    return test_config
