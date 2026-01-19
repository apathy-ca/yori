"""
Policy Evaluation for YORI

Integrates with Rust policy engine (yori_core) or provides mock evaluation.
"""

import logging
from typing import Optional

from yori.config import YoriConfig
from yori.models import PolicyDecision, PolicyResult, LLMProvider

logger = logging.getLogger(__name__)


class PolicyEvaluator:
    """
    Policy evaluator that integrates with Rust policy engine.

    Uses yori_core Python bindings when available, otherwise provides
    mock evaluation for development/testing.
    """

    def __init__(self, config: YoriConfig):
        self.config = config
        self._use_rust = False
        self._rust_evaluator = None

        # Try to import Rust policy engine
        try:
            from yori._core import PolicyEngine

            self._rust_evaluator = PolicyEngine(str(config.policies.directory))
            self._use_rust = True
            logger.info("Using Rust policy engine")
        except ImportError:
            logger.warning(
                "Rust policy engine not available, using mock evaluator. "
                "Install yori_core for real policy evaluation."
            )

    async def evaluate(
        self,
        source_ip: str,
        host: str,
        path: str,
        method: str,
        body: bytes,
        provider: LLMProvider,
    ) -> PolicyResult:
        """
        Evaluate policy for a request.

        Args:
            source_ip: Source IP address
            host: Destination host
            path: Request path
            method: HTTP method
            body: Request body
            provider: Detected LLM provider

        Returns:
            PolicyResult with decision
        """
        if self._use_rust and self._rust_evaluator:
            return await self._evaluate_rust(source_ip, host, path, method, body, provider)
        else:
            return await self._evaluate_mock(source_ip, host, path, method, body, provider)

    async def _evaluate_rust(
        self,
        source_ip: str,
        host: str,
        path: str,
        method: str,
        body: bytes,
        provider: LLMProvider,
    ) -> PolicyResult:
        """Evaluate using Rust policy engine"""
        # Prepare request data for Rust evaluator
        request_data = {
            "source_ip": source_ip,
            "destination": host,
            "path": path,
            "method": method,
            "provider": provider.value,
            "timestamp": None,  # Will be set by Rust
        }

        try:
            # Call Rust policy engine
            result = self._rust_evaluator.evaluate(request_data)

            # Convert Rust result to PolicyResult
            return PolicyResult(
                decision=PolicyDecision(result["decision"]),
                policy_name=result.get("policy_name", "unknown"),
                reason=result.get("reason"),
                metadata=result.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Rust policy evaluation failed: {e}")
            # Fall back to allow on error (fail open)
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                policy_name="error_fallback",
                reason=f"Policy evaluation error: {str(e)}",
            )

    async def _evaluate_mock(
        self,
        source_ip: str,
        host: str,
        path: str,
        method: str,
        body: bytes,
        provider: LLMProvider,
    ) -> PolicyResult:
        """
        Mock policy evaluator for development/testing.

        This implements simple rules for demonstration:
        - Block requests from specific test IPs
        - Alert on requests to unknown providers
        - Allow all others
        """
        # Example: Block requests from test IP
        if source_ip == "192.168.1.666":
            return PolicyResult(
                decision=PolicyDecision.BLOCK,
                policy_name="mock_block_test_ip",
                reason=f"Blocked test IP: {source_ip}",
            )

        # Example: Alert on unknown providers
        if provider == LLMProvider.UNKNOWN:
            return PolicyResult(
                decision=PolicyDecision.ALERT,
                policy_name="mock_unknown_provider",
                reason=f"Unknown LLM provider for host: {host}",
            )

        # Example: Check for sensitive keywords in request body (simple demo)
        if body:
            try:
                body_text = body.decode("utf-8", errors="ignore").lower()

                # Very basic content filtering (for demonstration only)
                sensitive_keywords = ["secret", "password", "apikey"]
                for keyword in sensitive_keywords:
                    if keyword in body_text:
                        return PolicyResult(
                            decision=PolicyDecision.ALERT,
                            policy_name="mock_sensitive_content",
                            reason=f"Request contains sensitive keyword: {keyword}",
                        )
            except Exception:
                pass

        # Default: allow
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            policy_name="mock_default_allow",
            reason="No policy violations detected",
        )
