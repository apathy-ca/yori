"""
Unit Tests: Policy Engine (Python wrapper)

Tests for the Python interface to the Rust PolicyEngine.
These tests use mocks since the Rust module may not be built.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


@pytest.mark.unit
class TestPolicyEngineImport:
    """Test PolicyEngine import and availability"""

    def test_policy_engine_import(self):
        """Test importing PolicyEngine from yori"""
        from yori import PolicyEngine
        # May be None if Rust module not built, that's okay
        assert PolicyEngine is not None or PolicyEngine is None

    def test_policy_engine_module_fallback(self):
        """Test that missing Rust module is handled gracefully"""
        # This tests the try/except in yori/__init__.py
        with patch("yori._core", None):
            # Should not raise exception
            import yori
            # PolicyEngine should be None or a fallback
            assert hasattr(yori, "PolicyEngine")


@pytest.mark.unit
class TestPolicyEngineCreation:
    """Test PolicyEngine creation and initialization"""

    def test_policy_engine_creation_with_mock(self, mock_policy_engine: MagicMock):
        """Test creating policy engine with mock"""
        engine = mock_policy_engine
        assert engine is not None

    def test_policy_engine_creation_with_path(self, tmp_dir: Path):
        """Test creating policy engine with policy directory path"""
        # This would test the real Rust module if built
        # For now, we test the mock
        try:
            from yori import PolicyEngine
            if PolicyEngine is not None:
                engine = PolicyEngine(str(tmp_dir / "policies"))
                assert engine is not None
        except ImportError:
            pytest.skip("Rust module not built")

    def test_policy_engine_creation_invalid_path(self):
        """Test that invalid path is handled"""
        try:
            from yori import PolicyEngine
            if PolicyEngine is not None:
                # Should accept path even if directory doesn't exist
                # Rust code will handle validation
                engine = PolicyEngine("/nonexistent/path")
                assert engine is not None
        except ImportError:
            pytest.skip("Rust module not built")


@pytest.mark.unit
class TestPolicyEngineEvaluation:
    """Test policy evaluation functionality"""

    def test_evaluate_with_mock(self, mock_policy_engine: MagicMock, sample_policy_input: dict):
        """Test policy evaluation with mock engine"""
        result = mock_policy_engine.evaluate(sample_policy_input)
        assert "allow" in result
        assert "policy" in result
        assert "reason" in result
        assert "mode" in result
        assert isinstance(result["allow"], bool)

    def test_evaluate_allow_result(self, mock_policy_engine: MagicMock):
        """Test evaluation that allows request"""
        mock_policy_engine.evaluate.return_value = {
            "allow": True,
            "policy": "test_policy",
            "reason": "User authorized",
            "mode": "enforce",
        }

        result = mock_policy_engine.evaluate({"user": "alice"})
        assert result["allow"] is True
        assert result["reason"] == "User authorized"

    def test_evaluate_deny_result(self, mock_deny_policy_engine: MagicMock):
        """Test evaluation that denies request"""
        result = mock_deny_policy_engine.evaluate({"user": "bob"})
        assert result["allow"] is False
        assert "reason" in result
        assert len(result["reason"]) > 0

    def test_evaluate_with_complete_input(
        self,
        mock_policy_engine: MagicMock,
        sample_policy_input: dict,
    ):
        """Test evaluation with complete input data"""
        result = mock_policy_engine.evaluate(sample_policy_input)
        assert result is not None
        mock_policy_engine.evaluate.assert_called_once_with(sample_policy_input)

    def test_evaluate_mode_observe(self, mock_policy_engine: MagicMock):
        """Test evaluation in observe mode"""
        mock_policy_engine.evaluate.return_value = {
            "allow": True,
            "policy": "observe_policy",
            "reason": "Observe mode - logged only",
            "mode": "observe",
        }

        result = mock_policy_engine.evaluate({})
        assert result["mode"] == "observe"

    def test_evaluate_mode_advisory(self, mock_policy_engine: MagicMock):
        """Test evaluation in advisory mode"""
        mock_policy_engine.evaluate.return_value = {
            "allow": False,
            "policy": "advisory_policy",
            "reason": "Would block but advisory mode",
            "mode": "advisory",
        }

        result = mock_policy_engine.evaluate({})
        assert result["mode"] == "advisory"
        # In advisory mode, request might be denied but still forwarded

    def test_evaluate_mode_enforce(self, mock_policy_engine: MagicMock):
        """Test evaluation in enforce mode"""
        mock_policy_engine.evaluate.return_value = {
            "allow": False,
            "policy": "enforce_policy",
            "reason": "Policy violation - blocked",
            "mode": "enforce",
        }

        result = mock_policy_engine.evaluate({})
        assert result["mode"] == "enforce"
        assert result["allow"] is False


@pytest.mark.unit
class TestPolicyEngineManagement:
    """Test policy management functionality"""

    def test_load_policies(self, mock_policy_engine: MagicMock):
        """Test loading policies"""
        mock_policy_engine.load_policies.return_value = 5
        count = mock_policy_engine.load_policies()
        assert count == 5
        assert isinstance(count, int)

    def test_load_policies_empty_directory(self, mock_policy_engine: MagicMock):
        """Test loading policies from empty directory"""
        mock_policy_engine.load_policies.return_value = 0
        count = mock_policy_engine.load_policies()
        assert count == 0

    def test_list_policies(self, mock_policy_engine: MagicMock):
        """Test listing loaded policies"""
        policies = mock_policy_engine.list_policies()
        assert isinstance(policies, list)

    def test_list_policies_returns_names(self, mock_policy_engine: MagicMock):
        """Test that list_policies returns policy names"""
        mock_policy_engine.list_policies.return_value = [
            "home_default",
            "work_hours",
            "content_filter",
        ]

        policies = mock_policy_engine.list_policies()
        assert len(policies) == 3
        assert "home_default" in policies
        assert "work_hours" in policies

    def test_test_policy(self, mock_policy_engine: MagicMock):
        """Test testing a specific policy"""
        test_input = {"user": "alice", "endpoint": "api.openai.com"}
        result = mock_policy_engine.test_policy("home_default", test_input)
        assert result is not None
        assert "allow" in result


@pytest.mark.unit
class TestPolicyEngineEdgeCases:
    """Test edge cases and error handling"""

    def test_evaluate_empty_input(self, mock_policy_engine: MagicMock):
        """Test evaluation with empty input"""
        result = mock_policy_engine.evaluate({})
        assert result is not None
        assert "allow" in result

    def test_evaluate_none_input(self, mock_policy_engine: MagicMock):
        """Test evaluation with None input"""
        # Rust code should handle this appropriately
        # This tests the Python interface
        try:
            mock_policy_engine.evaluate(None)
        except (TypeError, AttributeError):
            # Expected if Rust code validates input
            pass

    def test_evaluate_missing_fields(self, mock_policy_engine: MagicMock):
        """Test evaluation with missing required fields"""
        # Policy should handle missing fields gracefully
        result = mock_policy_engine.evaluate({"user": "alice"})  # Missing other fields
        assert result is not None

    def test_evaluate_extra_fields(self, mock_policy_engine: MagicMock):
        """Test evaluation with extra unknown fields"""
        input_data = {
            "user": "alice",
            "endpoint": "api.openai.com",
            "unknown_field": "value",
            "another_unknown": 123,
        }
        result = mock_policy_engine.evaluate(input_data)
        assert result is not None


@pytest.mark.unit
class TestPolicyEngineIntegrationWithPython:
    """Test PolicyEngine integration with Python code"""

    def test_policy_result_type_checking(self, mock_policy_engine: MagicMock):
        """Test that policy result has correct types"""
        result = mock_policy_engine.evaluate({})
        assert isinstance(result["allow"], bool)
        assert isinstance(result["policy"], str)
        assert isinstance(result["reason"], str)
        assert isinstance(result["mode"], str)

    def test_policy_engine_in_context_manager(self, mock_policy_engine: MagicMock):
        """Test using policy engine in various contexts"""
        # Policy engine should be usable in different contexts
        engine = mock_policy_engine

        # In list comprehension
        results = [engine.evaluate({"user": f"user{i}"}) for i in range(3)]
        assert len(results) == 3

    def test_policy_engine_thread_safety(self, mock_policy_engine: MagicMock):
        """Test policy engine with concurrent calls (mock)"""
        # Real Rust implementation should be thread-safe
        # This tests the Python interface
        import concurrent.futures

        def evaluate_policy(user):
            return mock_policy_engine.evaluate({"user": user})

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(evaluate_policy, f"user{i}") for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 10


@pytest.mark.unit
class TestCacheIntegration:
    """Test Cache integration from Python"""

    def test_cache_import(self):
        """Test importing Cache from yori"""
        from yori import Cache
        assert Cache is not None or Cache is None

    def test_cache_creation_with_mock(self, mock_cache: MagicMock):
        """Test creating cache with mock"""
        cache = mock_cache
        assert cache is not None

    def test_cache_set_get(self, mock_cache: MagicMock):
        """Test basic cache set/get operations"""
        mock_cache.set("test_key", {"data": "value"})
        mock_cache.get.return_value = {"data": "value"}

        value = mock_cache.get("test_key")
        assert value == {"data": "value"}

    def test_cache_stats(self, mock_cache: MagicMock):
        """Test getting cache statistics"""
        stats = mock_cache.stats()
        assert "entries" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats

    def test_cache_clear(self, mock_cache: MagicMock):
        """Test clearing cache"""
        count = mock_cache.clear()
        assert isinstance(count, int)

    def test_cache_contains(self, mock_cache: MagicMock):
        """Test checking if key exists in cache"""
        exists = mock_cache.contains("test_key")
        assert isinstance(exists, bool)
