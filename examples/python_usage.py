#!/usr/bin/env python3
"""
YORI Python API Usage Examples

This script demonstrates how to use the YORI Python API to manage
allowlist, time exceptions, and emergency override programmatically.
"""

from datetime import datetime, timedelta
from yori.config import YoriConfig
from yori.models import PolicyResult
from yori.allowlist import add_device, remove_device, is_allowlisted
from yori.time_exceptions import add_exception, check_any_exception_active
from yori.emergency import (
    set_override_password,
    activate_override,
    deactivate_override,
    is_emergency_override_active,
)
from yori.enforcement import should_enforce_policy


def example_1_add_permanent_device():
    """Example 1: Add a permanent device to allowlist"""
    print("=" * 60)
    print("Example 1: Add permanent device to allowlist")
    print("=" * 60)

    config = YoriConfig()

    # Add Dad's laptop - permanent, never blocked
    device = add_device(
        config,
        ip="192.168.1.100",
        name="Dad's Laptop",
        mac="aa:bb:cc:dd:ee:ff",
        permanent=True,
        group="family",
        notes="Primary admin device",
    )

    print(f"✓ Added: {device.name}")
    print(f"  IP: {device.ip}")
    print(f"  MAC: {device.mac}")
    print(f"  Permanent: {device.permanent}")
    print()


def example_2_add_temporary_device():
    """Example 2: Add temporary device (1 hour)"""
    print("=" * 60)
    print("Example 2: Add temporary device (expires in 1 hour)")
    print("=" * 60)

    config = YoriConfig()

    # Add guest device - expires in 1 hour
    expires = datetime.now() + timedelta(hours=1)
    device = add_device(
        config,
        ip="192.168.1.200",
        name="Guest Device",
        expires_at=expires,
        notes="Visitor for afternoon meeting",
    )

    print(f"✓ Added: {device.name}")
    print(f"  IP: {device.ip}")
    print(f"  Expires: {device.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def example_3_check_allowlist():
    """Example 3: Check if device is allowlisted"""
    print("=" * 60)
    print("Example 3: Check if device is allowlisted")
    print("=" * 60)

    config = YoriConfig()
    add_device(config, "192.168.1.100", "Test Device", mac="aa:bb:cc:dd:ee:ff")

    # Check by IP
    is_allowed, device = is_allowlisted("192.168.1.100", config)
    print(f"IP 192.168.1.100: {'✓ ALLOWED' if is_allowed else '✗ BLOCKED'}")

    # Check by MAC (even if IP is different)
    is_allowed, device = is_allowlisted(
        "192.168.1.200", config, client_mac="aa:bb:cc:dd:ee:ff"
    )
    print(f"MAC aa:bb:cc:dd:ee:ff: {'✓ ALLOWED' if is_allowed else '✗ BLOCKED'}")
    if device:
        print(f"  Device: {device.name}")
    print()


def example_4_time_exceptions():
    """Example 4: Add time-based exception"""
    print("=" * 60)
    print("Example 4: Add time-based exception (homework hours)")
    print("=" * 60)

    config = YoriConfig()

    # Add homework hours: Mon-Fri 3-6pm
    exception = add_exception(
        config,
        name="homework_hours",
        description="Allow LLM access for homework help",
        days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        start_time="15:00",
        end_time="18:00",
        device_ips=["192.168.1.102"],
    )

    print(f"✓ Added exception: {exception.name}")
    print(f"  Days: {', '.join(exception.days)}")
    print(f"  Time: {exception.start_time} - {exception.end_time}")
    print(f"  Devices: {', '.join(exception.device_ips)}")
    print()

    # Check if exception is active (Monday 4pm)
    check_time = datetime(2026, 1, 19, 16, 0)  # Monday 4:00 PM
    is_active, active_exception = check_any_exception_active(
        "192.168.1.102", config, check_time
    )

    print(f"Active at {check_time.strftime('%A %H:%M')}: {is_active}")
    print()


def example_5_emergency_override():
    """Example 5: Emergency override"""
    print("=" * 60)
    print("Example 5: Emergency override")
    print("=" * 60)

    config = YoriConfig()

    # Set password
    set_override_password(config, "admin123")
    print("✓ Password set")

    # Activate override
    success, message = activate_override(
        config, password="admin123", activated_by="admin@192.168.1.1"
    )

    if success:
        print(f"✓ {message}")
        print(f"  Active: {is_emergency_override_active(config)}")
    else:
        print(f"✗ {message}")

    # Deactivate override
    success, message = deactivate_override(config, password="admin123")

    if success:
        print(f"✓ {message}")
        print(f"  Active: {is_emergency_override_active(config)}")
    print()


def example_6_enforcement_decision():
    """Example 6: Full enforcement decision flow"""
    print("=" * 60)
    print("Example 6: Enforcement decision flow")
    print("=" * 60)

    config = YoriConfig()

    # Setup: Add allowlisted device
    add_device(config, "192.168.1.100", "Admin Device", permanent=True)

    # Simulate policy that blocks request
    policy_result = PolicyResult(
        allowed=False,
        policy_name="content_filter",
        reason="Inappropriate content detected",
        violations=["profanity"],
    )

    # Decision for allowlisted device
    decision = should_enforce_policy(
        request={},
        policy_result=policy_result,
        client_ip="192.168.1.100",
        config=config,
    )

    print(f"Client IP: 192.168.1.100 (allowlisted)")
    print(f"  Enforce: {decision.enforce}")
    print(f"  Reason: {decision.reason}")
    print(f"  Bypass type: {decision.bypass_type}")
    print()

    # Decision for non-allowlisted device
    decision = should_enforce_policy(
        request={},
        policy_result=policy_result,
        client_ip="192.168.1.200",
        config=config,
    )

    print(f"Client IP: 192.168.1.200 (not allowlisted)")
    print(f"  Enforce: {decision.enforce}")
    print(f"  Reason: {decision.reason}")
    print()


def example_7_complex_scenario():
    """Example 7: Complex real-world scenario"""
    print("=" * 60)
    print("Example 7: Complex scenario - Family with homework hours")
    print("=" * 60)

    config = YoriConfig()

    # Add family devices
    add_device(config, "192.168.1.100", "Dad's Laptop", permanent=True, group="family")
    add_device(config, "192.168.1.101", "Mom's iPad", permanent=True, group="family")
    add_device(config, "192.168.1.102", "Kid's Laptop", group="family")

    # Add homework hours exception
    add_exception(
        config,
        name="homework_hours",
        description="Homework help",
        days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        start_time="15:00",
        end_time="18:00",
        device_ips=["192.168.1.102"],
    )

    # Policy that would normally block
    policy_result = PolicyResult(
        allowed=False, policy_name="time_limit", reason="Daily limit exceeded"
    )

    # Test different scenarios
    print("Scenario 1: Dad's laptop (permanent allowlist)")
    decision = should_enforce_policy(
        {}, policy_result, "192.168.1.100", config
    )
    print(f"  Result: {'ALLOWED' if not decision.enforce else 'BLOCKED'}")
    print(f"  Reason: {decision.reason}\n")

    print("Scenario 2: Kid's laptop at 4pm Monday (during homework hours)")
    check_time = datetime(2026, 1, 19, 16, 0)  # Monday 4pm
    is_active, _ = check_any_exception_active("192.168.1.102", config, check_time)
    print(f"  Time exception active: {is_active}")
    print(f"  Result: {'ALLOWED' if is_active else 'Would be BLOCKED'}\n")

    print("Scenario 3: Kid's laptop at 8pm Monday (after homework hours)")
    check_time = datetime(2026, 1, 19, 20, 0)  # Monday 8pm
    is_active, _ = check_any_exception_active("192.168.1.102", config, check_time)
    print(f"  Time exception active: {is_active}")
    print(f"  Result: {'ALLOWED' if is_active else 'BLOCKED'}\n")

    print("Scenario 4: Emergency override activated")
    set_override_password(config, "emergency123")
    activate_override(config, password="emergency123", activated_by="parent")
    decision = should_enforce_policy(
        {}, policy_result, "192.168.1.102", config
    )
    print(f"  Result: {'ALLOWED' if not decision.enforce else 'BLOCKED'}")
    print(f"  Reason: {decision.reason}")
    print()


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  YORI Allowlist System - Python API Examples".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    example_1_add_permanent_device()
    example_2_add_temporary_device()
    example_3_check_allowlist()
    example_4_time_exceptions()
    example_5_emergency_override()
    example_6_enforcement_decision()
    example_7_complex_scenario()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print()
    print("For more information, see:")
    print("  - ALLOWLIST_IMPLEMENTATION.md")
    print("  - examples/cli_usage.sh")
    print("=" * 60)


if __name__ == "__main__":
    main()
