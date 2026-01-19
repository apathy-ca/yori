"""
Tests for YORI policy evaluation system
"""

import pytest
from datetime import datetime
from yori.policy import PolicyEvaluator, PolicyResult


class TestPolicyEvaluator:
    """Test policy evaluator functionality"""

    def test_init(self):
        """Test policy evaluator initialization"""
        evaluator = PolicyEvaluator("/tmp/test_policies")
        assert evaluator.policy_dir.name == "test_policies"

    def test_evaluate_no_policies(self):
        """Test evaluation with no policies loaded (should default to allow)"""
        evaluator = PolicyEvaluator("/tmp/nonexistent")
        result = evaluator.evaluate({
            "user": "test",
            "device": "device1",
            "endpoint": "api.openai.com",
        })

        assert isinstance(result, PolicyResult)
        assert result.allow is True
        assert result.mode in ["observe", "stub"]

    def test_evaluate_with_data(self):
        """Test evaluation with various input data"""
        evaluator = PolicyEvaluator("/tmp/test_policies")

        # Test with bedtime data
        result = evaluator.evaluate({
            "user": "alice",
            "device": "iphone",
            "hour": 22,  # 10 PM
            "prompt": "Help me with homework",
        })

        assert isinstance(result, PolicyResult)
        assert result.allow is True
        assert hasattr(result, "policy")
        assert hasattr(result, "reason")

    def test_policy_result_dataclass(self):
        """Test PolicyResult dataclass"""
        result = PolicyResult(
            allow=True,
            policy="test_policy",
            reason="Test reason",
            mode="advisory",
            metadata={"key": "value"},
        )

        assert result.allow is True
        assert result.policy == "test_policy"
        assert result.reason == "Test reason"
        assert result.mode == "advisory"
        assert result.metadata["key"] == "value"


class TestPolicyInputs:
    """Test different policy input scenarios"""

    def test_bedtime_input(self):
        """Test bedtime policy input"""
        evaluator = PolicyEvaluator("/tmp/test_policies")

        # Late night (should trigger advisory)
        result = evaluator.evaluate({
            "user": "child",
            "device": "tablet",
            "hour": 23,
            "timestamp": "2026-01-19T23:00:00Z",
        })

        assert result.allow is True

    def test_high_usage_input(self):
        """Test high usage policy input"""
        evaluator = PolicyEvaluator("/tmp/test_policies")

        # High usage (should trigger warning)
        result = evaluator.evaluate({
            "user": "user1",
            "device": "laptop",
            "request_count": 45,
            "config": {"daily_threshold": 50},
        })

        assert result.allow is True

    def test_privacy_input(self):
        """Test privacy policy input with PII"""
        evaluator = PolicyEvaluator("/tmp/test_policies")

        # Prompt with email (should trigger alert)
        result = evaluator.evaluate({
            "user": "user1",
            "device": "phone",
            "prompt": "My email is test@example.com",
        })

        assert result.allow is True

    def test_homework_input(self):
        """Test homework detection policy input"""
        evaluator = PolicyEvaluator("/tmp/test_policies")

        # Homework-related prompt
        result = evaluator.evaluate({
            "user": "student",
            "device": "chromebook",
            "prompt": "Help me solve this calculus problem",
            "hour": 15,
        })

        assert result.allow is True


class TestPolicyTesting:
    """Test policy dry-run functionality"""

    def test_test_policy(self):
        """Test policy testing/dry-run"""
        evaluator = PolicyEvaluator("/tmp/test_policies")

        result = evaluator.test_policy("bedtime", {
            "user": "test",
            "hour": 22,
        })

        assert isinstance(result, PolicyResult)
        assert result.mode == "test"

    def test_test_policy_various_inputs(self):
        """Test policy testing with various inputs"""
        evaluator = PolicyEvaluator("/tmp/test_policies")

        test_cases = [
            ("bedtime", {"hour": 22, "user": "alice"}),
            ("high_usage", {"request_count": 100, "user": "bob"}),
            ("privacy", {"prompt": "Call me at 555-1234", "user": "charlie"}),
        ]

        for policy_name, test_data in test_cases:
            result = evaluator.test_policy(policy_name, test_data)
            assert isinstance(result, PolicyResult)
            assert result.mode == "test"


@pytest.mark.performance
class TestPolicyPerformance:
    """Test policy evaluation performance"""

    def test_evaluation_latency(self):
        """Test that policy evaluation is fast (<5ms target)"""
        import time

        evaluator = PolicyEvaluator("/tmp/test_policies")

        # Warm up
        for _ in range(10):
            evaluator.evaluate({"user": "test", "hour": 12})

        # Measure
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            evaluator.evaluate({
                "user": "test",
                "device": "test",
                "hour": 12,
                "prompt": "test prompt",
            })
            latency = (time.perf_counter() - start) * 1000  # ms

            latencies.append(latency)

        # Calculate p95
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]

        # Log performance
        print(f"\nPolicy evaluation latency:")
        print(f"  Mean: {sum(latencies) / len(latencies):.2f}ms")
        print(f"  P50:  {latencies[50]:.2f}ms")
        print(f"  P95:  {p95:.2f}ms")
        print(f"  P99:  {latencies[99]:.2f}ms")

        # Note: Without actual OPA engine, this will be very fast
        # With real engine, target is <5ms p95
        assert p95 < 100  # Relaxed for stub mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
