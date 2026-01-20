"""
YORI Proxy Server

FastAPI-based transparent proxy for LLM traffic interception.
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
import httpx
import logging
import uuid
from typing import Optional
from datetime import datetime

from yori.config import YoriConfig
from yori.enforcement import should_enforce_policy, EnforcementDecision
from yori.block_page import render_block_page
from yori.override import (
    validate_override_password,
    validate_emergency_override,
    check_override_rate_limit,
    reset_override_rate_limit,
    create_override_event,
    log_override_event,
)

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

        @self.app.post("/yori/override")
        async def handle_override(request: Request):
            """Handle override password submission"""
            client_ip = request.client.host if request.client else "unknown"

            # Check rate limiting
            if not check_override_rate_limit(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "Too many override attempts. Please wait before trying again.",
                    },
                )

            # Parse request body
            try:
                body = await request.json()
                password = body.get("password", "")
                request_id = body.get("request_id", "")
                policy_name = body.get("policy_name", "")
                emergency = body.get("emergency", False)
            except Exception as e:
                logger.error(f"Failed to parse override request: {e}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "Invalid request format",
                    },
                )

            # Validate password
            if not self.config.enforcement.override_enabled:
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": "Override feature is disabled",
                    },
                )

            # Check emergency override first
            if emergency:
                admin_token_hash = self.config.enforcement.admin_token_hash
                if admin_token_hash and validate_emergency_override(password, admin_token_hash):
                    # Log successful emergency override
                    event = create_override_event(
                        request_id=request_id,
                        client_ip=client_ip,
                        policy_name=policy_name,
                        password=password,
                        success=True,
                        emergency=True,
                    )
                    log_override_event(event)
                    reset_override_rate_limit(client_ip)

                    return JSONResponse(
                        content={
                            "success": True,
                            "message": "Emergency override granted",
                        }
                    )

            # Check regular override password
            password_hash = self.config.enforcement.override_password_hash
            if password_hash and validate_override_password(password, password_hash):
                # Log successful override
                event = create_override_event(
                    request_id=request_id,
                    client_ip=client_ip,
                    policy_name=policy_name,
                    password=password,
                    success=True,
                    emergency=False,
                )
                log_override_event(event)
                reset_override_rate_limit(client_ip)

                return JSONResponse(
                    content={
                        "success": True,
                        "message": "Override successful",
                    }
                )

            # Log failed override
            event = create_override_event(
                request_id=request_id,
                client_ip=client_ip,
                policy_name=policy_name,
                password=password,
                success=False,
                emergency=emergency,
            )
            log_override_event(event)

            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Invalid override password",
                },
            )

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_request(request: Request, path: str):
            """Proxy all requests to real LLM endpoints"""
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            client_ip = request.client.host if request.client else "unknown"

            # Extract request body for policy evaluation
            try:
                body = await request.body()
                request_data = await request.json() if body else {}
            except Exception as e:
                logger.error(f"Failed to parse request body: {e}")
                request_data = {}

            # Check for override header (from successful override)
            override_password = request.headers.get("X-YORI-Override", "")
            has_override = False

            if override_password:
                password_hash = self.config.enforcement.override_password_hash
                admin_token_hash = self.config.enforcement.admin_token_hash

                # Check regular or emergency override
                if (password_hash and validate_override_password(override_password, password_hash)) or \
                   (admin_token_hash and validate_emergency_override(override_password, admin_token_hash)):
                    has_override = True
                    logger.info(f"Request {request_id} has valid override")

            # Evaluate policy (skip if override is valid)
            if not has_override and self.config.mode == "enforce":
                decision = should_enforce_policy(request_data)

                if decision.should_block:
                    # Set request ID for tracking
                    decision.request_id = request_id

                    # Render and return block page
                    html = render_block_page(decision)
                    logger.info(
                        f"Blocked request {request_id} by policy {decision.policy_name}: {decision.reason}"
                    )
                    return HTMLResponse(content=html, status_code=403)

            # Request is allowed - forward to real endpoint
            # TODO: Implement actual forwarding to LLM endpoint
            # This will be completed by upstream workers

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Request allowed (forwarding not yet implemented)",
                    "request_id": request_id,
                    "mode": self.config.mode,
                    "path": path,
                },
            )

    async def startup(self):
        """Initialize proxy server resources"""
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"YORI proxy server starting (mode: {self.config.mode})")

    async def shutdown(self):
        """Clean up proxy server resources"""
        if self._client:
            await self._client.aclose()
        logger.info("YORI proxy server shutting down")
