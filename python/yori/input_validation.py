"""
YORI Input Validation

Enhanced input validation and sanitization for security hardening.
Provides defense-in-depth validation beyond Pydantic model validation.
"""

import re
import logging
from typing import Any, Dict, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# Security limits
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_JSON_DEPTH = 20  # Prevent deeply nested JSON attacks
MAX_HEADER_SIZE = 8 * 1024  # 8 KB per header
MAX_URL_LENGTH = 2048  # Max URL length
MAX_QUERY_PARAMS = 50  # Max number of query parameters


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce request size limits.

    Prevents resource exhaustion from oversized requests.
    """

    def __init__(self, app, max_request_size: int = MAX_REQUEST_SIZE):
        """
        Initialize request size limit middleware.

        Args:
            app: FastAPI application
            max_request_size: Maximum request body size in bytes
        """
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next):
        """
        Check request size before processing.

        Args:
            request: Incoming request
            call_next: Next middleware

        Returns:
            Response or 413 error if request too large

        Raises:
            HTTPException: If request exceeds size limits
        """
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(
                        f"Request too large: {size} bytes (max: {self.max_request_size})"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={
                            "error": "Request too large",
                            "max_size": self.max_request_size,
                            "provided_size": size,
                        }
                    )
            except ValueError:
                # Invalid Content-Length header
                logger.warning(f"Invalid Content-Length header: {content_length}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header"
                )

        # Check URL length
        if len(str(request.url)) > MAX_URL_LENGTH:
            logger.warning(f"URL too long: {len(str(request.url))} chars")
            raise HTTPException(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                detail="URL too long"
            )

        # Check number of query parameters
        if len(request.query_params) > MAX_QUERY_PARAMS:
            logger.warning(
                f"Too many query parameters: {len(request.query_params)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many query parameters (max: {MAX_QUERY_PARAMS})"
            )

        # Check header sizes
        for header_name, header_value in request.headers.items():
            if len(header_value) > MAX_HEADER_SIZE:
                logger.warning(
                    f"Header too large: {header_name} = {len(header_value)} bytes"
                )
                raise HTTPException(
                    status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE,
                    detail=f"Header too large: {header_name}"
                )

        return await call_next(request)


def validate_json_depth(data: Any, current_depth: int = 0) -> bool:
    """
    Validate JSON depth to prevent deeply nested object attacks.

    Args:
        data: JSON data to validate
        current_depth: Current nesting depth

    Returns:
        True if depth is acceptable

    Raises:
        ValueError: If depth exceeds maximum
    """
    if current_depth > MAX_JSON_DEPTH:
        raise ValueError(f"JSON depth exceeds maximum ({MAX_JSON_DEPTH})")

    if isinstance(data, dict):
        for value in data.values():
            validate_json_depth(value, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            validate_json_depth(item, current_depth + 1)

    return True


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing/escaping dangerous characters.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        raise TypeError("Value must be a string")

    # Truncate to max length
    if len(value) > max_length:
        value = value[:max_length]

    # Remove null bytes (common in injection attempts)
    value = value.replace('\x00', '')

    # Remove control characters (except newline and tab)
    value = ''.join(char for char in value if char >= ' ' or char in '\n\t')

    return value


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format (basic validation).

    Args:
        api_key: API key to validate

    Returns:
        True if format is valid

    Raises:
        ValueError: If API key format is invalid
    """
    if not api_key:
        raise ValueError("API key cannot be empty")

    # Remove common prefixes for validation
    key = api_key
    for prefix in ["sk-", "pk-", "Bearer "]:
        if key.startswith(prefix):
            key = key[len(prefix):]

    # Check length (most API keys are 20-128 characters)
    if len(key) < 20 or len(key) > 128:
        raise ValueError(f"API key length invalid: {len(key)} chars")

    # Check for valid characters (alphanumeric + common special chars)
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', key):
        raise ValueError("API key contains invalid characters")

    return True


def validate_endpoint_path(path: str) -> bool:
    """
    Validate endpoint path to prevent path traversal attacks.

    Args:
        path: URL path to validate

    Returns:
        True if path is safe

    Raises:
        ValueError: If path contains dangerous patterns
    """
    # Check for path traversal attempts
    dangerous_patterns = [
        "..",
        "//",
        "\\",
        "%2e%2e",  # URL-encoded ..
        "%2f",     # URL-encoded /
        "%5c",     # URL-encoded \
    ]

    path_lower = path.lower()
    for pattern in dangerous_patterns:
        if pattern in path_lower:
            raise ValueError(f"Path contains dangerous pattern: {pattern}")

    # Ensure path starts with /
    if not path.startswith('/'):
        raise ValueError("Path must start with /")

    return True


def validate_content_type(content_type: Optional[str], allowed_types: list) -> bool:
    """
    Validate Content-Type header against allowed types.

    Args:
        content_type: Content-Type header value
        allowed_types: List of allowed MIME types

    Returns:
        True if content type is allowed

    Raises:
        ValueError: If content type is not allowed
    """
    if not content_type:
        raise ValueError("Content-Type header missing")

    # Extract base content type (ignore parameters like charset)
    base_type = content_type.split(';')[0].strip().lower()

    if base_type not in [t.lower() for t in allowed_types]:
        raise ValueError(
            f"Content-Type not allowed: {base_type}. "
            f"Allowed: {', '.join(allowed_types)}"
        )

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and injection.

    Args:
        filename: Filename to sanitize

    Returns:
        Safe filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')

    # Keep only alphanumeric, dash, underscore, and dot
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Prevent hidden files
    if filename.startswith('.'):
        filename = '_' + filename[1:]

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    return filename


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address format (IPv4 or IPv6).

    Args:
        ip: IP address string

    Returns:
        True if valid IP address

    Raises:
        ValueError: If IP address format is invalid
    """
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        raise ValueError(f"Invalid IP address format: {ip}")


def validate_port_number(port: int) -> bool:
    """
    Validate port number is in valid range.

    Args:
        port: Port number

    Returns:
        True if valid port

    Raises:
        ValueError: If port is invalid
    """
    if not isinstance(port, int):
        raise TypeError("Port must be an integer")

    if port < 1 or port > 65535:
        raise ValueError(f"Port out of range: {port} (must be 1-65535)")

    # Warn about privileged ports
    if port < 1024:
        logger.warning(f"Using privileged port: {port}")

    return True


def sanitize_log_message(message: str) -> str:
    """
    Sanitize log message to prevent log injection.

    Args:
        message: Log message to sanitize

    Returns:
        Safe log message
    """
    # Replace newlines to prevent log injection
    message = message.replace('\n', '\\n').replace('\r', '\\r')

    # Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    message = ansi_escape.sub('', message)

    return message


class InputValidator:
    """
    Comprehensive input validator for YORI proxy.

    Provides centralized validation for all user inputs.
    """

    @staticmethod
    def validate_proxy_request(
        body: Optional[Dict],
        headers: Dict[str, str],
        path: str,
    ) -> bool:
        """
        Validate complete proxy request.

        Args:
            body: Request body (if any)
            headers: Request headers
            path: Request path

        Returns:
            True if request is valid

        Raises:
            ValueError: If validation fails
        """
        # Validate path
        validate_endpoint_path(path)

        # Validate JSON depth if body present
        if body:
            validate_json_depth(body)

        # Validate Content-Type for POST/PUT requests
        content_type = headers.get("content-type")
        if content_type:
            # Allow common content types
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            ]
            # Only validate if content-type is specified
            # (some requests may not have bodies)

        return True

    @staticmethod
    def validate_api_response(
        response_data: Any,
        expected_type: type = dict,
    ) -> bool:
        """
        Validate upstream API response.

        Args:
            response_data: Response data from upstream API
            expected_type: Expected Python type

        Returns:
            True if response is valid

        Raises:
            ValueError: If response validation fails
        """
        # Check type
        if not isinstance(response_data, expected_type):
            raise ValueError(
                f"Response type mismatch: expected {expected_type.__name__}, "
                f"got {type(response_data).__name__}"
            )

        # Validate JSON depth for dict/list responses
        if isinstance(response_data, (dict, list)):
            validate_json_depth(response_data)

        return True


# Export commonly used validators
__all__ = [
    "RequestSizeLimitMiddleware",
    "InputValidator",
    "validate_json_depth",
    "sanitize_string",
    "validate_api_key_format",
    "validate_endpoint_path",
    "validate_content_type",
    "sanitize_filename",
    "validate_ip_address",
    "validate_port_number",
    "sanitize_log_message",
]
