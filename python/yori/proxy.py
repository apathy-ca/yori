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
import json

from yori.config import YoriConfig
from yori.policy import get_evaluator, PolicyResult
from yori.alerts import get_alert_manager

logger = logging.getLogger(__name__)


class ProxyServer:
    """YORI transparent proxy server"""

    def __init__(self, config: YoriConfig):
        self.config = config
        self.app = FastAPI(
            title="YORI LLM Gateway",
            description="Zero-trust LLM governance for home networks",
            version="0.1.0",
        )
        self._setup_routes()
        self._client: Optional[httpx.AsyncClient] = None
        self._policy_evaluator = None
        self._alert_manager = None

    def _setup_routes(self):
        """Set up proxy routes"""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "mode": self.config.mode,
                "endpoints": len(self.config.endpoints),
            }

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_request(request: Request, path: str):
            """Proxy all requests to real LLM endpoints"""
            # 1. Extract request details
            client_host = request.client.host if request.client else "unknown"
            body = await request.body()

            try:
                body_json = json.loads(body) if body else {}
            except json.JSONDecodeError:
                body_json = {}

            # Extract prompt/messages for policy evaluation
            prompt = body_json.get("prompt", "")
            messages = body_json.get("messages", [])

            # 2. Evaluate policy
            request_data = {
                "user": client_host,  # Could be enhanced with auth
                "device": client_host,
                "endpoint": request.url.hostname or "unknown",
                "method": request.method,
                "path": path,
                "prompt": prompt,
                "messages": messages,
                "timestamp": datetime.utcnow().isoformat(),
                "hour": datetime.utcnow().hour,
            }

            policy_result = self._policy_evaluator.evaluate(request_data)

            logger.info(
                f"Policy evaluation: {policy_result.policy} - "
                f"{policy_result.mode} - {policy_result.reason}"
            )

            # 3. Send alerts if in advisory mode
            if policy_result.mode == "advisory":
                await self._alert_manager.send_alert(
                    user=client_host,
                    device=client_host,
                    policy=policy_result.policy,
                    reason=policy_result.reason,
                    mode=policy_result.mode,
                    metadata=policy_result.metadata,
                )

            # 4. Handle based on policy decision and mode
            if not policy_result.allow and policy_result.mode == "enforce":
                # Block request (enforce mode only)
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Request blocked by policy",
                        "policy": policy_result.policy,
                        "reason": policy_result.reason,
                    },
                )

            # 5. Forward to real endpoint (observe or advisory mode)
            # TODO: Implement actual forwarding in later phase
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Policy evaluation complete",
                    "policy": policy_result.policy,
                    "mode": policy_result.mode,
                    "allowed": policy_result.allow,
                    "reason": policy_result.reason,
                },
            )

    async def startup(self):
        """Initialize proxy server resources"""
        self._client = httpx.AsyncClient(timeout=30.0)
        self._policy_evaluator = get_evaluator()
        self._alert_manager = get_alert_manager()
        logger.info(f"YORI proxy server starting (mode: {self.config.mode})")

    async def shutdown(self):
        """Clean up proxy server resources"""
        if self._client:
            await self._client.aclose()
        logger.info("YORI proxy server shutting down")
