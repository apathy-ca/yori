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
from yori.cache import InMemoryCache, generate_policy_cache_key
from yori.csrf import CSRFMiddleware
from yori.rate_limit import RateLimitMiddleware
from yori.security_headers import SecurityHeadersMiddleware
from yori.input_validation import RequestSizeLimitMiddleware
from yori.override import (
    validate_override_password,
    validate_emergency_override,
    check_override_rate_limit,
    reset_override_rate_limit,
    create_override_event,
    log_override_event,
)
from yori import metrics
from yori.metrics_middleware import (
    MetricsMiddleware,
    record_upstream_request,
    record_upstream_error,
    record_enforcement_block,
    record_enforcement_allow,
    record_override_attempt,
    record_override_rate_limit,
    record_audit_log_write,
)
from yori.resilience.shutdown import GracefulShutdownManager

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

        # Add middlewares (order matters - outermost first)
        # Security headers (should be applied last, so added first)
        self.app.add_middleware(
            SecurityHeadersMiddleware,
            hsts_max_age=31536000,  # 1 year
            hsts_include_subdomains=True,
            hsts_preload=True,
        )

        # Request size limits (prevent resource exhaustion)
        self.app.add_middleware(
            RequestSizeLimitMiddleware,
            max_request_size=10 * 1024 * 1024,  # 10 MB
        )

        # Rate limiting to prevent abuse
        self.app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=60,  # TODO: Make configurable
            requests_per_hour=1000,
        )

        # CSRF protection for state-changing operations
        # TODO: Use a persistent secret key from config in production
        self.app.add_middleware(CSRFMiddleware)

        # Metrics middleware for observability
        self.app.add_middleware(MetricsMiddleware)

        self._setup_routes()
        self._client: Optional[httpx.AsyncClient] = None

        # Initialize shutdown manager
        self.shutdown_manager = GracefulShutdownManager(timeout=30)

        # Initialize audit logger with error handling
        self.audit_logger: Optional[EnforcementAuditLogger] = None
        try:
            audit_db_path = self.config.audit.database
            self.audit_logger = EnforcementAuditLogger(audit_db_path)
            logger.info(f"Audit logger initialized: {audit_db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize audit logger: {e}")
            logger.warning("Proxy will continue without audit logging")

        # Initialize policy evaluation cache
        # TTL = 60s for policy decisions (balance freshness vs. performance)
        # Max size = 1000 entries (sufficient for home network)
        self.policy_cache = InMemoryCache(default_ttl=60, max_size=1000)
        logger.info("Policy cache initialized: ttl=60s, max_size=1000")

        # Validate consent on startup
        self._validate_consent_on_startup()

        # Register startup and shutdown events
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)

        # Add request tracking middleware
        self.app.middleware("http")(self._request_tracking_middleware)

    def _setup_routes(self):
        """Set up proxy routes"""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint with component validation"""
            import time
            start_time = time.time()

            # Overall health status
            overall_healthy = True
            components = {}

            # Check proxy service
            components["proxy"] = {
                "status": "healthy",
                "message": "Proxy service is running",
            }
            metrics.health_status.labels(component="proxy").set(1)

            # Check upstream API connectivity
            upstream_healthy = False
            upstream_start = time.time()
            try:
                # Try to connect to upstream API
                if self._client:
                    # Simple HEAD request to check connectivity
                    upstream_response = await self._client.head(
                        "https://api.openai.com/",
                        timeout=5.0,
                    )
                    upstream_healthy = True
                    components["upstream_api"] = {
                        "status": "healthy",
                        "message": "Upstream API is reachable",
                        "host": "api.openai.com",
                    }
                    metrics.health_status.labels(component="upstream_api").set(1)
                else:
                    components["upstream_api"] = {
                        "status": "unhealthy",
                        "message": "HTTP client not initialized",
                    }
                    metrics.health_status.labels(component="upstream_api").set(0)
                    overall_healthy = False
            except httpx.TimeoutException:
                components["upstream_api"] = {
                    "status": "degraded",
                    "message": "Upstream API is slow to respond",
                    "host": "api.openai.com",
                }
                metrics.health_status.labels(component="upstream_api").set(0.5)
            except Exception as e:
                components["upstream_api"] = {
                    "status": "unhealthy",
                    "message": f"Cannot reach upstream API: {str(e)}",
                    "host": "api.openai.com",
                }
                metrics.health_status.labels(component="upstream_api").set(0)
                overall_healthy = False

            upstream_duration = time.time() - upstream_start
            metrics.health_check_duration_seconds.labels(component="upstream_api").observe(upstream_duration)

            # Check audit database
            audit_db_start = time.time()
            if self.audit_logger:
                try:
                    # Simple connectivity check (database exists)
                    db_path = self.config.audit.database
                    if db_path.exists():
                        components["audit_db"] = {
                            "status": "healthy",
                            "message": "Audit database is accessible",
                            "path": str(db_path),
                        }
                        metrics.health_status.labels(component="audit_db").set(1)

                        # Update audit DB size metric
                        try:
                            from yori.metrics_middleware import update_audit_db_size
                            db_size = db_path.stat().st_size
                            update_audit_db_size(db_size)
                        except Exception:
                            pass
                    else:
                        components["audit_db"] = {
                            "status": "unhealthy",
                            "message": "Audit database file not found",
                            "path": str(db_path),
                        }
                        metrics.health_status.labels(component="audit_db").set(0)
                        # Don't mark overall as unhealthy for missing audit DB
                except Exception as e:
                    components["audit_db"] = {
                        "status": "unhealthy",
                        "message": f"Audit database error: {str(e)}",
                    }
                    metrics.health_status.labels(component="audit_db").set(0)
            else:
                components["audit_db"] = {
                    "status": "disabled",
                    "message": "Audit logging is not configured",
                }
                # Don't set metric for disabled component

            audit_db_duration = time.time() - audit_db_start
            metrics.health_check_duration_seconds.labels(component="audit_db").observe(audit_db_duration)

            # Calculate total health check duration
            total_duration = time.time() - start_time

            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "mode": self.config.mode,
                "endpoints": len(self.config.endpoints),
                "enforcement_enabled": self.config.enforcement.enabled if self.config.enforcement else False,
                "cache": self.policy_cache.metrics(),
                "components": components,
                "check_duration_ms": round(total_duration * 1000, 2),
            }

        @self.app.get("/metrics")
        async def metrics_endpoint():
            """Prometheus metrics endpoint"""
            return Response(
                content=metrics.generate_metrics(),
                media_type=metrics.get_content_type(),
            )

        @self.app.post("/yori/override")
        async def handle_override(request: Request):
            """Handle override password submission"""
            client_ip = request.client.host if request.client else "unknown"

            # Check rate limiting
            if not check_override_rate_limit(client_ip):
                record_override_rate_limit()
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

                    # Record metric
                    record_override_attempt(success=True, emergency=True)

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

                # Record metric
                record_override_attempt(success=True, emergency=False)

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

            # Record metric
            record_override_attempt(success=False, emergency=emergency)

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
                # Generate cache key for policy decision
                cache_key = generate_policy_cache_key(
                    client_ip=client_ip,
                    request_path=path,
                    request_method=request.method,
                )

                # Check cache first
                cached_decision = self.policy_cache.get(cache_key)
                if cached_decision is not None:
                    enforcement_decision = cached_decision
                    logger.debug(f"Cache HIT for policy decision: {cache_key[:16]}...")
                else:
                    # Cache miss - evaluate policy
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

                    # Cache the decision for future requests
                    self.policy_cache.set(cache_key, enforcement_decision)
                    logger.debug(f"Cache MISS - stored policy decision: {cache_key[:16]}...")

                # If should enforce (block), return block page
                if enforcement_decision.should_block:
                    logger.warning(
                        f"BLOCKED request {request_id} from {client_ip} to {path}: "
                        f"{enforcement_decision.reason}"
                    )

                    # Record enforcement block metric
                    record_enforcement_block(
                        policy_name=mock_policy_result.policy_name,
                        reason=enforcement_decision.reason,
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
                            record_audit_log_write("block", True)
                        except Exception as e:
                            logger.error(f"Failed to log block event: {e}")
                            record_audit_log_write("block", False)

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

                # Record enforcement allow metric
                record_enforcement_allow(action=enforcement_decision.action_taken)

            # Forward request to upstream API
            try:
                # Determine upstream URL
                # For now, hardcode to OpenAI (will be configurable later)
                upstream_base = "https://api.openai.com"
                upstream_host = "api.openai.com"
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
                        record_audit_log_write("request", True)
                    except Exception as e:
                        logger.error(f"Failed to log request event: {e}")
                        record_audit_log_write("request", False)

                # Prepare headers (exclude hop-by-hop headers)
                forward_headers = dict(request.headers)
                # Remove headers that shouldn't be forwarded
                for header in ["host", "connection", "keep-alive", "transfer-encoding"]:
                    forward_headers.pop(header, None)

                # Forward the request
                logger.info(f"Forwarding request {request_id} to {upstream_url}")
                upstream_start_time = time.time()
                upstream_response = await self._client.request(
                    method=request.method,
                    url=upstream_url,
                    headers=forward_headers,
                    content=body,
                    timeout=30.0,
                )
                upstream_duration = time.time() - upstream_start_time

                # Record upstream metrics
                record_upstream_request(
                    host=upstream_host,
                    method=request.method,
                    status_code=upstream_response.status_code,
                    duration=upstream_duration,
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
                        record_audit_log_write("response", True)
                    except Exception as e:
                        logger.error(f"Failed to log response event: {e}")
                        record_audit_log_write("response", False)

                # Return upstream response to client
                return response

            except httpx.TimeoutException as e:
                logger.error(f"Timeout forwarding request {request_id}: {e}")
                record_upstream_error(upstream_host, "timeout")
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
                record_upstream_error(upstream_host, "connection_error")
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
                record_upstream_error(upstream_host, "unknown_error")
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

    async def _request_tracking_middleware(self, request: Request, call_next):
        """
        Middleware to track in-flight requests for graceful shutdown.
        """
        # Check if shutdown is in progress
        if self.shutdown_manager.is_shutting_down():
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "message": "Server is shutting down, not accepting new requests",
                },
            )

        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Register this request
        await self.shutdown_manager.register_request(request_id)

        try:
            # Process the request
            response = await call_next(request)
            return response
        finally:
            # Always unregister, even if request failed
            await self.shutdown_manager.unregister_request(request_id)

    async def startup(self):
        """Initialize proxy server resources"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(
                max_connections=100,           # Total concurrent connections
                max_keepalive_connections=20,  # Persistent connection pool
            ),
        )
        logger.info(f"YORI proxy server starting (mode: {self.config.mode})")
        logger.info("Connection pooling enabled: max_connections=100, keepalive=20")

        # Initialize metrics
        metrics.initialize_info_metrics(version="0.2.0", mode=self.config.mode)

    async def shutdown(self):
        """Clean up proxy server resources with graceful shutdown"""
        logger.info("Shutdown event triggered")

        # If shutdown wasn't already requested, request it now
        if not self.shutdown_manager.is_shutting_down():
            self.shutdown_manager.request_shutdown()

        # Define cleanup tasks
        async def close_http_client():
            """Close the HTTP client connection pool"""
            if self._client:
                await self._client.aclose()
                logger.info("HTTP client closed")

        async def close_audit_logger():
            """Close audit logger database connections"""
            if self.audit_logger:
                # Audit logger doesn't have async close, but we can log
                logger.info("Audit logger connections will be closed")

        # Execute graceful shutdown sequence
        cleanup_callbacks = [close_http_client, close_audit_logger]
        clean_exit = await self.shutdown_manager.shutdown_sequence(cleanup_callbacks)

        if clean_exit:
            logger.info("YORI proxy server shutdown complete (clean)")
        else:
            logger.warning("YORI proxy server shutdown complete (forced due to timeout)")
