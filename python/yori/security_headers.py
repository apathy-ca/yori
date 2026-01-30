"""
YORI Security Headers

Middleware to add security headers to all HTTP responses.
Implements defense-in-depth security measures following OWASP best practices.
"""

import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for adding security headers.

    Adds comprehensive security headers to all responses including:
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection (legacy browsers)
    - Referrer-Policy
    - Permissions-Policy

    These headers provide defense-in-depth protection against common
    web vulnerabilities including XSS, clickjacking, and content sniffing.
    """

    def __init__(
        self,
        app,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        custom_csp: Optional[str] = None,
    ):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application
            hsts_max_age: HSTS max-age in seconds (default 1 year)
            hsts_include_subdomains: Include subdomains in HSTS
            hsts_preload: Enable HSTS preload
            custom_csp: Custom Content-Security-Policy (overrides default)
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.custom_csp = custom_csp

    def _get_hsts_header(self) -> str:
        """
        Build Strict-Transport-Security header value.

        Returns:
            HSTS header value
        """
        hsts = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts += "; includeSubDomains"
        if self.hsts_preload:
            hsts += "; preload"
        return hsts

    def _get_csp_header(self) -> str:
        """
        Build Content-Security-Policy header value.

        Returns:
            CSP header value
        """
        if self.custom_csp:
            return self.custom_csp

        # Default CSP for YORI proxy
        # Restrictive policy: only allow same-origin resources
        csp_directives = [
            "default-src 'self'",  # Only load resources from same origin
            "script-src 'self' 'unsafe-inline'",  # Allow inline scripts (needed for block page)
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles (needed for block page)
            "img-src 'self' data:",  # Allow images from same origin and data URIs
            "font-src 'self'",  # Only fonts from same origin
            "connect-src 'self'",  # Only XHR/fetch to same origin
            "frame-ancestors 'none'",  # Prevent framing (clickjacking protection)
            "base-uri 'self'",  # Restrict <base> tag to same origin
            "form-action 'self'",  # Only submit forms to same origin
            "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
        ]
        return "; ".join(csp_directives)

    def _get_permissions_policy_header(self) -> str:
        """
        Build Permissions-Policy header value.

        Disables unnecessary browser features to reduce attack surface.

        Returns:
            Permissions-Policy header value
        """
        # Disable all unnecessary features
        policies = [
            "accelerometer=()",
            "ambient-light-sensor=()",
            "autoplay=()",
            "battery=()",
            "camera=()",
            "cross-origin-isolated=()",
            "display-capture=()",
            "document-domain=()",
            "encrypted-media=()",
            "execution-while-not-rendered=()",
            "execution-while-out-of-viewport=()",
            "fullscreen=()",
            "geolocation=()",
            "gyroscope=()",
            "keyboard-map=()",
            "magnetometer=()",
            "microphone=()",
            "midi=()",
            "navigation-override=()",
            "payment=()",
            "picture-in-picture=()",
            "publickey-credentials-get=()",
            "screen-wake-lock=()",
            "sync-xhr=()",
            "usb=()",
            "web-share=()",
            "xr-spatial-tracking=()",
        ]
        return ", ".join(policies)

    def _get_security_headers(self) -> Dict[str, str]:
        """
        Get all security headers to add to responses.

        Returns:
            Dictionary of header name to value
        """
        return {
            # HSTS - Force HTTPS for all future requests
            "Strict-Transport-Security": self._get_hsts_header(),

            # CSP - Prevent XSS and other injection attacks
            "Content-Security-Policy": self._get_csp_header(),

            # Prevent clickjacking
            "X-Frame-Options": "DENY",

            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Enable XSS protection in legacy browsers
            # Note: Modern browsers rely on CSP instead
            "X-XSS-Protection": "1; mode=block",

            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Disable browser features
            "Permissions-Policy": self._get_permissions_policy_header(),

            # Indicate server type (optional, can be removed for security obscurity)
            "X-Content-Type-Options": "nosniff",

            # Remove server header fingerprinting (if possible)
            # Note: Some servers add this automatically
        }

    async def dispatch(self, request: Request, call_next):
        """
        Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with security headers added
        """
        # Process request
        response = await call_next(request)

        # Add all security headers
        security_headers = self._get_security_headers()
        for header_name, header_value in security_headers.items():
            # Don't override existing headers
            if header_name not in response.headers:
                response.headers[header_name] = header_value

        # Log security headers added (debug only)
        logger.debug(
            f"Security headers added to {request.url.path}: "
            f"{len(security_headers)} headers"
        )

        return response


def get_default_security_headers() -> Dict[str, str]:
    """
    Get default security headers for standalone use.

    Returns:
        Dictionary of default security headers
    """
    middleware = SecurityHeadersMiddleware(app=None)
    return middleware._get_security_headers()


def validate_csp(csp_policy: str) -> bool:
    """
    Validate Content-Security-Policy syntax.

    Args:
        csp_policy: CSP policy string to validate

    Returns:
        True if CSP appears valid, False otherwise
    """
    # Basic validation - check for required directives
    required_directives = ["default-src"]

    for directive in required_directives:
        if directive not in csp_policy:
            logger.warning(f"CSP missing required directive: {directive}")
            return False

    # Check for dangerous directives
    dangerous_patterns = ["'unsafe-eval'", "'unsafe-inline'"]
    for pattern in dangerous_patterns:
        if pattern in csp_policy:
            logger.warning(f"CSP contains potentially dangerous directive: {pattern}")
            # Not invalid, just warning

    return True
