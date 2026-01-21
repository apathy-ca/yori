"""
Unit tests for emergency override functionality
"""

import pytest

from yori.models import EmergencyOverride, EnforcementConfig
from yori.config import YoriConfig
from yori.emergency import (
    hash_password,
    verify_password,
    is_emergency_override_active,
    activate_override,
    deactivate_override,
    set_override_password,
    get_override_status,
    toggle_password_requirement,
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        password = "test_password123"
        hashed = hash_password(password)

        assert hashed.startswith("sha256:")
        assert len(hashed) > 7  # More than just the prefix

    def test_hash_password_consistent(self):
        # Same password should produce same hash
        password = "test_password123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 == hash2

    def test_hash_password_different(self):
        # Different passwords should produce different hashes
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")

        assert hash1 != hash2

    def test_verify_password_correct(self):
        password = "test_password123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "test_password123"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_invalid_format(self):
        result = verify_password("test", "invalid_hash")
        assert result is False


class TestOverrideActive:
    """Test checking if override is active"""

    def test_override_inactive(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(enabled=False)
            )
        )

        assert is_emergency_override_active(config) is False

    def test_override_active(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(enabled=True)
            )
        )

        assert is_emergency_override_active(config) is True

    def test_no_override_config(self):
        config = YoriConfig()

        assert is_emergency_override_active(config) is False


class TestActivateOverride:
    """Test activating emergency override"""

    def test_activate_without_password_requirement(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=False, require_password=False
                )
            )
        )

        success, message = activate_override(config, activated_by="192.168.1.1")

        assert success is True
        assert config.enforcement.emergency_override.enabled is True
        assert config.enforcement.emergency_override.activated_by == "192.168.1.1"
        assert config.enforcement.emergency_override.activated_at is not None

    def test_activate_with_correct_password(self):
        password = "admin123"
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=False,
                    require_password=True,
                    password_hash=hash_password(password),
                )
            )
        )

        success, message = activate_override(
            config, password=password, activated_by="192.168.1.1"
        )

        assert success is True
        assert config.enforcement.emergency_override.enabled is True

    def test_activate_with_incorrect_password(self):
        password = "admin123"
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=False,
                    require_password=True,
                    password_hash=hash_password(password),
                )
            )
        )

        success, message = activate_override(
            config, password="wrong_password", activated_by="192.168.1.1"
        )

        assert success is False
        assert "Invalid password" in message
        assert config.enforcement.emergency_override.enabled is False

    def test_activate_without_password_when_required(self):
        password = "admin123"
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=False,
                    require_password=True,
                    password_hash=hash_password(password),
                )
            )
        )

        success, message = activate_override(config, activated_by="192.168.1.1")

        assert success is False
        assert "Password required" in message
        assert config.enforcement.emergency_override.enabled is False

    def test_activate_when_no_password_configured(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=False, require_password=True, password_hash=None
                )
            )
        )

        success, message = activate_override(
            config, password="any_password", activated_by="192.168.1.1"
        )

        assert success is False
        assert "No password configured" in message


class TestDeactivateOverride:
    """Test deactivating emergency override"""

    def test_deactivate_without_password_requirement(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=True, require_password=False
                )
            )
        )

        success, message = deactivate_override(config)

        assert success is True
        assert config.enforcement.emergency_override.enabled is False
        assert config.enforcement.emergency_override.activated_at is None
        assert config.enforcement.emergency_override.activated_by is None

    def test_deactivate_with_correct_password(self):
        password = "admin123"
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=True,
                    require_password=True,
                    password_hash=hash_password(password),
                )
            )
        )

        success, message = deactivate_override(config, password=password)

        assert success is True
        assert config.enforcement.emergency_override.enabled is False

    def test_deactivate_with_incorrect_password(self):
        password = "admin123"
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=True,
                    require_password=True,
                    password_hash=hash_password(password),
                )
            )
        )

        success, message = deactivate_override(config, password="wrong_password")

        assert success is False
        assert "Invalid password" in message
        assert config.enforcement.emergency_override.enabled is True


class TestSetOverridePassword:
    """Test setting override password"""

    def test_set_password(self):
        config = YoriConfig()

        result = set_override_password(config, "new_password123")

        assert result is True
        assert config.enforcement.emergency_override.password_hash is not None
        assert config.enforcement.emergency_override.password_hash.startswith("sha256:")

    def test_password_works_after_setting(self):
        config = YoriConfig()
        password = "new_password123"

        set_override_password(config, password)

        # Password should be required by default
        config.enforcement.emergency_override.require_password = True

        success, _ = activate_override(config, password=password, activated_by="test")

        assert success is True


class TestGetOverrideStatus:
    """Test getting override status"""

    def test_status_not_configured(self):
        config = YoriConfig()

        status = get_override_status(config)

        assert status["configured"] is True
        assert status["enabled"] is False
        assert status["activated_at"] is None
        assert status["activated_by"] is None

    def test_status_configured_and_active(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=True,
                    password_hash=hash_password("test"),
                    activated_by="192.168.1.1",
                )
            )
        )

        status = get_override_status(config)

        assert status["configured"] is True
        assert status["enabled"] is True
        assert status["has_password"] is True
        assert status["activated_by"] == "192.168.1.1"


class TestTogglePasswordRequirement:
    """Test toggling password requirement"""

    def test_enable_password_requirement(self):
        config = YoriConfig()

        result = toggle_password_requirement(config, True)

        assert result is True
        assert config.enforcement.emergency_override.require_password is True

    def test_disable_password_requirement(self):
        config = YoriConfig()

        result = toggle_password_requirement(config, False)

        assert result is True
        assert config.enforcement.emergency_override.require_password is False

    def test_activate_without_password_when_disabled(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                emergency_override=EmergencyOverride(
                    enabled=False,
                    require_password=False,
                    password_hash=hash_password("test"),
                )
            )
        )

        # Should succeed without password
        success, _ = activate_override(config, activated_by="192.168.1.1")

        assert success is True
