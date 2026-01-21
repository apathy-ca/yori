#!/usr/bin/env python3
"""
YORI Allowlist Implementation Verification Script

This script verifies that all components of the allowlist system are working correctly.
It runs a series of tests to ensure:
1. All modules can be imported
2. Basic functionality works
3. Configuration can be loaded
4. CLI works
5. All tests pass
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

PASSED = 0
FAILED = 0


def test(name: str):
    """Decorator for test functions"""
    def decorator(func):
        def wrapper():
            global PASSED, FAILED
            print(f"\n{'=' * 60}")
            print(f"TEST: {name}")
            print('=' * 60)
            try:
                func()
                print(f"✓ PASSED: {name}")
                PASSED += 1
                return True
            except Exception as e:
                print(f"✗ FAILED: {name}")
                print(f"  Error: {e}")
                FAILED += 1
                return False
        return wrapper
    return decorator


@test("Import all modules")
def test_imports():
    """Test that all modules can be imported"""
    from yori.config import YoriConfig
    from yori.models import (
        AllowlistDevice,
        TimeException,
        EmergencyOverride,
        PolicyResult,
        EnforcementDecision,
    )
    from yori.allowlist import is_allowlisted, add_device, remove_device
    from yori.time_exceptions import (
        add_exception,
        check_any_exception_active,
        is_exception_active,
    )
    from yori.emergency import (
        activate_override,
        deactivate_override,
        is_emergency_override_active,
    )
    from yori.enforcement import should_enforce_policy

    print("  ✓ All modules imported successfully")


@test("Create and load configuration")
def test_config():
    """Test configuration creation and loading"""
    from yori.config import YoriConfig

    # Create default config
    config = YoriConfig()
    assert config.mode in ["observe", "advisory", "enforce"]
    print(f"  ✓ Created config with mode: {config.mode}")

    # Check enforcement config exists
    assert config.enforcement is not None
    print("  ✓ Enforcement configuration initialized")


@test("Add and check allowlist device")
def test_allowlist_basic():
    """Test basic allowlist functionality"""
    from yori.config import YoriConfig
    from yori.allowlist import add_device, is_allowlisted

    config = YoriConfig()

    # Add device
    device = add_device(config, "192.168.1.100", "Test Device", mac="aa:bb:cc:dd:ee:ff")
    print(f"  ✓ Added device: {device.name}")

    # Check if allowlisted by IP
    is_allowed, found_device = is_allowlisted("192.168.1.100", config)
    assert is_allowed is True
    assert found_device.name == "Test Device"
    print(f"  ✓ Device found by IP: {found_device.name}")

    # Check if allowlisted by MAC (different IP)
    is_allowed, found_device = is_allowlisted(
        "192.168.1.200", config, client_mac="aa:bb:cc:dd:ee:ff"
    )
    assert is_allowed is True
    print("  ✓ Device found by MAC address")


@test("Temporary allowlist with expiration")
def test_temporary_allowlist():
    """Test temporary allowlist entries"""
    from yori.config import YoriConfig
    from yori.allowlist import add_device, is_allowlisted

    config = YoriConfig()

    # Add device that expires in 1 hour
    expires = datetime.now() + timedelta(hours=1)
    device = add_device(config, "192.168.1.200", "Guest", expires_at=expires)

    is_allowed, _ = is_allowlisted("192.168.1.200", config)
    assert is_allowed is True
    print("  ✓ Temporary device is allowlisted")

    # Add device that already expired
    expired = datetime.now() - timedelta(hours=1)
    device = add_device(config, "192.168.1.201", "Expired", expires_at=expired)

    is_allowed, _ = is_allowlisted("192.168.1.201", config)
    assert is_allowed is False
    print("  ✓ Expired device is not allowlisted")


@test("Time-based exceptions")
def test_time_exceptions():
    """Test time-based exception logic"""
    from yori.config import YoriConfig
    from yori.time_exceptions import add_exception, is_exception_active

    config = YoriConfig()

    # Add homework hours exception
    exception = add_exception(
        config,
        name="homework",
        description="Homework time",
        days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        start_time="15:00",
        end_time="18:00",
        device_ips=["192.168.1.102"],
    )
    print(f"  ✓ Added exception: {exception.name}")

    # Check during active time (Monday 4pm)
    check_time = datetime(2026, 1, 19, 16, 0)  # Monday 4:00 PM
    is_active = is_exception_active("homework", "192.168.1.102", config, check_time)
    assert is_active is True
    print("  ✓ Exception active during homework hours")

    # Check outside active time (Monday 2pm)
    check_time = datetime(2026, 1, 19, 14, 0)  # Monday 2:00 PM
    is_active = is_exception_active("homework", "192.168.1.102", config, check_time)
    assert is_active is False
    print("  ✓ Exception inactive outside homework hours")

    # Check wrong day (Saturday 4pm)
    check_time = datetime(2026, 1, 18, 16, 0)  # Saturday 4:00 PM
    is_active = is_exception_active("homework", "192.168.1.102", config, check_time)
    assert is_active is False
    print("  ✓ Exception inactive on weekends")


@test("Emergency override")
def test_emergency():
    """Test emergency override mechanism"""
    from yori.config import YoriConfig
    from yori.emergency import (
        set_override_password,
        activate_override,
        deactivate_override,
        is_emergency_override_active,
    )

    config = YoriConfig()

    # Set password
    set_override_password(config, "test123")
    print("  ✓ Password set")

    # Activate with correct password
    success, message = activate_override(config, password="test123", activated_by="test")
    assert success is True
    assert is_emergency_override_active(config) is True
    print("  ✓ Override activated successfully")

    # Deactivate
    success, message = deactivate_override(config, password="test123")
    assert success is True
    assert is_emergency_override_active(config) is False
    print("  ✓ Override deactivated successfully")

    # Try to activate with wrong password
    success, message = activate_override(config, password="wrong", activated_by="test")
    assert success is False
    print("  ✓ Wrong password rejected")


@test("Enforcement decision flow")
def test_enforcement():
    """Test full enforcement decision logic"""
    from yori.config import YoriConfig
    from yori.models import PolicyResult
    from yori.allowlist import add_device
    from yori.emergency import activate_override, set_override_password
    from yori.enforcement import should_enforce_policy

    config = YoriConfig()

    # Policy that blocks
    policy_result = PolicyResult(
        allowed=False, policy_name="test", reason="Test block"
    )

    # Test 1: No bypass - should enforce
    decision = should_enforce_policy({}, policy_result, "192.168.1.100", config)
    assert decision.enforce is True
    print("  ✓ Enforces when not allowlisted")

    # Test 2: Allowlist bypass
    add_device(config, "192.168.1.100", "Test")
    decision = should_enforce_policy({}, policy_result, "192.168.1.100", config)
    assert decision.enforce is False
    assert decision.bypass_type == "allowlist"
    print("  ✓ Bypasses for allowlisted device")

    # Test 3: Emergency override (highest priority)
    set_override_password(config, "test")
    activate_override(config, password="test")
    decision = should_enforce_policy({}, policy_result, "192.168.1.200", config)
    assert decision.enforce is False
    assert decision.bypass_type == "emergency_override"
    print("  ✓ Emergency override bypasses all enforcement")


@test("Unit tests pass")
def test_unit_tests():
    """Run pytest unit tests"""
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).parent / "python")},
    )

    # Check if pytest succeeded
    if result.returncode == 0:
        # Count passed tests
        output = result.stdout
        if "passed" in output:
            print(f"  ✓ All unit tests passed")
        else:
            raise Exception("No test results found")
    else:
        raise Exception(f"pytest failed:\n{result.stdout}\n{result.stderr}")


@test("Integration tests pass")
def test_integration_tests():
    """Run pytest integration tests"""
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).parent / "python")},
    )

    if result.returncode == 0:
        print(f"  ✓ All integration tests passed")
    else:
        raise Exception(f"pytest failed:\n{result.stdout}\n{result.stderr}")


@test("CLI help works")
def test_cli():
    """Test CLI help command"""
    result = subprocess.run(
        ["python3", "python/yori/cli.py", "--help"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and "YORI" in result.stdout:
        print("  ✓ CLI help works")
    else:
        raise Exception(f"CLI help failed:\n{result.stdout}")


@test("Configuration example is valid")
def test_config_example():
    """Test that yori.conf.example can be loaded"""
    from yori.config import YoriConfig

    if Path("yori.conf.example").exists():
        config = YoriConfig.from_yaml(Path("yori.conf.example"))
        assert config is not None
        assert config.enforcement is not None
        assert len(config.enforcement.allowlist.devices) > 0
        print(f"  ✓ Example config loaded with {len(config.enforcement.allowlist.devices)} devices")
    else:
        raise Exception("yori.conf.example not found")


def main():
    """Run all verification tests"""
    global PASSED, FAILED

    print("\n" + "=" * 60)
    print(" YORI Allowlist Implementation Verification ".center(60, "="))
    print("=" * 60)

    # Run all tests
    test_imports()
    test_config()
    test_allowlist_basic()
    test_temporary_allowlist()
    test_time_exceptions()
    test_emergency()
    test_enforcement()
    test_unit_tests()
    test_integration_tests()
    test_cli()
    test_config_example()

    # Summary
    print("\n" + "=" * 60)
    print(" VERIFICATION SUMMARY ".center(60, "="))
    print("=" * 60)
    print(f"  ✓ Passed: {PASSED}")
    print(f"  ✗ Failed: {FAILED}")
    print(f"  Total:  {PASSED + FAILED}")
    print("=" * 60)

    if FAILED == 0:
        print("\n✓ ALL VERIFICATION TESTS PASSED!")
        print("\nThe YORI allowlist implementation is working correctly.")
        print("\nNext steps:")
        print("  1. Review ALLOWLIST_IMPLEMENTATION.md for documentation")
        print("  2. Run examples/python_usage.py to see usage examples")
        print("  3. Try the CLI: python3 python/yori/cli.py --help")
        print("=" * 60)
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        print("\nPlease review the errors above and fix the issues.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
