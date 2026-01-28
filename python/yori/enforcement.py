"""
Enforcement decision logic

Determines whether to enforce policy results based on allowlist, time exceptions,
and emergency override settings.
"""

from typing import Optional
import logging

from yori.models import PolicyResult, EnforcementDecision
from yori.config import YoriConfig
from yori.allowlist import is_allowlisted
from yori.time_exceptions import check_any_exception_active
from yori.emergency import is_emergency_override_active

# Alias for backwards compatibility with tests
EnforcementEngineDecision = EnforcementDecision

logger = logging.getLogger(__name__)


def should_enforce_policy(
    request: dict,
    policy_result: PolicyResult,
    client_ip: str,
    config: YoriConfig,
    client_mac: Optional[str] = None,
) -> EnforcementDecision:
    """
    Determine whether to enforce a policy result

    This is the main entry point for enforcement decisions. Checks (in order):
    1. Emergency override - if active, bypass ALL enforcement
    2. Allowlist - if device is allowlisted, bypass enforcement
    3. Time exceptions - if active time exception exists, bypass enforcement
    4. Otherwise, enforce the policy result

    Args:
        request: The original request data
        policy_result: Result from policy evaluation
        client_ip: Client IP address
        config: Full YORI configuration
        client_mac: Client MAC address (optional)

    Returns:
        EnforcementDecision indicating whether to enforce and why
    """
    # If policy allows the request, no enforcement needed
    if policy_result.allowed:
        return EnforcementDecision(
            enforce=False,
            reason="Policy allows request",
            bypass_type=None,
            device_name=None
        )

    # Check 1: Emergency override (highest priority)
    if is_emergency_override_active(config):
        logger.warning(f"Emergency override active - bypassing enforcement for {client_ip}")
        return EnforcementDecision(
            enforce=False,
            reason="Emergency override is active - all enforcement disabled",
            bypass_type="emergency_override",
            device_name=None
        )

    # Check 2: Device allowlist
    is_on_allowlist, device = is_allowlisted(client_ip, config, client_mac)
    if is_on_allowlist and device:
        logger.info(f"Allowlist bypass for device: {device.name} ({client_ip})")
        return EnforcementDecision(
            enforce=False,
            reason=f"Device is on allowlist: {device.name}",
            bypass_type="allowlist",
            device_name=device.name
        )

    # Check 3: Time-based exceptions
    exception_active, exception = check_any_exception_active(client_ip, config)
    if exception_active and exception:
        logger.info(f"Time exception '{exception.name}' active for {client_ip}")
        return EnforcementDecision(
            enforce=False,
            reason=f"Time exception active: {exception.name}",
            bypass_type="time_exception",
            device_name=exception.name
        )

    # No bypasses apply - enforce the policy result
    logger.info(f"Enforcing policy for {client_ip}: {policy_result.reason or 'Policy violation'}")
    return EnforcementDecision(
        enforce=True,
        reason=policy_result.reason or f"Policy '{policy_result.policy_name}' blocks request",
        bypass_type=None,
        device_name=None
    )


def get_enforcement_summary(config: YoriConfig) -> dict:
    """
    Get a summary of current enforcement configuration

    Args:
        config: Full YORI configuration

    Returns:
        Dictionary with enforcement status summary
    """
    if not config.enforcement:
        return {
            "enforcement_enabled": False,
            "allowlist_devices": 0,
            "allowlist_groups": 0,
            "time_exceptions": 0,
            "emergency_override_active": False,
        }

    allowlist = config.enforcement.allowlist

    return {
        "enforcement_enabled": config.enforcement.enabled,
        "consent_accepted": config.enforcement.consent_accepted,
        "allowlist_devices": len(allowlist.devices),
        "allowlist_devices_active": sum(
            1 for d in allowlist.devices
            if d.enabled and (not d.expires_at or d.expires_at > datetime.now())
        ),
        "allowlist_groups": len(allowlist.groups),
        "time_exceptions": len(allowlist.time_exceptions),
        "time_exceptions_active": sum(1 for e in allowlist.time_exceptions if e.enabled),
        "emergency_override_active": config.enforcement.emergency_override.enabled,
        "emergency_override_activated_by": config.enforcement.emergency_override.activated_by,
    }


# Import datetime for summary function
from datetime import datetime
