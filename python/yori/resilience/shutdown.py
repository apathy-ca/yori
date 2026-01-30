"""
YORI Graceful Shutdown Manager

Handles graceful shutdown with in-flight request tracking and timeout.
"""

import asyncio
import logging
import signal
import time
from typing import Optional, Set
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to track request IDs
_request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class GracefulShutdownManager:
    """
    Manages graceful shutdown of the YORI proxy server.

    Tracks in-flight requests and ensures they complete before shutdown.
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize shutdown manager.

        Args:
            timeout: Maximum seconds to wait for in-flight requests (default: 30)
        """
        self.timeout = timeout
        self.shutdown_requested = False
        self.shutdown_event = asyncio.Event()
        self._in_flight_requests: Set[str] = set()
        self._lock = asyncio.Lock()
        self._shutdown_start_time: Optional[float] = None

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested

    def request_shutdown(self):
        """Request graceful shutdown."""
        if not self.shutdown_requested:
            self.shutdown_requested = True
            self._shutdown_start_time = time.time()
            self.shutdown_event.set()
            logger.info("Graceful shutdown requested")

    async def register_request(self, request_id: str):
        """
        Register an in-flight request.

        Args:
            request_id: Unique identifier for the request
        """
        if self.shutdown_requested:
            logger.warning(f"Request {request_id} started during shutdown")

        async with self._lock:
            self._in_flight_requests.add(request_id)
            logger.debug(f"Request {request_id} registered ({len(self._in_flight_requests)} in-flight)")

    async def unregister_request(self, request_id: str):
        """
        Unregister a completed request.

        Args:
            request_id: Unique identifier for the request
        """
        async with self._lock:
            self._in_flight_requests.discard(request_id)
            logger.debug(f"Request {request_id} completed ({len(self._in_flight_requests)} in-flight)")

    async def get_in_flight_count(self) -> int:
        """Get current count of in-flight requests."""
        async with self._lock:
            return len(self._in_flight_requests)

    async def wait_for_requests(self) -> bool:
        """
        Wait for all in-flight requests to complete.

        Returns:
            True if all requests completed, False if timeout occurred
        """
        wait_start = time.time()
        deadline = wait_start + self.timeout

        while time.time() < deadline:
            count = await self.get_in_flight_count()

            if count == 0:
                elapsed = time.time() - wait_start
                logger.info(f"All in-flight requests completed ({elapsed:.2f}s)")
                return True

            remaining_time = deadline - time.time()
            logger.info(
                f"Waiting for {count} in-flight requests "
                f"(timeout in {remaining_time:.1f}s)"
            )

            # Wait a bit before checking again
            await asyncio.sleep(1.0)

        # Timeout occurred
        count = await self.get_in_flight_count()
        logger.warning(
            f"Shutdown timeout reached with {count} in-flight requests remaining"
        )
        return False

    async def shutdown_sequence(self, cleanup_callbacks: Optional[list] = None):
        """
        Execute full graceful shutdown sequence.

        Args:
            cleanup_callbacks: Optional list of async cleanup functions to call

        Returns:
            True if clean shutdown, False if forced due to timeout
        """
        logger.info("=" * 60)
        logger.info("GRACEFUL SHUTDOWN SEQUENCE STARTED")
        logger.info("=" * 60)

        # Step 1: Stop accepting new requests (handled by caller setting shutdown flag)
        logger.info("Step 1/4: Stopped accepting new requests")

        # Step 2: Wait for in-flight requests (max timeout - 5s for cleanup)
        wait_timeout_seconds = max(self.timeout - 5, 10)
        logger.info(
            f"Step 2/4: Waiting for in-flight requests (max {wait_timeout_seconds}s)"
        )

        # Temporarily adjust our timeout for this wait
        original_timeout = self.timeout
        self.timeout = wait_timeout_seconds

        all_completed = await self.wait_for_requests()

        # Restore original timeout
        self.timeout = original_timeout

        if not all_completed:
            logger.warning("Some requests did not complete in time")

        # Step 3: Run cleanup callbacks
        if cleanup_callbacks:
            logger.info(f"Step 3/4: Running {len(cleanup_callbacks)} cleanup tasks")
            for callback in cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Cleanup callback failed: {e}", exc_info=True)
        else:
            logger.info("Step 3/4: No cleanup tasks registered")

        # Step 4: Final status
        logger.info("Step 4/4: Shutdown sequence complete")
        logger.info("=" * 60)

        return all_completed


# Global shutdown manager instance
_shutdown_manager: Optional[GracefulShutdownManager] = None


def get_shutdown_manager() -> GracefulShutdownManager:
    """Get or create global shutdown manager."""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdownManager()
    return _shutdown_manager


def setup_signal_handlers(shutdown_manager: GracefulShutdownManager):
    """
    Set up signal handlers for graceful shutdown.

    Args:
        shutdown_manager: Shutdown manager to notify on signals
    """

    def handle_signal(signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal")
        shutdown_manager.request_shutdown()

        # For SIGINT (Ctrl+C), we need to handle it specially
        # to prevent immediate exit
        if signum == signal.SIGINT:
            # Set shutdown flag but don't exit immediately
            # The main loop will handle graceful shutdown
            pass

    # Register handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("Signal handlers registered (SIGTERM, SIGINT)")
