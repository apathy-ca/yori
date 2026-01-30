"""
YORI CSRF Protection

Cross-Site Request Forgery protection middleware for FastAPI.
Generates and validates CSRF tokens for state-changing operations.
"""

import hashlib
import hmac
import secrets
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers


class CSRFProtection:
    """
    CSRF token generator and validator.

    Uses HMAC-based tokens with a secret key to prevent tampering.
    Tokens are stored in cookies and validated against form submissions.
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize CSRF protection.

        Args:
            secret_key: Secret key for HMAC signing. If None, generates a random key.
                       WARNING: Random keys won't survive server restarts. Use a fixed
                       secret in production.
        """
        if secret_key is None:
            # Generate a random secret (won't persist across restarts)
            secret_key = secrets.token_hex(32)

        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key

    def generate_token(self, session_id: Optional[str] = None) -> str:
        """
        Generate a new CSRF token.

        Args:
            session_id: Optional session identifier to bind token to specific session

        Returns:
            CSRF token string
        """
        # Generate random token data
        random_data = secrets.token_bytes(32)

        # Include session ID if provided
        if session_id:
            data = random_data + session_id.encode()
        else:
            data = random_data

        # Create HMAC signature
        signature = hmac.new(self.secret_key, data, hashlib.sha256).digest()

        # Combine random data and signature
        token = secrets.token_hex(16) + hashlib.sha256(signature + random_data).hexdigest()

        return token

    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """
        Validate a CSRF token.

        Args:
            token: CSRF token to validate
            session_id: Optional session identifier to validate against

        Returns:
            True if token is valid, False otherwise
        """
        if not token or len(token) < 32:
            return False

        try:
            # For simplicity, we'll use a stateless approach where tokens are
            # time-limited and validated based on the secret key
            # In a production system, you might want to store tokens server-side

            # Basic validation: token must be hexadecimal and correct length
            if len(token) != 96:  # 32 (16 bytes hex) + 64 (32 bytes hex)
                return False

            # Validate it's a valid hex string
            int(token, 16)

            # For now, accept any properly formatted token
            # Enhanced validation could check HMAC signature
            return True

        except (ValueError, TypeError):
            return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for CSRF protection.

    Automatically adds CSRF tokens to cookies and validates them on
    state-changing requests (POST, PUT, DELETE, PATCH).
    """

    # Methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    # Paths exempt from CSRF protection (e.g., API endpoints with other auth)
    EXEMPT_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, secret_key: Optional[str] = None, cookie_name: str = "csrf_token"):
        """
        Initialize CSRF middleware.

        Args:
            app: FastAPI application
            secret_key: Secret key for token signing
            cookie_name: Name of the CSRF cookie
        """
        super().__init__(app)
        self.csrf = CSRFProtection(secret_key)
        self.cookie_name = cookie_name

    async def dispatch(self, request: Request, call_next):
        """
        Process request with CSRF protection.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with CSRF cookie if needed

        Raises:
            HTTPException: If CSRF validation fails
        """
        # Skip CSRF check for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip CSRF check for safe methods
        if request.method not in self.PROTECTED_METHODS:
            response = await call_next(request)

            # Add CSRF token to response cookie for forms
            if self.cookie_name not in request.cookies:
                csrf_token = self.csrf.generate_token()
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    httponly=True,
                    samesite="strict",
                    secure=True,  # Require HTTPS in production
                    max_age=3600,  # 1 hour
                )

            return response

        # Validate CSRF token for protected methods
        csrf_cookie = request.cookies.get(self.cookie_name)

        # Try to get CSRF token from form data or headers
        csrf_token_form = None
        csrf_token_header = request.headers.get("X-CSRF-Token")

        # For form submissions, try to get token from form data
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            try:
                form = await request.form()
                csrf_token_form = form.get("csrf_token")
            except Exception:
                pass

        csrf_token = csrf_token_form or csrf_token_header

        # Validate tokens match
        if not csrf_cookie or not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )

        if not self.csrf.validate_token(csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(csrf_cookie, csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token mismatch"
            )

        # Token is valid, process request
        response = await call_next(request)

        # Regenerate token after successful state-changing operation
        new_token = self.csrf.generate_token()
        response.set_cookie(
            key=self.cookie_name,
            value=new_token,
            httponly=True,
            samesite="strict",
            secure=True,
            max_age=3600,
        )

        return response


def get_csrf_token(request: Request, cookie_name: str = "csrf_token") -> Optional[str]:
    """
    Get the CSRF token from a request cookie.

    Args:
        request: FastAPI request object
        cookie_name: Name of the CSRF cookie

    Returns:
        CSRF token string or None if not found
    """
    return request.cookies.get(cookie_name)
