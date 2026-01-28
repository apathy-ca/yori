"""
YORI Proxy Server

FastAPI-based transparent proxy for LLM traffic interception.
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
import httpx
import logging
import uuid
import time
from typing import Optional
from datetime import datetime
from pathlib import Path

from yori.config import YoriConfig
from yori.models import PolicyResult, EnforcementDecision
from yori.enforcement import should_enforce_policy
from yori.consent import validate_enforcement_consent
from yori.block_page import render_block_page
from yori.audit_enforcement import EnforcementAuditLogger
from yori.proxy_handlers import create_block_response, get_body_preview
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
            version="0.2.0",
        )
        self._setup_routes()
        self._client: Optional[httpx.AsyncClient] = None

        # Initialize audit logger with error handling
        self.audit_logger: Optional[EnforcementAuditLogger] = None
        try:
            audit_db_path = self.config.audit.database
            self.audit_logger = EnforcementAuditLogger(audit_db_path)
            logger.info(f"Audit logger initialized: {audit_db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize audit logger: {e}")
            logger.warning("Proxy will continue without audit logging")

        # Validate consent on startup
        self._validate_consent_on_startup()

        # Register startup and shutdown events
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)

    def _setup_routes(self):
        """Set up proxy routes"""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "mode": self.config.mode,
                "endpoints": len(self.config.endpoints),
                "enforcement_enabled": self.config.enforcement.enabled if self.config.enforcement else False,
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
            # Start timing for audit logging
            start_time = time.time()

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

            # TODO Phase 1: Implement policy evaluation
            # For now, create a mock policy result for enforcement testing
            # In Phase 1, this will call yori_core.evaluate_policy()
            mock_policy_result = PolicyResult(
                allowed=True,  # This would come from policy evaluation
                policy_name="test_policy",
                reason="Mock policy result - Phase 1 will implement real evaluation",
                violations=[],
            )

            # Check enforcement decision (skip if override is valid)
            if not has_override:
                enforcement_decision = should_enforce_policy(
                    request={
                        "method": request.method,
                        "path": path,
                        "headers": dict(request.headers),
                        "body": request_data,
                    },
                    policy_result=mock_policy_result,
                    client_ip=client_ip,
                    config=self.config,
                )

                # If should enforce (block), return block page
                if enforcement_decision.should_block:
                    logger.warning(
                        f"BLOCKED request {request_id} from {client_ip} to {path}: "
                        f"{enforcement_decision.reason}"
                    )

                    # Log block event to audit database
                    if self.audit_logger:
                        try:
                            self.audit_logger.log_block(
                                client_ip=client_ip,
                                policy_name=mock_policy_result.policy_name,
                                reason=enforcement_decision.reason,
                                request_path=path,
                                request_method=request.method,
                                headers=dict(request.headers),
                                request_id=request_id,
                            )
                        except Exception as e:
                            logger.error(f"Failed to log block event: {e}")

                    # Return HTML block page
                    return await create_block_response(
                        request=request,
                        decision=enforcement_decision,
                        policy_name=mock_policy_result.policy_name,
                        request_id=request_id,
                    )

                # Log allowed status
                logger.info(
                    f"Request {request_id} from {client_ip} to {path}: {enforcement_decision.action_taken} "
                    f"(reason: {enforcement_decision.reason})"
                )

            # Forward request to upstream API
            try:
                # Determine upstream URL
                # For now, hardcode to OpenAI (will be configurable later)
                upstream_base = "https://api.openai.com"
                upstream_url = f"{upstream_base}/{path}"

                # Add query parameters if present
                if request.url.query:
                    upstream_url = f"{upstream_url}?{request.url.query}"

                # Log request event to audit database
                if self.audit_logger:
                    try:
                        self.audit_logger.log_request(
                            client_ip=client_ip,
                            request_path=path,
                            request_method=request.method,
                            upstream_host=upstream_base,
                            headers=dict(request.headers),
                            request_id=request_id,
                        )
                    except Exception as e:
                        logger.error(f"Failed to log request event: {e}")

                # Prepare headers (exclude hop-by-hop headers)
                forward_headers = dict(request.headers)
                # Remove headers that shouldn't be forwarded
                for header in ["host", "connection", "keep-alive", "transfer-encoding"]:
                    forward_headers.pop(header, None)

                # Forward the request
                logger.info(f"Forwarding request {request_id} to {upstream_url}")
                upstream_response = await self._client.request(
                    method=request.method,
                    url=upstream_url,
                    headers=forward_headers,
                    content=body,
                    timeout=30.0,
                )

                # Create response object
                response = Response(
                    content=upstream_response.content,
                    status_code=upstream_response.status_code,
                    headers=dict(upstream_response.headers),
                )

                # Log response event to audit database
                if self.audit_logger:
                    try:
                        duration_ms = (time.time() - start_time) * 1000
                        self.audit_logger.log_response(
                            client_ip=client_ip,
                            status_code=response.status_code,
                            duration_ms=duration_ms,
                            upstream_host=upstream_base,
                            request_path=path,
                            request_id=request_id,
                        )
                    except Exception as e:
                        logger.error(f"Failed to log response event: {e}")

                # Return upstream response to client
                return response

            except httpx.TimeoutException as e:
                logger.error(f"Timeout forwarding request {request_id}: {e}")
                return JSONResponse(
                    status_code=504,
                    content={
                        "error": "Gateway Timeout",
                        "message": "The upstream server did not respond in time",
                        "request_id": request_id,
                    },
                )
            except httpx.ConnectError as e:
                logger.error(f"Connection error forwarding request {request_id}: {e}")
                return JSONResponse(
                    status_code=502,
                    content={
                        "error": "Bad Gateway",
                        "message": "Could not connect to upstream server",
                        "request_id": request_id,
                    },
                )
            except Exception as e:
                logger.error(f"Error forwarding request {request_id}: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal Server Error",
                        "message": "An unexpected error occurred while forwarding the request",
                        "request_id": request_id,
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

        if self.config.enforcement and self.config.enforcement.enabled and self.config.enforcement.consent_accepted:
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
