"""
YORI Proxy Server

FastAPI-based transparent proxy for LLM traffic interception.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
import logging
import time
from typing import Optional

from yori.config import YoriConfig
from yori.audit import AuditLogger
from yori.models import (
    AuditEvent,
    PolicyDecision,
    PolicyResult,
    OperationMode,
    LLMProvider,
)
from yori.detection import (
    detect_provider,
    get_target_url,
    extract_preview,
    is_llm_endpoint,
)
from yori.policy import PolicyEvaluator

logger = logging.getLogger(__name__)


class ProxyServer:
    """YORI transparent proxy server"""

    def __init__(self, config: YoriConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._audit_logger: Optional[AuditLogger] = None
        self._policy_evaluator: Optional[PolicyEvaluator] = None
        self._start_time = time.time()

        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.startup()
            yield
            # Shutdown
            await self.shutdown()

        self.app = FastAPI(
            title="YORI LLM Gateway",
            description="Zero-trust LLM governance for home networks",
            version="0.1.0",
            lifespan=lifespan,
        )
        self._setup_routes()

    def _setup_routes(self):
        """Set up proxy routes"""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "version": "0.1.0",
                "mode": self.config.mode,
                "endpoints": len(self.config.endpoints),
                "uptime_seconds": time.time() - self._start_time,
            }

        @self.app.get("/api/stats")
        async def get_stats():
            """Get statistics for dashboard"""
            if not self._audit_logger:
                return JSONResponse(
                    status_code=503,
                    content={"error": "Audit logger not initialized"},
                )

            stats = await self._audit_logger.get_stats()
            return stats.model_dump(mode="json")

        @self.app.get("/api/audit")
        async def get_audit_logs(
            limit: int = 100,
            offset: int = 0,
            provider: Optional[str] = None,
            decision: Optional[str] = None,
        ):
            """Get paginated audit logs"""
            if not self._audit_logger:
                return JSONResponse(
                    status_code=503,
                    content={"error": "Audit logger not initialized"},
                )

            events = await self._audit_logger.get_events(
                limit=limit,
                offset=offset,
                provider=provider,
                decision=decision,
            )
            return [event.model_dump(mode="json") for event in events]

        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_request(request: Request, path: str):
            """Proxy all requests to real LLM endpoints"""
            return await self._handle_proxy_request(request, path)

    async def _handle_proxy_request(self, request: Request, path: str) -> Response:
        """
        Handle transparent proxy request.

        This is the core proxy logic that:
        1. Extracts request details
        2. Evaluates policy
        3. Logs to audit database
        4. Forwards to real endpoint (if allowed)
        5. Returns response
        """
        start_time = time.time()

        # Extract request details
        host = request.headers.get("host", "unknown")
        method = request.method
        source_ip = request.client.host if request.client else "unknown"

        # Read request body
        body = await request.body()

        # Detect LLM provider
        provider = detect_provider(host, f"/{path}")

        # Check if endpoint is enabled
        if not self._is_endpoint_enabled(host):
            logger.warning(f"Request to disabled endpoint: {host}")
            await self._log_blocked_request(
                source_ip, host, path, provider, method, body, start_time, "Endpoint disabled"
            )
            return JSONResponse(
                status_code=403,
                content={"error": "Endpoint not enabled in YORI configuration"},
            )

        # Evaluate policy
        policy_result = await self._evaluate_policy(
            source_ip=source_ip,
            host=host,
            path=path,
            method=method,
            body=body,
            provider=provider,
        )

        # Handle policy decision based on mode
        should_block = self._should_block_request(policy_result)

        if should_block:
            await self._log_blocked_request(
                source_ip,
                host,
                path,
                provider,
                method,
                body,
                start_time,
                policy_result.reason or "Policy violation",
                policy_result,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Request blocked by policy",
                    "policy": policy_result.policy_name,
                    "reason": policy_result.reason,
                    "mode": self.config.mode,
                },
            )

        # Forward request to real endpoint
        try:
            target_url = get_target_url(provider, host, f"/{path}")

            # Copy headers (exclude host and content-length)
            headers = dict(request.headers)
            headers.pop("host", None)
            headers.pop("content-length", None)

            # Forward request
            response = await self._client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
            )

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Log successful request
            await self._log_successful_request(
                source_ip,
                host,
                path,
                provider,
                method,
                body,
                response.content,
                response.status_code,
                latency_ms,
                policy_result,
            )

            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            latency_ms = (time.time() - start_time) * 1000

            # Log error
            await self._log_error_request(
                source_ip, host, path, provider, method, body, latency_ms, str(e), policy_result
            )

            return JSONResponse(
                status_code=502,
                content={"error": "Failed to forward request to LLM endpoint"},
            )

    def _is_endpoint_enabled(self, host: str) -> bool:
        """Check if endpoint is enabled in configuration"""
        host_clean = host.split(":")[0].lower()

        for endpoint in self.config.endpoints:
            if endpoint.domain.lower() in host_clean or host_clean in endpoint.domain.lower():
                return endpoint.enabled

        # If not explicitly configured, allow by default in observe mode
        return self.config.mode == "observe"

    async def _evaluate_policy(
        self,
        source_ip: str,
        host: str,
        path: str,
        method: str,
        body: bytes,
        provider: LLMProvider,
    ) -> PolicyResult:
        """Evaluate policy for request"""
        if not self._policy_evaluator:
            # No policy evaluator, allow by default
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                policy_name="default",
                reason="No policy evaluator configured",
            )

        return await self._policy_evaluator.evaluate(
            source_ip=source_ip,
            host=host,
            path=path,
            method=method,
            body=body,
            provider=provider,
        )

    def _should_block_request(self, policy_result: PolicyResult) -> bool:
        """Determine if request should be blocked based on mode and policy decision"""
        # In observe mode, never block
        if self.config.mode == "observe":
            return False

        # In advisory mode, never block (just log alerts)
        if self.config.mode == "advisory":
            return False

        # In enforce mode, block on BLOCK decision
        if self.config.mode == "enforce":
            return policy_result.decision == PolicyDecision.BLOCK

        return False

    async def _log_successful_request(
        self,
        source_ip: str,
        host: str,
        path: str,
        provider: LLMProvider,
        method: str,
        request_body: bytes,
        response_body: bytes,
        status_code: int,
        latency_ms: float,
        policy_result: PolicyResult,
    ):
        """Log successful request to audit database"""
        if not self._audit_logger:
            return

        event = AuditEvent(
            source_ip=source_ip,
            destination=host,
            endpoint=f"/{path}",
            provider=provider,
            method=method,
            request_preview=extract_preview(request_body, max_length=200),
            response_preview=extract_preview(response_body, max_length=200),
            status_code=status_code,
            policy_decision=policy_result.decision,
            policy_name=policy_result.policy_name,
            mode=OperationMode(self.config.mode),
            latency_ms=latency_ms,
        )

        await self._audit_logger.log_event(event)

    async def _log_blocked_request(
        self,
        source_ip: str,
        host: str,
        path: str,
        provider: LLMProvider,
        method: str,
        request_body: bytes,
        start_time: float,
        error: str,
        policy_result: Optional[PolicyResult] = None,
    ):
        """Log blocked request to audit database"""
        if not self._audit_logger:
            return

        latency_ms = (time.time() - start_time) * 1000

        event = AuditEvent(
            source_ip=source_ip,
            destination=host,
            endpoint=f"/{path}",
            provider=provider,
            method=method,
            request_preview=extract_preview(request_body, max_length=200),
            status_code=403,
            policy_decision=(
                policy_result.decision if policy_result else PolicyDecision.BLOCK
            ),
            policy_name=policy_result.policy_name if policy_result else "default",
            mode=OperationMode(self.config.mode),
            latency_ms=latency_ms,
            error=error,
        )

        await self._audit_logger.log_event(event)

    async def _log_error_request(
        self,
        source_ip: str,
        host: str,
        path: str,
        provider: LLMProvider,
        method: str,
        request_body: bytes,
        latency_ms: float,
        error: str,
        policy_result: PolicyResult,
    ):
        """Log error request to audit database"""
        if not self._audit_logger:
            return

        event = AuditEvent(
            source_ip=source_ip,
            destination=host,
            endpoint=f"/{path}",
            provider=provider,
            method=method,
            request_preview=extract_preview(request_body, max_length=200),
            status_code=502,
            policy_decision=policy_result.decision,
            policy_name=policy_result.policy_name,
            mode=OperationMode(self.config.mode),
            latency_ms=latency_ms,
            error=error,
        )

        await self._audit_logger.log_event(event)

    async def startup(self):
        """Initialize proxy server resources"""
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

        # Initialize audit logger
        self._audit_logger = AuditLogger(self.config.audit.database)
        await self._audit_logger.initialize()

        # Initialize policy evaluator
        self._policy_evaluator = PolicyEvaluator(str(self.config.policies.directory))

        logger.info(f"YORI proxy server starting (mode: {self.config.mode})")

    async def shutdown(self):
        """Clean up proxy server resources"""
        if self._client:
            await self._client.aclose()
        logger.info("YORI proxy server shutting down")
