"""
YORI Proxy Server

FastAPI-based transparent proxy for LLM traffic interception.
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx
import logging
from typing import Optional
from datetime import datetime

from yori.config import YoriConfig
from yori.enforcement import EnforcementEngine, PolicyResult
from yori.consent import validate_enforcement_consent

logger = logging.getLogger(__name__)


class ProxyServer:
    """YORI transparent proxy server"""

    def __init__(self, config: YoriConfig):
        self.config = config
        self.enforcement_engine = EnforcementEngine(config)
        self.app = FastAPI(
            title="YORI LLM Gateway",
            description="Zero-trust LLM governance for home networks",
            version="0.1.0",
        )
        self._setup_routes()
        self._client: Optional[httpx.AsyncClient] = None

        # Validate consent on startup
        self._validate_consent_on_startup()

    def _setup_routes(self):
        """Set up proxy routes"""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "mode": self.config.mode,
                "endpoints": len(self.config.endpoints),
                "enforcement_enabled": self.enforcement_engine._is_enforcement_enabled(),
            }

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_request(request: Request, path: str):
            """Proxy all requests to real LLM endpoints"""
            client_ip = request.client.host if request.client else "unknown"

            # TODO Phase 1: Implement policy evaluation
            # For now, create a mock policy result for enforcement testing
            # In Phase 1, this will call yori_core.evaluate_policy()
            mock_policy_result = PolicyResult(
                action="alert",  # This would come from policy evaluation
                reason="Mock policy result - Phase 1 will implement real evaluation",
                policy_name="test_policy",
                metadata={"timestamp": datetime.now().isoformat()},
            )

            # Check enforcement decision
            enforcement_decision = self.enforcement_engine.should_enforce_policy(
                request={
                    "method": request.method,
                    "path": path,
                    "headers": dict(request.headers),
                },
                policy_result=mock_policy_result,
                client_ip=client_ip,
            )

            # If should block, return error response
            if enforcement_decision.should_block:
                logger.warning(
                    f"BLOCKED request from {client_ip} to {path}: "
                    f"{enforcement_decision.policy_name} - {enforcement_decision.reason}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Request blocked by YORI policy",
                        "policy": enforcement_decision.policy_name,
                        "reason": enforcement_decision.reason,
                        "timestamp": enforcement_decision.timestamp.isoformat(),
                        "can_override": enforcement_decision.allow_override,
                        "message": (
                            "This request was blocked by your YORI governance policy. "
                            "Contact your administrator if you believe this is an error."
                        ),
                    },
                )

            # TODO Phase 1: Forward to real endpoint if not blocked
            # For now, return a placeholder response
            logger.info(
                f"Request from {client_ip} to {path}: {enforcement_decision.action_taken} "
                f"(policy: {enforcement_decision.policy_name})"
            )

            return JSONResponse(
                status_code=501,
                content={
                    "error": "Proxy forwarding not yet implemented (Phase 1)",
                    "enforcement_status": {
                        "blocked": enforcement_decision.should_block,
                        "action": enforcement_decision.action_taken,
                        "policy": enforcement_decision.policy_name,
                    },
                    "mode": self.config.mode,
                    "path": path,
                },
            )

    def _validate_consent_on_startup(self):
        """Validate consent configuration on startup"""
        result = validate_enforcement_consent(self.config)

        if not result.valid:
            logger.error("=" * 80)
            logger.error("ENFORCEMENT MODE CONFIGURATION ERROR")
            logger.error("=" * 80)
            for error in result.errors:
                logger.error(f"  - {error.value}")
            logger.error("")
            logger.error("Enforcement mode will NOT be active due to consent errors.")
            logger.error("=" * 80)

        for warning in result.warnings:
            logger.warning(f"Configuration warning: {warning}")

        if self.enforcement_engine._is_enforcement_enabled():
            logger.warning("=" * 80)
            logger.warning("ENFORCEMENT MODE IS ACTIVE")
            logger.warning("Requests WILL be blocked based on policy configuration.")
            logger.warning("=" * 80)

    async def startup(self):
        """Initialize proxy server resources"""
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"YORI proxy server starting (mode: {self.config.mode})")

    async def shutdown(self):
        """Clean up proxy server resources"""
        if self._client:
            await self._client.aclose()
        logger.info("YORI proxy server shutting down")
