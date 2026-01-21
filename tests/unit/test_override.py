"""
Unit tests for override password validation and rate limiting
"""

import pytest
import time
from datetime import datetime
from yori.override import (
    hash_password,
    validate_override_password,
    validate_emergency_override,
    check_override_rate_limit,
    reset_override_rate_limit,
    create_override_event,
    log_override_event,
    RateLimiter,
)


def test_hash_password():
    """Test password hashing"""
    password = "test123"
    hashed = hash_password(password)

    assert hashed.startswith("sha256:")
    assert len(hashed) > 7  # sha256: + hex digest

    # Same password should produce same hash
    hashed2 = hash_password(password)
    assert hashed == hashed2

    # Different password should produce different hash
    hashed3 = hash_password("different")
    assert hashed != hashed3


def test_validate_override_password():
    """Test override password validation"""
    password = "my_password"
    hashed = hash_password(password)

    # Correct password should validate
    assert validate_override_password(password, hashed) is True

    # Wrong password should not validate
    assert validate_override_password("wrong_password", hashed) is False

    # Empty password should not validate
    assert validate_override_password("", hashed) is False


def test_validate_override_password_invalid_format():
    """Test validation with invalid hash format"""
    # Hash without sha256: prefix
    invalid_hash = "abc123def456"
    assert validate_override_password("test", invalid_hash) is False

    # Empty hash
    assert validate_override_password("test", "") is False


def test_validate_emergency_override():
    """Test emergency override token validation"""
    token = "admin_emergency_token"
    hashed = hash_password(token)

    # Correct token should validate
    assert validate_emergency_override(token, hashed) is True

    # Wrong token should not validate
    assert validate_emergency_override("wrong_token", hashed) is False


def test_rate_limiter_basic():
    """Test basic rate limiting functionality"""
    limiter = RateLimiter(max_attempts=3, window_seconds=60)

    # First 3 attempts should succeed
    assert limiter.check_rate_limit("client1") is True
    assert limiter.check_rate_limit("client1") is True
    assert limiter.check_rate_limit("client1") is True

    # 4th attempt should be rate limited
    assert limiter.check_rate_limit("client1") is False


def test_rate_limiter_different_clients():
    """Test that rate limiting is per-client"""
    limiter = RateLimiter(max_attempts=2, window_seconds=60)

    # Client 1
    assert limiter.check_rate_limit("client1") is True
    assert limiter.check_rate_limit("client1") is True
    assert limiter.check_rate_limit("client1") is False  # Rate limited

    # Client 2 should not be affected
    assert limiter.check_rate_limit("client2") is True
    assert limiter.check_rate_limit("client2") is True
    assert limiter.check_rate_limit("client2") is False  # Rate limited


def test_rate_limiter_reset():
    """Test rate limiter reset"""
    limiter = RateLimiter(max_attempts=2, window_seconds=60)

    # Exhaust limit
    limiter.check_rate_limit("client1")
    limiter.check_rate_limit("client1")
    assert limiter.check_rate_limit("client1") is False

    # Reset
    limiter.reset("client1")

    # Should be able to make attempts again
    assert limiter.check_rate_limit("client1") is True


def test_rate_limiter_window_expiry():
    """Test that rate limit window expires"""
    limiter = RateLimiter(max_attempts=2, window_seconds=1)  # 1 second window

    # Exhaust limit
    limiter.check_rate_limit("client1")
    limiter.check_rate_limit("client1")
    assert limiter.check_rate_limit("client1") is False

    # Wait for window to expire
    time.sleep(1.1)

    # Should be able to make attempts again
    assert limiter.check_rate_limit("client1") is True


def test_check_override_rate_limit():
    """Test global override rate limit check"""
    # Reset any existing state
    reset_override_rate_limit("test_ip")

    # Should allow attempts
    assert check_override_rate_limit("test_ip") is True
    assert check_override_rate_limit("test_ip") is True
    assert check_override_rate_limit("test_ip") is True

    # 4th attempt should be rate limited (default is 3 per minute)
    assert check_override_rate_limit("test_ip") is False

    # Reset
    reset_override_rate_limit("test_ip")


def test_create_override_event():
    """Test override event creation"""
    event = create_override_event(
        request_id="test-123",
        client_ip="192.168.1.100",
        policy_name="bedtime.rego",
        password="test_password",
        success=True,
        emergency=False,
    )

    assert event.request_id == "test-123"
    assert event.client_ip == "192.168.1.100"
    assert event.policy_name == "bedtime.rego"
    assert event.success is True
    assert event.emergency is False
    assert event.password_hash.startswith("sha256:")
    assert isinstance(event.timestamp, datetime)


def test_create_override_event_emergency():
    """Test emergency override event creation"""
    event = create_override_event(
        request_id="emergency-456",
        client_ip="192.168.1.200",
        policy_name="strict.rego",
        password="admin_token",
        success=True,
        emergency=True,
    )

    assert event.emergency is True


def test_log_override_event(caplog):
    """Test override event logging"""
    import logging

    # Set up logging to capture
    caplog.set_level(logging.INFO)

    event = create_override_event(
        request_id="log-test-789",
        client_ip="192.168.1.50",
        policy_name="test.rego",
        password="password",
        success=True,
        emergency=False,
    )

    log_override_event(event)

    # Check that log was created
    assert "override_success" in caplog.text
    assert "log-test-789" in caplog.text
    assert "192.168.1.50" in caplog.text


def test_password_timing_attack_resistance():
    """Test that password validation is resistant to timing attacks"""
    password = "correct_password"
    hashed = hash_password(password)

    # The validate functions use secrets.compare_digest which is timing-safe
    # We can't easily test timing directly, but we can verify it uses the function

    import inspect
    source = inspect.getsource(validate_override_password)
    assert "compare_digest" in source

    source = inspect.getsource(validate_emergency_override)
    assert "compare_digest" in source
