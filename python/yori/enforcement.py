"""
Enforcement Mode Logic

Determines whether requests should be blocked based on policy evaluation results
and enforcement configuration. This module is the core decision engine for
enforcement mode.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import logging

from yori.config import YoriConfig, PolicyFileConfig

logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
    """
    Result from policy evaluation (from yori_core Rust module).
    This is a placeholder until the Rust binding is available.
    """

    action: str  # "allow", "alert", or "block" (from policy evaluation)
    reason: str  # Human-readable reason for the decision
    policy_name: str  # Name of the policy that triggered
    metadata: Optional[dict] = None  # Additional context


@dataclass
class EnforcementDecision:
    """
    Decision about whether to enforce (block) a request.
    Used by proxy to determine if request should be blocked.
    """

    should_block: bool  # Whether to actually block the request
    policy_name: str  # Name of the policy that made the decision
    reason: str  # Human-readable reason
    timestamp: datetime  # When the decision was made
    allow_override: bool  # Whether user can override the block (future: allowlist)
    action_taken: str  # "allow", "alert", or "block" - what we actually did


class EnforcementEngine:
    """
    Enforcement decision engine.

    Determines whether requests should be blocked based on:
    1. Global enforcement mode settings
    2. Per-policy action configuration
    3. Policy evaluation results
    """

    def __init__(self, config: YoriConfig):
        self.config = config

    def should_enforce_policy(
        self,
        request: dict,
        policy_result: PolicyResult,
        client_ip: str,
    ) -> EnforcementDecision:
        """
        Determines if a request should be blocked based on policy result.

        This is the main entry point for enforcement decisions.

        Args:
            request: The request being evaluated (dict with method, path, headers, etc.)
            policy_result: Result from policy evaluation (from Rust yori_core)
            client_ip: Source IP address of the request

        Returns:
            EnforcementDecision with should_block=True if request should be blocked
        """
        timestamp = datetime.now()

        # Safety check: If enforcement is not enabled, never block
        if not self._is_enforcement_enabled():
            return EnforcementDecision(
                should_block=False,
                policy_name=policy_result.policy_name,
                reason=f"Enforcement disabled: {policy_result.reason}",
                timestamp=timestamp,
                allow_override=False,
                action_taken="alert",  # Just log, don't block
            )

        # Check if this specific policy is configured to block
        policy_action = self._get_policy_action(policy_result.policy_name)

        # Determine what action to take
        if policy_action == "allow":
            # Policy is set to allow - never block
            return EnforcementDecision(
                should_block=False,
                policy_name=policy_result.policy_name,
                reason=f"Policy set to allow: {policy_result.reason}",
                timestamp=timestamp,
                allow_override=False,
                action_taken="allow",
            )
        elif policy_action == "alert":
            # Policy is set to alert only - log but don't block
            return EnforcementDecision(
                should_block=False,
                policy_name=policy_result.policy_name,
                reason=f"Policy set to alert only: {policy_result.reason}",
                timestamp=timestamp,
                allow_override=False,
                action_taken="alert",
            )
        elif policy_action == "block":
            # Policy is set to block - actually deny the request
            logger.warning(
                f"BLOCKING request from {client_ip}: {policy_result.policy_name} - {policy_result.reason}"
            )
            return EnforcementDecision(
                should_block=True,
                policy_name=policy_result.policy_name,
                reason=policy_result.reason,
                timestamp=timestamp,
                allow_override=True,  # Future: check allowlist
                action_taken="block",
            )
        else:
            # Unknown action - fail safe (don't block)
            logger.error(f"Unknown policy action: {policy_action} for {policy_result.policy_name}")
            return EnforcementDecision(
                should_block=False,
                policy_name=policy_result.policy_name,
                reason=f"Unknown action {policy_action}: {policy_result.reason}",
                timestamp=timestamp,
                allow_override=False,
                action_taken="alert",
            )

    def _is_enforcement_enabled(self) -> bool:
        """
        Check if enforcement mode is enabled.

        Enforcement requires:
        1. mode = "enforce" in config
        2. enforcement.enabled = true
        3. enforcement.consent_accepted = true

        Returns:
            True if enforcement is fully enabled, False otherwise
        """
        # Check mode
        if self.config.mode != "enforce":
            return False

        # Check enforcement configuration
        if not self.config.enforcement.enabled:
            return False

        if not self.config.enforcement.consent_accepted:
            logger.error(
                "Enforcement enabled but consent not accepted! "
                "This should not happen - enforcement will not activate."
            )
            return False

        return True

    def _get_policy_action(self, policy_name: str) -> str:
        """
        Get the configured action for a specific policy.

        Args:
            policy_name: Name of the policy file (e.g., "bedtime.rego")

        Returns:
            Action string: "allow", "alert", or "block"
            Defaults to "alert" if not configured.
        """
        # Strip .rego extension if present
        policy_key = policy_name.replace(".rego", "")

        # Check if policy is configured
        if policy_key in self.config.policies.files:
            policy_config = self.config.policies.files[policy_key]
            if not policy_config.enabled:
                # Policy is disabled - treat as allow
                return "allow"
            return policy_config.action
        else:
            # Policy not configured - default to alert (safe default)
            logger.debug(f"Policy {policy_name} not in config, defaulting to 'alert'")
            return "alert"


def should_enforce_policy(
    request: dict,
    policy_result: PolicyResult,
    client_ip: str,
    config: Optional[YoriConfig] = None,
) -> EnforcementDecision:
    """
    Convenience function for enforcement decision.

    This is the main entry point used by the proxy.

    Args:
        request: Request being evaluated
        policy_result: Result from policy evaluation
        client_ip: Source IP
        config: Configuration (if None, loads from default location)

    Returns:
        EnforcementDecision
    """
    if config is None:
        config = YoriConfig.from_default_locations()

    engine = EnforcementEngine(config)
    return engine.should_enforce_policy(request, policy_result, client_ip)
