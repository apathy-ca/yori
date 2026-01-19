"""
Pytest configuration and shared fixtures for YORI tests

This module provides common fixtures used across all test types:
- Configuration fixtures
- Mock policy engines
- Mock caches
- Test data generators
- Database fixtures
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import pytest
import httpx
from fastapi.testclient import TestClient

# Import YORI components
from yori.config import YoriConfig, EndpointConfig, AuditConfig, PolicyConfig
from yori.proxy import ProxyServer


# ============================================================================
# Session-scoped fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests"""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def tmp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# Configuration fixtures
# ============================================================================

@pytest.fixture
def test_config(tmp_dir: Path) -> YoriConfig:
    """Create test configuration with temporary paths"""
    return YoriConfig(
        mode="observe",
        listen="127.0.0.1:8443",
        endpoints=[
            EndpointConfig(domain="api.openai.com", enabled=True),
            EndpointConfig(domain="api.anthropic.com", enabled=True),
        ],
        audit=AuditConfig(
            database=tmp_dir / "audit.db",
            retention_days=30,
        ),
        policies=PolicyConfig(
            directory=tmp_dir / "policies",
            default="test_default.rego",
        ),
    )


@pytest.fixture
def enforce_config(test_config: YoriConfig) -> YoriConfig:
    """Configuration with enforce mode enabled"""
    test_config.mode = "enforce"
    return test_config


@pytest.fixture
def advisory_config(test_config: YoriConfig) -> YoriConfig:
    """Configuration with advisory mode enabled"""
    test_config.mode = "advisory"
    return test_config


# ============================================================================
# Mock Rust components (for when Rust module isn't built)
# ============================================================================

@pytest.fixture
def mock_policy_engine():
    """Mock PolicyEngine for testing without Rust"""
    mock = MagicMock()
    mock.evaluate.return_value = {
        "allow": True,
        "policy": "test_policy",
        "reason": "Test allowed",
        "mode": "observe",
    }
    mock.load_policies.return_value = 1
    mock.list_policies.return_value = ["test_policy"]
    return mock


@pytest.fixture
def mock_deny_policy_engine():
    """Mock PolicyEngine that denies requests"""
    mock = MagicMock()
    mock.evaluate.return_value = {
        "allow": False,
        "policy": "test_policy",
        "reason": "Test denied - blocked keyword",
        "mode": "enforce",
    }
    return mock


@pytest.fixture
def mock_cache():
    """Mock Cache for testing without Rust"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.clear.return_value = 0
    mock.contains.return_value = False
    mock.stats.return_value = {
        "entries": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
    }
    return mock


# ============================================================================
# Proxy server fixtures
# ============================================================================

@pytest.fixture
def proxy_server(test_config: YoriConfig) -> ProxyServer:
    """Create ProxyServer instance with test configuration"""
    return ProxyServer(test_config)


@pytest.fixture
def test_client(proxy_server: ProxyServer) -> TestClient:
    """Create FastAPI test client"""
    return TestClient(proxy_server.app)


@pytest.fixture
async def async_client(proxy_server: ProxyServer) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for testing"""
    async with httpx.AsyncClient(
        app=proxy_server.app,
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# Test data fixtures
# ============================================================================

@pytest.fixture
def sample_llm_request():
    """Sample LLM API request for testing"""
    return {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the weather today?"},
        ],
        "temperature": 0.7,
        "max_tokens": 150,
    }


@pytest.fixture
def sample_policy_input():
    """Sample input for policy evaluation"""
    return {
        "user": "alice",
        "client_ip": "192.168.1.100",
        "endpoint": "api.openai.com",
        "method": "POST",
        "path": "/v1/chat/completions",
        "time": "2024-01-15T14:30:00Z",
        "prompt_preview": "What is the weather today?",
    }


@pytest.fixture
def sample_audit_record():
    """Sample audit log record"""
    return {
        "id": 1,
        "timestamp": "2024-01-15T14:30:00.123456",
        "client_ip": "192.168.1.100",
        "user": "alice",
        "endpoint": "api.openai.com",
        "method": "POST",
        "path": "/v1/chat/completions",
        "prompt_preview": "What is the weather today?",
        "policy_result": "allow",
        "policy_name": "home_default",
        "status_code": 200,
        "duration_ms": 1234,
        "tokens": 42,
    }


# ============================================================================
# Database fixtures
# ============================================================================

@pytest.fixture
async def audit_db(tmp_dir: Path):
    """Create temporary audit database for testing"""
    import aiosqlite

    db_path = tmp_dir / "test_audit.db"

    # Create database with schema
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                user TEXT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                prompt_preview TEXT,
                policy_result TEXT NOT NULL,
                policy_name TEXT,
                status_code INTEGER,
                duration_ms INTEGER,
                tokens INTEGER
            )
        """)
        await db.commit()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


# ============================================================================
# Policy file fixtures
# ============================================================================

@pytest.fixture
def sample_rego_policy(tmp_dir: Path) -> Path:
    """Create sample Rego policy file"""
    policy_dir = tmp_dir / "policies"
    policy_dir.mkdir(exist_ok=True)

    policy_file = policy_dir / "test_policy.rego"
    policy_file.write_text("""
package yori.test

default allow = false

allow {
    input.user == "alice"
    input.endpoint == "api.openai.com"
}

deny_reason = "User not authorized" {
    not allow
}
""")

    return policy_file


# ============================================================================
# Network mocking fixtures
# ============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock response from OpenAI API"""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "I don't have access to real-time weather data.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 15,
            "total_tokens": 35,
        },
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock response from Anthropic API"""
    return {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I don't have access to real-time weather information.",
            }
        ],
        "model": "claude-3-sonnet-20240229",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 18,
            "output_tokens": 12,
        },
    }


# ============================================================================
# Performance testing fixtures
# ============================================================================

@pytest.fixture
def performance_config():
    """Configuration for performance tests"""
    return {
        "latency_target_ms": 10,
        "throughput_target_rps": 50,
        "memory_target_mb": 256,
        "sqlite_query_target_ms": 100,
        "test_duration_seconds": 30,
    }


# ============================================================================
# Markers and skip conditions
# ============================================================================

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (deselect with '-m \"not unit\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )


# Check for optional dependencies
opnsense_available = os.environ.get("OPNSENSE_VM", None) is not None
llm_api_available = os.environ.get("TEST_LLM_API", None) is not None

# Skip markers
requires_opnsense = pytest.mark.skipif(
    not opnsense_available,
    reason="Requires OPNSENSE_VM environment variable",
)

requires_llm = pytest.mark.skipif(
    not llm_api_available,
    reason="Requires TEST_LLM_API environment variable",
)
