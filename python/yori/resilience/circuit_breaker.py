"""
YORI Circuit Breaker

Prevents cascade failures from upstream API outages using the circuit breaker pattern.
"""

import logging
from typing import Dict, Optional, Callable, Any
from enum import Enum
from datetime import datetime, timedelta
import httpx
from pybreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerError

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerMonitor(CircuitBreakerListener):
    """
    Listener to monitor circuit breaker state changes.
    Logs state transitions and tracks metrics.
    """

    def __init__(self, name: str):
        self.name = name
        self.state_changes: list = []
        self.failure_count = 0
        self.success_count = 0

    def before_call(self, cb, func, *args, **kwargs):
        """Called before attempting to call the protected function"""
        logger.debug(f"Circuit breaker '{self.name}' calling function")

    def state_change(self, cb, old_state, new_state):
        """Called when circuit breaker changes state"""
        timestamp = datetime.utcnow()
        self.state_changes.append((timestamp, old_state.name, new_state.name))

        logger.warning(
            f"Circuit breaker '{self.name}' changed state: "
            f"{old_state.name} -> {new_state.name} "
            f"(failures: {cb.fail_counter})"
        )

    def failure(self, cb, exc):
        """Called when a call fails"""
        self.failure_count += 1
        logger.warning(
            f"Circuit breaker '{self.name}' recorded failure: {type(exc).__name__}: {exc} "
            f"(total failures: {self.failure_count})"
        )

    def success(self, cb):
        """Called when a call succeeds"""
        self.success_count += 1
        logger.debug(
            f"Circuit breaker '{self.name}' recorded success "
            f"(total successes: {self.success_count})"
        )


class UpstreamCircuitBreakers:
    """
    Manages circuit breakers for upstream API calls.

    Each upstream endpoint (e.g., OpenAI, Anthropic) gets its own circuit breaker
    to isolate failures and prevent cascade failures.
    """

    def __init__(
        self,
        fail_max: int = 5,
        timeout_duration: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker manager.

        Args:
            fail_max: Number of consecutive failures before opening circuit (default: 5)
            timeout_duration: Seconds to wait before half-open attempt (default: 60)
            expected_exception: Exception type(s) that trigger circuit breaker
        """
        self.fail_max = fail_max
        self.timeout_duration = timeout_duration
        self.expected_exception = expected_exception

        # Registry of circuit breakers by name
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._monitors: Dict[str, CircuitBreakerMonitor] = {}

    def get_breaker(self, name: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a named endpoint.

        Args:
            name: Unique name for the circuit breaker (e.g., "openai", "anthropic")

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            # Create monitor for this breaker
            monitor = CircuitBreakerMonitor(name)
            self._monitors[name] = monitor

            # Create circuit breaker
            # Note: pybreaker catches all exceptions by default
            # We can filter using exclude_exception if needed
            breaker = CircuitBreaker(
                fail_max=self.fail_max,
                reset_timeout=self.timeout_duration,
                name=name,
                listeners=[monitor],
            )

            self._breakers[name] = breaker
            logger.info(
                f"Created circuit breaker '{name}' "
                f"(fail_max={self.fail_max}, timeout={self.timeout_duration}s)"
            )

        return self._breakers[name]

    def get_state(self, name: str) -> CircuitState:
        """
        Get current state of a circuit breaker.

        Args:
            name: Circuit breaker name

        Returns:
            Current state (CLOSED, OPEN, or HALF_OPEN)
        """
        if name not in self._breakers:
            return CircuitState.CLOSED

        breaker = self._breakers[name]

        # pybreaker's current_state is a string
        if isinstance(breaker.current_state, str):
            state_name = breaker.current_state.lower()
        else:
            state_name = breaker.current_state.name.lower()

        # Map pybreaker states to our enum
        if state_name == "closed":
            return CircuitState.CLOSED
        elif state_name == "open":
            return CircuitState.OPEN
        elif state_name == "half-open" or state_name == "half_open":
            return CircuitState.HALF_OPEN
        else:
            return CircuitState.CLOSED

    def get_stats(self, name: str) -> Dict[str, Any]:
        """
        Get statistics for a circuit breaker.

        Args:
            name: Circuit breaker name

        Returns:
            Dictionary with statistics
        """
        if name not in self._breakers:
            return {
                "exists": False,
                "state": "closed",
                "failure_count": 0,
                "success_count": 0,
            }

        breaker = self._breakers[name]
        monitor = self._monitors[name]

        return {
            "exists": True,
            "name": name,
            "state": self.get_state(name).value,
            "fail_counter": breaker.fail_counter,
            "failure_count": monitor.failure_count,
            "success_count": monitor.success_count,
            "state_changes": monitor.state_changes,
            "last_failure": getattr(breaker, "_last_failure_time", None),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all circuit breakers.

        Returns:
            Dictionary mapping breaker names to their stats
        """
        return {name: self.get_stats(name) for name in self._breakers.keys()}

    def reset(self, name: str):
        """
        Reset a circuit breaker to closed state.

        Args:
            name: Circuit breaker name
        """
        if name in self._breakers:
            # pybreaker uses .close() not .reset()
            self._breakers[name].close()
            logger.info(f"Circuit breaker '{name}' reset to closed state")

    def reset_all(self):
        """Reset all circuit breakers to closed state."""
        for name in self._breakers.keys():
            self.reset(name)


# Global circuit breaker manager
_global_breakers: Optional[UpstreamCircuitBreakers] = None


def get_circuit_breakers() -> UpstreamCircuitBreakers:
    """Get or create global circuit breaker manager."""
    global _global_breakers
    if _global_breakers is None:
        # Default to httpx exceptions that should trigger circuit breaker
        _global_breakers = UpstreamCircuitBreakers(
            fail_max=5,
            timeout_duration=60,
            expected_exception=(
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
            ),
        )
    return _global_breakers


async def call_with_circuit_breaker(
    endpoint: str,
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    """
    Call a function protected by a circuit breaker.

    Note: Currently pybreaker doesn't properly track failures for async functions
    since exceptions are raised during await, not during the breaker.call().
    For production use, consider using aiobreaker or implementing custom async support.

    Args:
        endpoint: Name of the endpoint (circuit breaker name)
        func: Function to call (async or sync)
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Raises:
        CircuitBreakerError: If circuit is open
        Original exception: If func fails
    """
    breakers = get_circuit_breakers()
    breaker = breakers.get_breaker(endpoint)

    # Call the function through the circuit breaker
    result = breaker.call(func, *args, **kwargs)

    # If it's a coroutine, await it
    # Note: Failures during await won't be tracked by pybreaker
    if hasattr(result, "__await__"):
        result = await result

    return result
