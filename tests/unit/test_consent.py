"""
Unit tests for consent validation

Tests the user consent validation logic for enforcement mode.
"""

import pytest

from yori.consent import (
    ConsentValidator,
    ConsentError,
    validate_enforcement_consent,
    require_consent,
)
from yori.config import YoriConfig, EnforcementConfig


class TestConsentValidator:
    """Test ConsentValidator class"""

    def test_no_consent_required_in_observe_mode(self):
        """Test that consent is not required for config validity in observe mode"""
        config = YoriConfig(mode="observe")
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert result.valid  # Config is valid
        assert len(result.errors) == 0  # No errors
        assert not result.can_enable_enforcement  # But can't enable without consent

    def test_no_consent_required_in_advisory_mode(self):
        """Test that consent is not required in advisory mode"""
        config = YoriConfig(mode="advisory")
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert result.valid
        assert len(result.errors) == 0

    def test_consent_required_in_enforce_mode(self):
        """Test that consent is required in enforce mode"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=False, consent_accepted=False),
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert not result.valid
        assert ConsentError.CONSENT_NOT_ACCEPTED in result.errors

    def test_consent_required_when_enforcement_enabled(self):
        """Test that consent is required when enforcement.enabled=true"""
        config = YoriConfig(
            mode="observe",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=False),
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert not result.valid
        assert ConsentError.CONSENT_NOT_ACCEPTED in result.errors

    def test_valid_with_consent_in_enforce_mode(self):
        """Test that configuration is valid with consent in enforce mode"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert result.valid
        assert len(result.errors) == 0

    def test_warning_when_mode_enforce_but_not_enabled(self):
        """Test warning when mode=enforce but enforcement.enabled=false"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=False, consent_accepted=True),
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert result.valid  # Valid because consent is given
        assert len(result.warnings) > 0
        assert any("enforcement.enabled=false" in w for w in result.warnings)

    def test_warning_when_enabled_but_mode_not_enforce(self):
        """Test warning when enforcement.enabled=true but mode is not enforce"""
        config = YoriConfig(
            mode="observe",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert result.valid
        assert len(result.warnings) > 0
        assert any("mode=" in w for w in result.warnings)

    def test_error_enforcement_enabled_without_consent(self):
        """Test error when enforcement.enabled=true without consent"""
        config = YoriConfig(
            mode="observe",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=False),
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert not result.valid
        assert ConsentError.ENFORCEMENT_ENABLED_WITHOUT_CONSENT in result.errors

    def test_error_mode_enforce_without_consent(self):
        """Test error when mode=enforce without consent"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=False, consent_accepted=False),
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert not result.valid
        assert ConsentError.MODE_ENFORCE_WITHOUT_CONSENT in result.errors

    def test_can_enable_enforcement_with_consent(self):
        """Test that enforcement can be enabled when consent is given"""
        config = YoriConfig(
            enforcement=EnforcementConfig(consent_accepted=True)
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert result.can_enable_enforcement

    def test_cannot_enable_enforcement_without_consent(self):
        """Test that enforcement cannot be enabled without consent"""
        config = YoriConfig(
            enforcement=EnforcementConfig(consent_accepted=False)
        )
        validator = ConsentValidator(config)

        result = validator.validate_consent()

        assert not result.can_enable_enforcement

    def test_get_consent_warning(self):
        """Test that consent warning message is available"""
        config = YoriConfig()
        validator = ConsentValidator(config)

        warning = validator.get_consent_warning()

        assert isinstance(warning, str)
        assert len(warning) > 100  # Should be a substantial warning
        assert "WARNING" in warning or "Warning" in warning

    def test_validate_config_change(self):
        """Test validating a proposed configuration change"""
        validator = ConsentValidator(YoriConfig())

        new_config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=False),
        )

        result = validator.validate_config_change(new_config)

        assert not result.valid


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_validate_enforcement_consent_function(self):
        """Test validate_enforcement_consent function"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )

        result = validate_enforcement_consent(config)

        assert result.valid

    def test_require_consent_passes_with_consent(self):
        """Test require_consent passes with valid consent"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=True),
        )

        # Should not raise
        require_consent(config)

    def test_require_consent_raises_without_consent(self):
        """Test require_consent raises PermissionError without consent"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=True, consent_accepted=False),
        )

        with pytest.raises(PermissionError):
            require_consent(config)

    def test_require_consent_raises_in_enforce_mode_without_consent(self):
        """Test require_consent raises in enforce mode without consent"""
        config = YoriConfig(
            mode="enforce",
            enforcement=EnforcementConfig(enabled=False, consent_accepted=False),
        )

        with pytest.raises(PermissionError):
            require_consent(config)


class TestConsentErrorEnum:
    """Test ConsentError enum"""

    def test_consent_error_values(self):
        """Test that ConsentError enum has expected values"""
        assert ConsentError.CONSENT_NOT_ACCEPTED.value == "consent_not_accepted"
        assert (
            ConsentError.ENFORCEMENT_ENABLED_WITHOUT_CONSENT.value
            == "enforcement_enabled_without_consent"
        )
        assert (
            ConsentError.MODE_ENFORCE_WITHOUT_CONSENT.value
            == "mode_enforce_without_consent"
        )
