"""Tests for policy evaluation"""

import pytest
from yori.policy import PolicyEvaluator
from yori.config import YoriConfig
from yori.models import PolicyDecision, LLMProvider


@pytest.fixture
def policy_evaluator():
    """Create a policy evaluator for testing"""
    config = YoriConfig()
    return PolicyEvaluator(config)


@pytest.mark.asyncio
async def test_evaluate_allow(policy_evaluator):
    """Test policy evaluation for allowed request"""
    result = await policy_evaluator.evaluate(
        source_ip="192.168.1.100",
        host="api.openai.com",
        path="/v1/chat/completions",
        method="POST",
        body=b'{"model": "gpt-4", "messages": []}',
        provider=LLMProvider.OPENAI,
    )

    assert result.decision == PolicyDecision.ALLOW
    assert result.policy_name is not None


@pytest.mark.asyncio
async def test_evaluate_block_test_ip(policy_evaluator):
    """Test policy evaluation blocks test IP"""
    result = await policy_evaluator.evaluate(
        source_ip="192.168.1.666",
        host="api.openai.com",
        path="/v1/chat/completions",
        method="POST",
        body=b"{}",
        provider=LLMProvider.OPENAI,
    )

    assert result.decision == PolicyDecision.BLOCK
    assert "test ip" in result.reason.lower()


@pytest.mark.asyncio
async def test_evaluate_alert_unknown_provider(policy_evaluator):
    """Test policy evaluation alerts on unknown provider"""
    result = await policy_evaluator.evaluate(
        source_ip="192.168.1.100",
        host="unknown.ai",
        path="/v1/chat",
        method="POST",
        body=b"{}",
        provider=LLMProvider.UNKNOWN,
    )

    assert result.decision == PolicyDecision.ALERT
    assert "unknown" in result.reason.lower()


@pytest.mark.asyncio
async def test_evaluate_sensitive_content(policy_evaluator):
    """Test policy evaluation alerts on sensitive content"""
    result = await policy_evaluator.evaluate(
        source_ip="192.168.1.100",
        host="api.openai.com",
        path="/v1/chat/completions",
        method="POST",
        body=b'{"content": "My password is secret123"}',
        provider=LLMProvider.OPENAI,
    )

    # Should alert on sensitive keywords
    assert result.decision == PolicyDecision.ALERT
    assert "sensitive" in result.reason.lower()
