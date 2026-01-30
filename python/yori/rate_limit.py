"""
YORI Rate Limiting

Rate limiting middleware to prevent abuse and DoS attacks.
Implements sliding window algorithm with per-IP and per-endpoint limits.
"""

import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from threading import Lock

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter implementation.

    Tracks request timestamps per client and enforces rate limits
    using a sliding time window approach.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        window_size: int = 60,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            requests_per_hour: Maximum requests allowed per hour
            window_size: Size of sliding window in seconds (default 60)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.window_size = window_size

        # Store request timestamps: {client_id: [(timestamp, endpoint), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)

        # Lock for thread-safe access
        self.lock = Lock()

    def _clean_old_requests(self, client_id: str, current_time: float) -> None:
        """
        Remove request records older than the sliding window.

        Args:
            client_id: Client identifier (IP address)
            current_time: Current timestamp
        """
        # Keep only requests within the last hour (for hourly limit)
        cutoff_time = current_time - 3600
        self.request_history[client_id] = [
            (ts, ep) for ts, ep in self.request_history[client_id]
            if ts > cutoff_time
        ]

    def check_rate_limit(
        self,
        client_id: str,
        endpoint: Optional[str] = None
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limits.

        Args:
            client_id: Client identifier (IP address)
            endpoint: Optional endpoint path for per-endpoint limits

        Returns:
            Tuple of (allowed, limits_info) where limits_info contains:
                - requests_remaining_minute
                - requests_remaining_hour
                - reset_time_minute
                - reset_time_hour
        """
        current_time = time.time()

        with self.lock:
            # Clean old requests
            self._clean_old_requests(client_id, current_time)

            # Get request history for this client
            history = self.request_history[client_id]

            # Count requests in the last minute
            minute_cutoff = current_time - 60
            minute_requests = [ts for ts, _ in history if ts > minute_cutoff]
            minute_count = len(minute_requests)

            # Count requests in the last hour
            hour_count = len(history)

            # Calculate remaining requests
            remaining_minute = max(0, self.requests_per_minute - minute_count)
            remaining_hour = max(0, self.requests_per_hour - hour_count)

            # Check if limits exceeded
            if minute_count >= self.requests_per_minute:
                logger.warning(
                    f"Rate limit exceeded (minute): {client_id} - {minute_count}/{self.requests_per_minute}"
                )
                return False, {
                    "requests_remaining_minute": 0,
                    "requests_remaining_hour": remaining_hour,
                    "reset_time_minute": int(minute_cutoff + 60),
                    "reset_time_hour": int(current_time - 3600 + 3600),
                }

            if hour_count >= self.requests_per_hour:
                logger.warning(
                    f"Rate limit exceeded (hour): {client_id} - {hour_count}/{self.requests_per_hour}"
                )
                return False, {
                    "requests_remaining_minute": remaining_minute,
                    "requests_remaining_hour": 0,
                    "reset_time_minute": int(minute_cutoff + 60),
                    "reset_time_hour": int(current_time - 3600 + 3600),
                }

            # Record this request
            self.request_history[client_id].append((current_time, endpoint or ""))

            return True, {
                "requests_remaining_minute": remaining_minute - 1,
                "requests_remaining_hour": remaining_hour - 1,
                "reset_time_minute": int(minute_cutoff + 60),
                "reset_time_hour": int(current_time - 3600 + 3600),
            }

    def get_client_stats(self, client_id: str) -> Dict[str, int]:
        """
        Get current rate limit statistics for a client.

        Args:
            client_id: Client identifier

        Returns:
            Dictionary with current request counts and limits
        """
        current_time = time.time()

        with self.lock:
            self._clean_old_requests(client_id, current_time)
            history = self.request_history[client_id]

            minute_cutoff = current_time - 60
            minute_count = len([ts for ts, _ in history if ts > minute_cutoff])
            hour_count = len(history)

            return {
                "minute_count": minute_count,
                "minute_limit": self.requests_per_minute,
                "hour_count": hour_count,
                "hour_limit": self.requests_per_hour,
            }

    def reset_client(self, client_id: str) -> None:
        """
        Reset rate limit counters for a client.

        Args:
            client_id: Client identifier
        """
        with self.lock:
            if client_id in self.request_history:
                del self.request_history[client_id]
                logger.info(f"Rate limit reset for client: {client_id}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Enforces per-IP rate limits on incoming requests.
    Returns 429 Too Many Requests when limits are exceeded.
    """

    # Endpoints exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/metrics"}

    # Stricter limits for specific endpoints
    ENDPOINT_LIMITS = {
        "/yori/override": (5, 20),  # 5/min, 20/hour - strict for override attempts
        "/v1/chat/completions": (30, 500),  # 30/min, 500/hour - moderate for API calls
    }

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Default max requests per minute
            requests_per_hour: Default max requests per hour
        """
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
        )

    def _get_client_id(self, request: Request) -> str:
        """
        Extract client identifier from request.

        Args:
            request: FastAPI request

        Returns:
            Client identifier (IP address)
        """
        # Try to get real IP from X-Forwarded-For header (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in the chain (original client)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Get direct client IP
            client_ip = request.client.host if request.client else "unknown"

        return client_ip

    def _get_endpoint_limits(self, path: str) -> Optional[Tuple[int, int]]:
        """
        Get rate limits for specific endpoint.

        Args:
            path: Request path

        Returns:
            Tuple of (requests_per_minute, requests_per_hour) or None for default
        """
        for endpoint, limits in self.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint):
                return limits
        return None

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or 429 error if rate limited

        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check for endpoint-specific limits
        endpoint_limits = self._get_endpoint_limits(request.url.path)
        if endpoint_limits:
            # Create temporary limiter for this endpoint
            endpoint_limiter = SlidingWindowRateLimiter(
                requests_per_minute=endpoint_limits[0],
                requests_per_hour=endpoint_limits[1],
            )
            allowed, limits_info = endpoint_limiter.check_rate_limit(
                client_id, request.url.path
            )
        else:
            # Use default limiter
            allowed, limits_info = self.limiter.check_rate_limit(
                client_id, request.url.path
            )

        if not allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path}"
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please slow down and try again later.",
                    "limits": limits_info,
                },
                headers={
                    "Retry-After": str(limits_info.get("reset_time_minute", 60)),
                    "X-RateLimit-Limit-Minute": str(self.limiter.requests_per_minute),
                    "X-RateLimit-Limit-Hour": str(self.limiter.requests_per_hour),
                    "X-RateLimit-Remaining-Minute": "0",
                    "X-RateLimit-Remaining-Hour": str(limits_info.get("requests_remaining_hour", 0)),
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)

        response.headers["X-RateLimit-Limit-Minute"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.limiter.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Minute"] = str(limits_info["requests_remaining_minute"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(limits_info["requests_remaining_hour"])

        return response


def get_rate_limit_stats(limiter: SlidingWindowRateLimiter, client_id: str) -> Dict[str, int]:
    """
    Get rate limit statistics for monitoring.

    Args:
        limiter: Rate limiter instance
        client_id: Client identifier

    Returns:
        Dictionary with rate limit statistics
    """
    return limiter.get_client_stats(client_id)
