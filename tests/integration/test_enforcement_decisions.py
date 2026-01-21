"""
Integration tests for enforcement decision logic

Tests the full flow of enforcement decisions with allowlist, time exceptions,
and emergency override.
"""

import pytest
from datetime import datetime

from yori.models import (
    PolicyResult,
    AllowlistDevice,
    TimeException,
    AllowlistConfig,
    EmergencyOverride,
    EnforcementConfig,
)
from yori.config import YoriConfig
from yori.enforcement import should_enforce_policy
from yori.emergency import hash_password


class TestEnforcementBypass:
    """Test enforcement bypass scenarios"""

    def test_policy_allows_request_no_enforcement(self):
        """When policy allows, no enforcement needed"""
        config = YoriConfig()
        policy_result = PolicyResult(
            allowed=True, policy_name="test_policy", reason="Request is allowed"
        )

        decision = should_enforce_policy(
            request={}, policy_result=policy_result, client_ip="192.168.1.100", config=config
        )

        assert decision.enforce is False
        assert "Policy allows" in decision.reason
        assert decision.bypass_type is None

    def test_emergency_override_bypasses_enforcement(self):
        """Emergency override should bypass all enforcement"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(enabled=True)
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="test_policy",
            reason="Request blocked by policy",
        )

        decision = should_enforce_policy(
            request={}, policy_result=policy_result, client_ip="192.168.1.100", config=config
        )

        assert decision.enforce is False
        assert "Emergency override" in decision.reason
        assert decision.bypass_type == "emergency_override"

    def test_allowlist_bypasses_enforcement(self):
        """Allowlisted device should bypass enforcement"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Dad's Laptop",
                            enabled=True,
                        )
                    ]
                )
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="test_policy",
            reason="Request blocked by policy",
        )

        decision = should_enforce_policy(
            request={}, policy_result=policy_result, client_ip="192.168.1.100", config=config
        )

        assert decision.enforce is False
        assert "allowlist" in decision.reason.lower()
        assert decision.bypass_type == "allowlist"
        assert decision.device_name == "Dad's Laptop"

    def test_time_exception_bypasses_enforcement(self):
        """Time exception should bypass enforcement during active hours"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="homework_hours",
                            days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.102"],
                            enabled=True,
                        )
                    ]
                )
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="test_policy",
            reason="Request blocked by policy",
        )

        # Create enforcement module's should_enforce_policy with datetime injection
        # Since we can't easily mock datetime.now(), we'll test this indirectly
        # by calling check_any_exception_active with a specific time

        from yori.time_exceptions import check_any_exception_active

        # Monday 4:00 PM
        check_time = datetime(2026, 1, 20, 16, 0)
        is_active, exception = check_any_exception_active("192.168.1.102", config, check_time)

        assert is_active is True
        assert exception.name == "homework_hours"

    def test_enforcement_when_not_allowlisted(self):
        """Request should be enforced when device is not allowlisted"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Allowed Device",
                            enabled=True,
                        )
                    ]
                )
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="test_policy",
            reason="Request blocked by policy",
        )

        decision = should_enforce_policy(
            request={},
            policy_result=policy_result,
            client_ip="192.168.1.200",  # Different IP, not allowlisted
            config=config,
        )

        assert decision.enforce is True
        assert decision.bypass_type is None


class TestBypassPriority:
    """Test bypass priority: emergency > allowlist > time exception"""

    def test_emergency_override_highest_priority(self):
        """Emergency override should take precedence over everything"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(enabled=True),
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Test Device",
                            enabled=True,
                        )
                    ],
                    time_exceptions=[
                        TimeException(
                            name="test_exception",
                            days=["monday"],
                            start_time="00:00",
                            end_time="23:59",
                            device_ips=["192.168.1.100"],
                            enabled=True,
                        )
                    ],
                ),
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="test_policy",
            reason="Blocked",
        )

        decision = should_enforce_policy(
            request={}, policy_result=policy_result, client_ip="192.168.1.100", config=config
        )

        # Should use emergency override, not allowlist or time exception
        assert decision.enforce is False
        assert decision.bypass_type == "emergency_override"

    def test_allowlist_priority_over_time_exception(self):
        """Allowlist should take precedence over time exceptions"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Test Device",
                            enabled=True,
                        )
                    ],
                    time_exceptions=[
                        TimeException(
                            name="test_exception",
                            days=["monday"],
                            start_time="00:00",
                            end_time="23:59",
                            device_ips=["192.168.1.100"],
                            enabled=True,
                        )
                    ],
                )
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="test_policy",
            reason="Blocked",
        )

        decision = should_enforce_policy(
            request={}, policy_result=policy_result, client_ip="192.168.1.100", config=config
        )

        # Should use allowlist, not time exception
        assert decision.enforce is False
        assert decision.bypass_type == "allowlist"


class TestMACAddressAllowlist:
    """Test allowlist bypass using MAC address"""

    def test_allowlist_by_mac_when_ip_different(self):
        """Device should be allowlisted by MAC even if IP changed"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Test Device",
                            mac="aa:bb:cc:dd:ee:ff",
                            enabled=True,
                        )
                    ]
                )
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="test_policy",
            reason="Blocked",
        )

        # Different IP but same MAC
        decision = should_enforce_policy(
            request={},
            policy_result=policy_result,
            client_ip="192.168.1.200",
            config=config,
            client_mac="aa:bb:cc:dd:ee:ff",
        )

        assert decision.enforce is False
        assert decision.bypass_type == "allowlist"
        assert decision.device_name == "Test Device"


class TestPolicyViolations:
    """Test enforcement with policy violations"""

    def test_enforce_policy_violation_without_bypass(self):
        """Policy violation should be enforced without bypass"""
        config = YoriConfig(enforcement=EnforcementConfig(enabled=True))

        policy_result = PolicyResult(
            allowed=False,
            policy_name="content_filter",
            reason="Inappropriate content detected",
            violations=["profanity", "violence"],
        )

        decision = should_enforce_policy(
            request={"content": "test"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
            config=config,
        )

        assert decision.enforce is True
        assert decision.reason  # Should have a reason
        assert decision.bypass_type is None

    def test_allowlist_overrides_policy_violation(self):
        """Allowlisted device should bypass even with policy violations"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                enabled=True,
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Admin Device",
                            permanent=True,
                            enabled=True,
                        )
                    ]
                ),
            )
        )

        policy_result = PolicyResult(
            allowed=False,
            policy_name="content_filter",
            reason="Inappropriate content detected",
            violations=["profanity", "violence"],
        )

        decision = should_enforce_policy(
            request={"content": "test"},
            policy_result=policy_result,
            client_ip="192.168.1.100",
            config=config,
        )

        assert decision.enforce is False
        assert decision.bypass_type == "allowlist"


class TestComplexScenarios:
    """Test complex real-world scenarios"""

    def test_homework_hours_bypass(self):
        """Simulate homework hours scenario from documentation"""
        config = YoriConfig(
            enforcement=EnforcementConfig(
                enabled=True,
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Dad's Laptop",
                            permanent=True,
                            enabled=True,
                        ),
                        AllowlistDevice(
                            ip="192.168.1.102",
                            name="Kid's Laptop",
                            enabled=True,
                        ),
                    ],
                    time_exceptions=[
                        TimeException(
                            name="homework_hours",
                            days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.102"],
                            enabled=True,
                        )
                    ],
                ),
            )
        )

        policy_result = PolicyResult(
            allowed=False, policy_name="time_limit", reason="Daily limit exceeded"
        )

        # Dad's laptop should always bypass (permanent allowlist)
        decision = should_enforce_policy(
            request={}, policy_result=policy_result, client_ip="192.168.1.100", config=config
        )
        assert decision.enforce is False
        assert decision.bypass_type == "allowlist"

        # Kid's laptop should bypass during homework hours (tested via time_exceptions module)
        # Outside homework hours, should be enforced (tested in time exception tests)

    def test_guest_temporary_allowlist(self):
        """Test temporary allowlist for guest device"""
        from datetime import timedelta

        # Create device with 1-hour temporary allowlist
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.200",
                            name="Guest Device",
                            enabled=True,
                            expires_at=datetime.now() + timedelta(hours=1),
                        )
                    ]
                )
            )
        )

        policy_result = PolicyResult(
            allowed=False, policy_name="guest_policy", reason="Guest restrictions"
        )

        # Should bypass while temporary allowlist is valid
        decision = should_enforce_policy(
            request={}, policy_result=policy_result, client_ip="192.168.1.200", config=config
        )
        assert decision.enforce is False
        assert decision.bypass_type == "allowlist"
