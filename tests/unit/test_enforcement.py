"""
Unit tests for enforcement mode logic

Tests the enforcement decision engine and policy action handling.
"""

import pytest
from datetime import datetime

from yori.enforcement import (
    EnforcementEngine,
    EnforcementDecision,
    EnforcementEngineDecision,
    PolicyResult,
    should_enforce_policy,
)
from yori.config import YoriConfig, EnforcementConfig, PolicyConfig, PolicyFileConfig


class TestEnforcementEngine:
    """Test EnforcementEngine class"""

    def test_enforcement_disabled_by_default(self):
        """Test that enforcement is disabled by default"""
        config = YoriConfig()
        engine = EnforcementEngine(config)

        assert not engine._is_enforcement_enabled()

    def test_enforcement_requires_mode_enforce(self):
        """Test that enforcement requires mode='enforce'"""
        config = YoriConfig(
            mode="observe",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )
        engine = EnforcementEngine(config)

        assert not engine._is_enforcement_enabled()

    def test_enforcement_requires_enabled_flag(self):
        """Test that enforcement requires enforcement.enabled=true"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=False, consent_accepted=True),
        )
        engine = EnforcementEngine(config)

        assert not engine._is_enforcement_enabled()

    def test_enforcement_requires_consent(self):
        """Test that enforcement requires consent_accepted=true"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=False),
        )
        engine = EnforcementEngine(config)

        assert not engine._is_enforcement_enabled()

    def test_enforcement_enabled_when_all_requirements_met(self):
        """Test that enforcement is enabled when all requirements are met"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )
        engine = EnforcementEngine(config)

        assert engine._is_enforcement_enabled()

    def test_never_block_when_enforcement_disabled(self):
        """Test that requests are never blocked when enforcement is disabled"""
        config = YoriConfig(mode="observe")
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="block", reason="Test policy", policy_name="test.rego"
        )

        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )

        assert not decision.should_block
        assert decision.action_taken == "alert"

    def test_block_when_policy_action_is_block(self):
        """Test that requests are blocked when policy action is 'block'"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test": PolicyFileConfig(enabled=True, action="block"),
                }
            ),
        )
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="alert", reason="Test policy", policy_name="test.rego"
        )

        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )

        assert decision.should_block
        assert decision.action_taken == "block"
        assert decision.policy_name == "test.rego"

    def test_alert_when_policy_action_is_alert(self):
        """Test that requests are not blocked when policy action is 'alert'"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test": PolicyFileConfig(enabled=True, action="alert"),
                }
            ),
        )
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="block", reason="Test policy", policy_name="test.rego"
        )

        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )

        assert not decision.should_block
        assert decision.action_taken == "alert"

    def test_allow_when_policy_action_is_allow(self):
        """Test that requests are allowed when policy action is 'allow'"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test": PolicyFileConfig(enabled=True, action="allow"),
                }
            ),
        )
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="block", reason="Test policy", policy_name="test.rego"
        )

        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )

        assert not decision.should_block
        assert decision.action_taken == "allow"

    def test_default_to_alert_for_unconfigured_policy(self):
        """Test that unconfigured policies default to 'alert'"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="block", reason="Test policy", policy_name="unknown.rego"
        )

        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )

        assert not decision.should_block
        assert decision.action_taken == "alert"

    def test_disabled_policy_acts_as_allow(self):
        """Test that disabled policies act as 'allow'"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test": PolicyFileConfig(enabled=False, action="block"),
                }
            ),
        )
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="block", reason="Test policy", policy_name="test.rego"
        )

        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )

        assert not decision.should_block
        assert decision.action_taken == "allow"

    def test_enforcement_decision_includes_timestamp(self):
        """Test that enforcement decisions include a timestamp"""
        config = YoriConfig()
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="alert", reason="Test", policy_name="test.rego"
        )

        before = datetime.now()
        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )
        after = datetime.now()

        assert before <= decision.timestamp <= after

    def test_enforcement_decision_includes_allow_override(self):
        """Test that enforcement decisions include allow_override flag"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test": PolicyFileConfig(enabled=True, action="block"),
                }
            ),
        )
        engine = EnforcementEngine(config)

        policy_result = PolicyResult(
            action="block", reason="Test", policy_name="test.rego"
        )

        decision = engine.should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
        )

        assert decision.allow_override  # Future: allowlist integration


class TestConvenienceFunction:
    """Test the should_enforce_policy convenience function"""

    def test_should_enforce_policy_function(self):
        """Test that the convenience function works"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
            policies=PolicyConfig(
                files={
                    "test": PolicyFileConfig(enabled=True, action="block"),
                }
            ),
        )

        policy_result = PolicyResult(
            action="block", reason="Test", policy_name="test.rego"
        )

        decision = should_enforce_policy(
            request={"method": "POST"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
            config=config,
        )

        assert decision.should_block


class TestPolicyResultDataclass:
    """Test PolicyResult dataclass"""

    def test_policy_result_creation(self):
        """Test creating a PolicyResult"""
        result = PolicyResult(
            action="block", reason="Test reason", policy_name="test.rego"
        )

        assert result.action == "block"
        assert result.reason == "Test reason"
        assert result.policy_name == "test.rego"
        assert result.metadata is None

    def test_policy_result_with_metadata(self):
        """Test PolicyResult with metadata"""
        metadata = {"user": "alice", "timestamp": "2026-01-20T12:00:00"}
        result = PolicyResult(
            action="alert",
            reason="Test",
            policy_name="test.rego",
            metadata=metadata,
        )

        assert result.metadata == metadata


class TestEnforcementDecisionDataclass:
    """Test EnforcementDecision dataclass"""

    def test_enforcement_decision_creation(self):
        """Test creating an EnforcementEngineDecision"""
        timestamp = datetime.now()
        decision = EnforcementEngineDecision(
            should_block=True,
            policy_name="test.rego",
            reason="Test reason",
            timestamp=timestamp,
            allow_override=True,
            action_taken="block",
        )

        assert decision.should_block
        assert decision.policy_name == "test.rego"
        assert decision.reason == "Test reason"
        assert decision.timestamp == timestamp
        assert decision.allow_override
        assert decision.action_taken == "block"
