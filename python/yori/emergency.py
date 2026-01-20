"""
Emergency override mechanism

Provides ability to instantly disable all enforcement for emergency situations.
"""

from datetime import datetime
from typing import Optional
import hashlib
import logging

from yori.models import EmergencyOverride
from yori.config import YoriConfig

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Create SHA-256 hash of password

    Args:
        password: Plain text password

    Returns:
        SHA-256 hash as hex string with 'sha256:' prefix
    """
    hash_bytes = hashlib.sha256(password.encode('utf-8')).digest()
    return f"sha256:{hash_bytes.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify password against stored hash

    Args:
        password: Plain text password to verify
        password_hash: Stored hash (with 'sha256:' prefix)

    Returns:
        True if password matches hash
    """
    if not password_hash.startswith("sha256:"):
        logger.error("Invalid password hash format (missing sha256: prefix)")
        return False

    computed_hash = hash_password(password)
    return computed_hash == password_hash


def is_emergency_override_active(config: YoriConfig) -> bool:
    """
    Check if emergency override is currently active

    When active, ALL enforcement is disabled immediately.

    Args:
        config: Full YORI configuration

    Returns:
        True if emergency override is active
    """
    if not config.enforcement or not config.enforcement.emergency_override:
        return False

    return config.enforcement.emergency_override.enabled


def activate_override(config: YoriConfig, password: Optional[str] = None,
                      activated_by: Optional[str] = None) -> tuple[bool, str]:
    """
    Activate emergency override to disable all enforcement

    Args:
        config: Full YORI configuration
        password: Admin password (required if require_password is True)
        activated_by: IP address or identifier of who activated override

    Returns:
        Tuple of (success, message)
        - success: True if override was activated
        - message: Status message
    """
    if not config.enforcement:
        from yori.models import EnforcementConfig
        config.enforcement = EnforcementConfig()

    override = config.enforcement.emergency_override

    # Check password if required
    if override.require_password:
        if not password:
            return False, "Password required to activate emergency override"

        if not override.password_hash:
            return False, "No password configured for emergency override"

        if not verify_password(password, override.password_hash):
            logger.warning(f"Failed emergency override activation attempt from {activated_by}")
            return False, "Invalid password"

    # Activate override
    override.enabled = True
    override.activated_at = datetime.now()
    override.activated_by = activated_by

    logger.warning(f"EMERGENCY OVERRIDE ACTIVATED by {activated_by or 'unknown'} - All enforcement disabled")

    return True, "Emergency override activated - All enforcement disabled"


def deactivate_override(config: YoriConfig, password: Optional[str] = None) -> tuple[bool, str]:
    """
    Deactivate emergency override to re-enable enforcement

    Args:
        config: Full YORI configuration
        password: Admin password (required if require_password is True)

    Returns:
        Tuple of (success, message)
        - success: True if override was deactivated
        - message: Status message
    """
    if not config.enforcement or not config.enforcement.emergency_override:
        return False, "Emergency override not configured"

    override = config.enforcement.emergency_override

    # Check password if required
    if override.require_password:
        if not password:
            return False, "Password required to deactivate emergency override"

        if not override.password_hash:
            return False, "No password configured for emergency override"

        if not verify_password(password, override.password_hash):
            logger.warning("Failed emergency override deactivation attempt")
            return False, "Invalid password"

    # Deactivate override
    override.enabled = False
    override.activated_at = None
    override.activated_by = None

    logger.warning("EMERGENCY OVERRIDE DEACTIVATED - Enforcement re-enabled")

    return True, "Emergency override deactivated - Enforcement re-enabled"


def set_override_password(config: YoriConfig, password: str) -> bool:
    """
    Set the emergency override password

    Args:
        config: Full YORI configuration
        password: New password to set

    Returns:
        True if password was set
    """
    if not config.enforcement:
        from yori.models import EnforcementConfig
        config.enforcement = EnforcementConfig()

    config.enforcement.emergency_override.password_hash = hash_password(password)
    logger.info("Emergency override password updated")

    return True


def get_override_status(config: YoriConfig) -> dict:
    """
    Get current emergency override status

    Args:
        config: Full YORI configuration

    Returns:
        Dictionary with override status information
    """
    if not config.enforcement or not config.enforcement.emergency_override:
        return {
            "configured": False,
            "enabled": False,
            "activated_at": None,
            "activated_by": None,
            "require_password": True,
        }

    override = config.enforcement.emergency_override

    return {
        "configured": True,
        "enabled": override.enabled,
        "activated_at": override.activated_at.isoformat() if override.activated_at else None,
        "activated_by": override.activated_by,
        "require_password": override.require_password,
        "has_password": bool(override.password_hash),
    }


def toggle_password_requirement(config: YoriConfig, require: bool) -> bool:
    """
    Enable or disable password requirement for emergency override

    SECURITY WARNING: Disabling password requirement allows anyone to activate
    emergency override without authentication. Only use in trusted environments.

    Args:
        config: Full YORI configuration
        require: True to require password, False to allow activation without password

    Returns:
        True if setting was updated
    """
    if not config.enforcement:
        from yori.models import EnforcementConfig
        config.enforcement = EnforcementConfig()

    config.enforcement.emergency_override.require_password = require

    if require:
        logger.info("Emergency override now requires password")
    else:
        logger.warning("Emergency override password requirement DISABLED - Anyone can activate!")

    return True
