"""
YORI Override Mechanism

Password-based override for policy blocks with rate limiting and audit logging.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class OverrideEvent:
    """Represents an override attempt for audit logging"""

    request_id: str
    client_ip: str
    policy_name: str
    password_hash: str  # For failed attempts (audit)
    success: bool
    timestamp: datetime
    emergency: bool = False


class RateLimiter:
    """Simple in-memory rate limiter for override attempts"""

    def __init__(self, max_attempts: int = 3, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_attempts: Maximum attempts allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, list] = {}

    def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if identifier is within rate limits.

        Args:
            identifier: Unique identifier (e.g., IP address)

        Returns:
            True if within limits, False if rate limited
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old attempts
        if identifier in self._attempts:
            self._attempts[identifier] = [
                ts for ts in self._attempts[identifier] if ts > cutoff
            ]
        else:
            self._attempts[identifier] = []

        # Check limit
        if len(self._attempts[identifier]) >= self.max_attempts:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        # Record attempt
        self._attempts[identifier].append(now)
        return True

    def reset(self, identifier: str) -> None:
        """
        Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier to reset
        """
        self._attempts.pop(identifier, None)


# Global rate limiter instance
_rate_limiter = RateLimiter(max_attempts=3, window_seconds=60)


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.

    Args:
        password: Plain text password

    Returns:
        Hash in format "sha256:hexdigest"
    """
    hash_obj = hashlib.sha256(password.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()}"


def validate_override_password(
    password: str,
    stored_hash: str
) -> bool:
    """
    Validate an override password against stored hash.

    Args:
        password: Plain text password to validate
        stored_hash: Stored password hash (format: "sha256:hexdigest")

    Returns:
        True if password is valid, False otherwise
    """
    if not stored_hash.startswith("sha256:"):
        logger.error(f"Invalid hash format: {stored_hash}")
        return False

    computed_hash = hash_password(password)
    return secrets.compare_digest(computed_hash, stored_hash)


def validate_emergency_override(
    token: str,
    admin_token_hash: str
) -> bool:
    """
    Validate an emergency override token (admin only).

    Args:
        token: Emergency override token
        admin_token_hash: Stored admin token hash

    Returns:
        True if token is valid, False otherwise
    """
    if not admin_token_hash.startswith("sha256:"):
        logger.error(f"Invalid admin token hash format")
        return False

    computed_hash = hash_password(token)
    return secrets.compare_digest(computed_hash, admin_token_hash)


def check_override_rate_limit(client_ip: str) -> bool:
    """
    Check if client is within override attempt rate limits.

    Args:
        client_ip: Client IP address

    Returns:
        True if within limits, False if rate limited
    """
    return _rate_limiter.check_rate_limit(client_ip)


def reset_override_rate_limit(client_ip: str) -> None:
    """
    Reset override rate limit for a client (e.g., after successful override).

    Args:
        client_ip: Client IP address
    """
    _rate_limiter.reset(client_ip)


def create_override_event(
    request_id: str,
    client_ip: str,
    policy_name: str,
    password: str,
    success: bool,
    emergency: bool = False
) -> OverrideEvent:
    """
    Create an override event for audit logging.

    Args:
        request_id: Unique request identifier
        client_ip: Client IP address
        policy_name: Name of the policy being overridden
        password: Password used (will be hashed for storage)
        success: Whether override was successful
        emergency: Whether this was an emergency override

    Returns:
        OverrideEvent instance
    """
    return OverrideEvent(
        request_id=request_id,
        client_ip=client_ip,
        policy_name=policy_name,
        password_hash=hash_password(password),
        success=success,
        timestamp=datetime.now(),
        emergency=emergency,
    )


def log_override_event(event: OverrideEvent) -> None:
    """
    Log an override event (placeholder for audit system integration).

    This will be integrated with the enhanced-audit worker (Worker 12).

    Args:
        event: Override event to log
    """
    event_type = "override_success" if event.success else "override_failed"
    if event.emergency:
        event_type = "emergency_override"

    logger.info(
        f"Override event: {event_type} | "
        f"request_id={event.request_id} | "
        f"client_ip={event.client_ip} | "
        f"policy={event.policy_name} | "
        f"timestamp={event.timestamp.isoformat()}"
    )

    # TODO: Integrate with audit database when Worker 12 is complete
    # from yori.audit import log_audit_event
    # log_audit_event(event_type, event)
