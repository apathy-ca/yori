"""
FastAPI middleware for automatic request/response instrumentation.

This middleware automatically tracks metrics for all HTTP requests
without requiring explicit instrumentation in handlers.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from yori import metrics

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically instrument HTTP requests with Prometheus metrics.

    Tracks:
    - Request count (by method, path, status code)
    - Request duration (by method, path)
    - Active requests
    - Request and response sizes
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request and record metrics"""

        # Skip metrics for the metrics endpoint itself to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        # Normalize path to avoid cardinality explosion
        normalized_path = metrics.normalize_path(request.url.path)

        # Increment active requests
        metrics.active_requests.inc()

        # Start timing
        start_time = time.time()

        # Get request size
        request_size = 0
        if request.headers.get("content-length"):
            try:
                request_size = int(request.headers["content-length"])
            except (ValueError, TypeError):
                pass

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Get response size
            response_size = 0
            if hasattr(response, "headers") and "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                except (ValueError, TypeError):
                    pass

            # Record metrics
            method = request.method
            status_code = str(response.status_code)

            # Request count
            metrics.requests_total.labels(
                method=method,
                path=normalized_path,
                status_code=status_code,
            ).inc()

            # Request duration
            metrics.request_duration_seconds.labels(
                method=method,
                path=normalized_path,
            ).observe(duration)

            # Request size
            if request_size > 0:
                metrics.request_size_bytes.labels(
                    method=method,
                    path=normalized_path,
                ).observe(request_size)

            # Response size
            if response_size > 0:
                metrics.response_size_bytes.labels(
                    path=normalized_path,
                    status_code=status_code,
                ).observe(response_size)

            return response

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time

            # Assume 500 error for exceptions
            metrics.requests_total.labels(
                method=request.method,
                path=normalized_path,
                status_code="500",
            ).inc()

            metrics.request_duration_seconds.labels(
                method=request.method,
                path=normalized_path,
            ).observe(duration)

            # Re-raise the exception
            raise

        finally:
            # Decrement active requests
            metrics.active_requests.dec()


def record_upstream_request(host: str, method: str, status_code: int, duration: float):
    """
    Record metrics for an upstream API request.

    Args:
        host: Upstream host (e.g., "api.openai.com")
        method: HTTP method
        status_code: Response status code
        duration: Request duration in seconds
    """
    metrics.upstream_requests_total.labels(
        host=host,
        status_code=str(status_code),
        method=method,
    ).inc()

    metrics.upstream_duration_seconds.labels(
        host=host,
        method=method,
    ).observe(duration)


def record_upstream_error(host: str, error_type: str):
    """
    Record an upstream API error.

    Args:
        host: Upstream host
        error_type: Type of error (timeout, connection_error, http_error, etc.)
    """
    metrics.upstream_errors_total.labels(
        host=host,
        error_type=error_type,
    ).inc()


def record_enforcement_block(policy_name: str, reason: str):
    """
    Record an enforcement block event.

    Args:
        policy_name: Name of the policy that triggered the block
        reason: Reason for the block
    """
    metrics.enforcement_blocks_total.labels(
        policy_name=policy_name,
        reason=reason,
    ).inc()


def record_enforcement_allow(action: str):
    """
    Record an enforcement allow event.

    Args:
        action: Action taken (allowed, allowlisted, consent_mode, etc.)
    """
    metrics.enforcement_allows_total.labels(
        action=action,
    ).inc()


def record_override_attempt(success: bool, emergency: bool):
    """
    Record an override attempt.

    Args:
        success: Whether the override was successful
        emergency: Whether it was an emergency override
    """
    metrics.override_attempts_total.labels(
        success=str(success).lower(),
        emergency=str(emergency).lower(),
    ).inc()


def record_override_rate_limit():
    """Record an override attempt rejected due to rate limiting."""
    metrics.override_rate_limits_total.inc()


def record_audit_log_write(event_type: str, success: bool):
    """
    Record an audit log write.

    Args:
        event_type: Type of event (block, request, response, override)
        success: Whether the write was successful
    """
    metrics.audit_log_writes_total.labels(
        event_type=event_type,
        success=str(success).lower(),
    ).inc()


def update_audit_db_size(size_bytes: int):
    """
    Update the audit database size metric.

    Args:
        size_bytes: Size of the audit database in bytes
    """
    metrics.audit_db_size_bytes.set(size_bytes)
