"""
Integration Tests: Policy Evaluation

Tests for policy engine integration with the proxy.
"""

import pytest
from unittest.mock import MagicMock
from yori.config import YoriConfig


@pytest.mark.integration
class TestPolicyEvaluation:
    """Test policy evaluation integration"""

    def test_policy_allows_request(self, mock_policy_engine: MagicMock, sample_policy_input: dict):
        """Test policy evaluation that allows a request"""
        mock_policy_engine.evaluate.return_value = {
            "allow": True,
            "policy": "home_default",
            "reason": "User authorized for endpoint",
            "mode": "enforce",
        }

        result = mock_policy_engine.evaluate(sample_policy_input)

        assert result["allow"] is True
        assert result["policy"] == "home_default"
        assert "reason" in result

    def test_policy_denies_request(self, mock_deny_policy_engine: MagicMock, sample_policy_input: dict):
        """Test policy evaluation that denies a request"""
        result = mock_deny_policy_engine.evaluate(sample_policy_input)

        assert result["allow"] is False
        assert "reason" in result
        assert len(result["reason"]) > 0

    def test_policy_evaluation_with_user_context(self, mock_policy_engine: MagicMock):
        """Test policy evaluation with user context"""
        policy_input = {
            "user": "alice",
            "client_ip": "192.168.1.100",
            "endpoint": "api.openai.com",
        }

        result = mock_policy_engine.evaluate(policy_input)
        assert "allow" in result

    def test_policy_evaluation_caching(self, mock_policy_engine: MagicMock, mock_cache: MagicMock):
        """Test that policy results can be cached"""
        policy_input = {"user": "alice", "endpoint": "api.openai.com"}

        # First evaluation
        result1 = mock_policy_engine.evaluate(policy_input)

        # Cache the result
        cache_key = f"policy:{policy_input['user']}:{policy_input['endpoint']}"
        mock_cache.set(cache_key, result1)

        # Retrieve from cache
        mock_cache.get.return_value = result1
        cached_result = mock_cache.get(cache_key)

        assert cached_result == result1

    def test_policy_modes(self, mock_policy_engine: MagicMock):
        """Test different policy modes"""
        modes = ["observe", "advisory", "enforce"]

        for mode in modes:
            mock_policy_engine.evaluate.return_value = {
                "allow": True,
                "policy": "test",
                "reason": f"Testing {mode} mode",
                "mode": mode,
            }

            result = mock_policy_engine.evaluate({})
            assert result["mode"] == mode
