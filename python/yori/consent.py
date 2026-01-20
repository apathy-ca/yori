"""
User Consent Validation

Validates that users have explicitly consented to enforcement mode before
allowing it to be enabled. This prevents accidental enabling of blocking
functionality that could break LLM-dependent applications.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List
import logging

from yori.config import YoriConfig

logger = logging.getLogger(__name__)


class ConsentError(Enum):
    """Types of consent validation errors"""

    CONSENT_NOT_ACCEPTED = "consent_not_accepted"
    ENFORCEMENT_ENABLED_WITHOUT_CONSENT = "enforcement_enabled_without_consent"
    MODE_ENFORCE_WITHOUT_CONSENT = "mode_enforce_without_consent"
    BOTH_FLAGS_REQUIRED = "both_flags_required"


@dataclass
class ConsentValidationResult:
    """Result of consent validation"""

    valid: bool
    errors: List[ConsentError]
    warnings: List[str]
    can_enable_enforcement: bool


class ConsentValidator:
    """
    Validates user consent for enforcement mode.

    Ensures users cannot accidentally enable blocking functionality without
    explicitly accepting the risks.
    """

    WARNING_MESSAGE = """
WARNING: Enforcement mode will actively BLOCK LLM requests based on your policies.

This can break:
- AI-powered applications and services
- ChatGPT, Claude, and other LLM interfaces
- Development tools that use LLM APIs
- Any software relying on intercepted endpoints

Before enabling enforcement mode:
1. Test ALL policies in 'observe' mode first
2. Review audit logs to understand what will be blocked
3. Configure per-policy actions carefully (allow/alert/block)
4. Have a plan to quickly disable enforcement if needed

By checking 'consent_accepted', you acknowledge these risks.
"""

    def __init__(self, config: YoriConfig):
        self.config = config

    def validate_consent(self) -> ConsentValidationResult:
        """
        Validate that consent requirements are met for current configuration.

        Returns:
            ConsentValidationResult with validation status
        """
        errors: List[ConsentError] = []
        warnings: List[str] = []

        # Check if enforcement is being attempted
        enforcement_attempted = (
            self.config.mode == "enforce" or self.config.enforcement.enabled
        )

        # If not attempting enforcement, no consent required (valid=True)
        # But can_enable_enforcement depends on consent_accepted
        if not enforcement_attempted:
            return ConsentValidationResult(
                valid=True,
                errors=[],
                warnings=[],
                can_enable_enforcement=self.config.enforcement.consent_accepted,
            )

        # Check consent flag
        if not self.config.enforcement.consent_accepted:
            errors.append(ConsentError.CONSENT_NOT_ACCEPTED)

        # Check for dangerous combinations
        if self.config.enforcement.enabled and not self.config.enforcement.consent_accepted:
            errors.append(ConsentError.ENFORCEMENT_ENABLED_WITHOUT_CONSENT)

        if self.config.mode == "enforce" and not self.config.enforcement.consent_accepted:
            errors.append(ConsentError.MODE_ENFORCE_WITHOUT_CONSENT)

        # Check that both required flags are set for enforcement to work
        if self.config.mode == "enforce" and not self.config.enforcement.enabled:
            warnings.append(
                "Mode is 'enforce' but enforcement.enabled=false - enforcement will not activate"
            )

        if self.config.enforcement.enabled and self.config.mode != "enforce":
            warnings.append(
                f"enforcement.enabled=true but mode='{self.config.mode}' - enforcement will not activate"
            )

        # Determine if enforcement can be enabled
        can_enable = self.config.enforcement.consent_accepted

        return ConsentValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            can_enable_enforcement=can_enable,
        )

    def get_consent_warning(self) -> str:
        """Get the warning message to display to users before accepting consent."""
        return self.WARNING_MESSAGE

    def validate_config_change(
        self, new_config: YoriConfig
    ) -> ConsentValidationResult:
        """
        Validate a proposed configuration change.

        Use this before applying configuration changes to ensure consent
        requirements are met.

        Args:
            new_config: Proposed new configuration

        Returns:
            ConsentValidationResult
        """
        validator = ConsentValidator(new_config)
        return validator.validate_consent()


def validate_enforcement_consent(config: YoriConfig) -> ConsentValidationResult:
    """
    Convenience function to validate consent.

    Args:
        config: Configuration to validate

    Returns:
        ConsentValidationResult
    """
    validator = ConsentValidator(config)
    return validator.validate_consent()


def require_consent(config: YoriConfig) -> None:
    """
    Require that consent is valid, raise exception if not.

    Use this in critical paths where enforcement must not proceed without consent.

    Args:
        config: Configuration to validate

    Raises:
        PermissionError: If consent is not valid
    """
    result = validate_enforcement_consent(config)

    if not result.valid:
        error_messages = [
            f"- {error.value}" for error in result.errors
        ]
        raise PermissionError(
            f"Enforcement mode consent not valid:\n" + "\n".join(error_messages)
        )

    # Log warnings even if valid
    for warning in result.warnings:
        logger.warning(f"Consent validation warning: {warning}")
