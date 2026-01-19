"""
YORI Policy Evaluation

Python wrapper for policy evaluation using yori_core PolicyEngine.
Provides high-level interface for loading and evaluating Rego policies.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

try:
    import yori_core
except ImportError:
    # Fallback for development when Rust extension isn't built
    yori_core = None
    logging.warning("yori_core not available - policy evaluation will be stubbed")

logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
    """Result of a policy evaluation"""
    allow: bool
    policy: str
    reason: str
    mode: str  # observe, advisory, enforce
    metadata: Optional[Dict[str, Any]] = None


class PolicyEvaluator:
    """
    High-level policy evaluator for LLM requests.

    Wraps yori_core.PolicyEngine and provides a Python-friendly interface.
    """

    def __init__(self, policy_dir: str = "/usr/local/etc/yori/policies"):
        """
        Initialize policy evaluator.

        Args:
            policy_dir: Directory containing compiled .wasm policy files
        """
        self.policy_dir = Path(policy_dir)
        self.engine = None

        if yori_core:
            try:
                self.engine = yori_core.PolicyEngine(str(self.policy_dir))
                logger.info(f"Initialized policy engine with directory: {self.policy_dir}")
            except Exception as e:
                logger.error(f"Failed to initialize policy engine: {e}")
        else:
            logger.warning("Running without policy engine (yori_core not available)")

    def load_policies(self) -> int:
        """
        Load all policy files from the policy directory.

        Returns:
            Number of policies successfully loaded
        """
        if not self.engine:
            logger.warning("No policy engine available - using stub")
            return 0

        try:
            count = self.engine.load_policies()
            logger.info(f"Loaded {count} policies from {self.policy_dir}")
            return count
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
            return 0

    def list_policies(self) -> List[str]:
        """
        Get list of loaded policy names.

        Returns:
            List of policy names
        """
        if not self.engine:
            return []

        try:
            return self.engine.list_policies()
        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return []

    def evaluate(self, request_data: Dict[str, Any]) -> PolicyResult:
        """
        Evaluate a request against loaded policies.

        Args:
            request_data: Dictionary containing request context:
                - user: Username or device ID
                - device: Device identifier
                - endpoint: LLM endpoint (e.g., "api.openai.com")
                - method: HTTP method
                - path: Request path
                - prompt: User prompt text (optional)
                - messages: Chat messages (optional)
                - timestamp: ISO 8601 timestamp (optional)
                - hour: Hour of day 0-23 (optional)
                - request_count: Daily request count (optional)

        Returns:
            PolicyResult with decision
        """
        if not self.engine:
            # Stub behavior when engine not available
            return PolicyResult(
                allow=True,
                policy="stub",
                reason="Policy engine not available - defaulting to allow",
                mode="observe",
            )

        try:
            result_dict = self.engine.evaluate(request_data)
            return PolicyResult(
                allow=result_dict["allow"],
                policy=result_dict["policy"],
                reason=result_dict["reason"],
                mode=result_dict["mode"],
                metadata=result_dict.get("metadata"),
            )
        except Exception as e:
            logger.error(f"Policy evaluation error: {e}")
            # Fail open - allow request on error
            return PolicyResult(
                allow=True,
                policy="error",
                reason=f"Policy evaluation failed: {e}",
                mode="observe",
            )

    def test_policy(self, policy_name: str, test_data: Dict[str, Any]) -> PolicyResult:
        """
        Test a specific policy with sample data (dry run).

        Args:
            policy_name: Name of policy to test
            test_data: Sample input data

        Returns:
            PolicyResult from test evaluation
        """
        if not self.engine:
            return PolicyResult(
                allow=True,
                policy=policy_name,
                reason="Policy engine not available",
                mode="test",
            )

        try:
            result_dict = self.engine.test_policy(policy_name, test_data)
            return PolicyResult(
                allow=result_dict["allow"],
                policy=result_dict["policy"],
                reason=result_dict["reason"],
                mode=result_dict["mode"],
                metadata=result_dict.get("metadata"),
            )
        except Exception as e:
            logger.error(f"Policy test error: {e}")
            return PolicyResult(
                allow=True,
                policy=policy_name,
                reason=f"Test failed: {e}",
                mode="test",
            )


# Global policy evaluator instance
_evaluator: Optional[PolicyEvaluator] = None


def get_evaluator() -> PolicyEvaluator:
    """Get or create the global policy evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = PolicyEvaluator()
        _evaluator.load_policies()
    return _evaluator


def evaluate_request(request_data: Dict[str, Any]) -> PolicyResult:
    """
    Convenience function to evaluate a request using the global evaluator.

    Args:
        request_data: Request context dictionary

    Returns:
        PolicyResult
    """
    return get_evaluator().evaluate(request_data)
