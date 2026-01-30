"""
Tests for YORI Graceful Shutdown

Tests the graceful shutdown manager and request tracking.
"""

import asyncio
import pytest
import time
from yori.resilience.shutdown import GracefulShutdownManager


class TestGracefulShutdownManager:
    """Test suite for GracefulShutdownManager"""

    @pytest.fixture
    def manager(self):
        """Create a shutdown manager for testing"""
        return GracefulShutdownManager(timeout=5)

    def test_initial_state(self, manager):
        """Test initial state of shutdown manager"""
        assert not manager.is_shutting_down()
        assert manager.timeout == 5

    def test_request_shutdown(self, manager):
        """Test requesting shutdown"""
        manager.request_shutdown()
        assert manager.is_shutting_down()
        assert manager.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_register_unregister_request(self, manager):
        """Test registering and unregistering requests"""
        # Initially no requests
        assert await manager.get_in_flight_count() == 0

        # Register a request
        await manager.register_request("req-1")
        assert await manager.get_in_flight_count() == 1

        # Register another
        await manager.register_request("req-2")
        assert await manager.get_in_flight_count() == 2

        # Unregister one
        await manager.unregister_request("req-1")
        assert await manager.get_in_flight_count() == 1

        # Unregister the other
        await manager.unregister_request("req-2")
        assert await manager.get_in_flight_count() == 0

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self, manager):
        """Test unregistering a request that wasn't registered"""
        # Should not raise an error
        await manager.unregister_request("nonexistent")
        assert await manager.get_in_flight_count() == 0

    @pytest.mark.asyncio
    async def test_wait_for_requests_no_requests(self, manager):
        """Test waiting when there are no in-flight requests"""
        start_time = time.time()
        result = await manager.wait_for_requests()
        elapsed = time.time() - start_time

        assert result is True  # All completed
        assert elapsed < 1.0  # Should return immediately

    @pytest.mark.asyncio
    async def test_wait_for_requests_completes(self, manager):
        """Test waiting for requests that complete in time"""
        # Register a request
        await manager.register_request("req-1")

        # Simulate request completing after 1 second
        async def complete_request():
            await asyncio.sleep(1.0)
            await manager.unregister_request("req-1")

        # Start the completion task
        asyncio.create_task(complete_request())

        # Wait for requests to complete
        start_time = time.time()
        result = await manager.wait_for_requests()
        elapsed = time.time() - start_time

        assert result is True  # Completed successfully
        assert 0.9 < elapsed < 2.5  # Should take ~1 second (allow overhead)

    @pytest.mark.asyncio
    async def test_wait_for_requests_timeout(self, manager):
        """Test waiting for requests that don't complete in time"""
        # Register a request that won't complete
        await manager.register_request("req-stuck")

        # Wait should timeout
        start_time = time.time()
        result = await manager.wait_for_requests()
        elapsed = time.time() - start_time

        assert result is False  # Timed out
        assert 4.5 <= elapsed <= 6.0  # Should take ~5 seconds (timeout)
        assert await manager.get_in_flight_count() == 1  # Request still in-flight

    @pytest.mark.asyncio
    async def test_shutdown_sequence_no_requests(self, manager):
        """Test shutdown sequence with no in-flight requests"""
        cleanup_called = False

        async def cleanup_task():
            nonlocal cleanup_called
            cleanup_called = True

        result = await manager.shutdown_sequence([cleanup_task])

        assert result is True  # Clean shutdown
        assert cleanup_called is True  # Cleanup was called

    @pytest.mark.asyncio
    async def test_shutdown_sequence_with_completing_requests(self, manager):
        """Test shutdown sequence with requests that complete"""
        await manager.register_request("req-1")

        # Simulate request completing
        async def complete_request():
            await asyncio.sleep(0.5)
            await manager.unregister_request("req-1")

        asyncio.create_task(complete_request())

        # Run shutdown sequence
        result = await manager.shutdown_sequence()

        assert result is True  # Clean shutdown
        assert await manager.get_in_flight_count() == 0

    @pytest.mark.asyncio
    async def test_shutdown_sequence_with_timeout(self, manager):
        """Test shutdown sequence when requests don't complete in time"""
        # Create a manager with short timeout for faster test
        short_manager = GracefulShutdownManager(timeout=2)

        # Register a request that won't complete
        await short_manager.register_request("req-stuck")

        # Run shutdown sequence
        start_time = time.time()
        result = await short_manager.shutdown_sequence()
        elapsed = time.time() - start_time

        assert result is False  # Forced shutdown due to timeout
        assert await short_manager.get_in_flight_count() == 1  # Request still there

    @pytest.mark.asyncio
    async def test_shutdown_sequence_cleanup_errors(self, manager):
        """Test shutdown sequence handles cleanup errors gracefully"""
        cleanup_calls = []

        async def good_cleanup():
            cleanup_calls.append("good")

        async def bad_cleanup():
            cleanup_calls.append("bad")
            raise RuntimeError("Cleanup failed!")

        async def another_good_cleanup():
            cleanup_calls.append("another_good")

        # Cleanup should continue even if one fails
        result = await manager.shutdown_sequence([
            good_cleanup,
            bad_cleanup,
            another_good_cleanup,
        ])

        assert result is True  # Clean shutdown (no requests)
        assert cleanup_calls == ["good", "bad", "another_good"]

    @pytest.mark.asyncio
    async def test_multiple_requests_same_id(self, manager):
        """Test registering the same request ID multiple times"""
        # Registering same ID multiple times should work
        # (though it's not recommended in practice)
        await manager.register_request("req-1")
        await manager.register_request("req-1")

        # Should only count once (it's a set)
        assert await manager.get_in_flight_count() == 1

        # Unregister once
        await manager.unregister_request("req-1")

        # Should be gone
        assert await manager.get_in_flight_count() == 0

    @pytest.mark.asyncio
    async def test_register_during_shutdown(self, manager):
        """Test registering a request during shutdown"""
        # Request shutdown
        manager.request_shutdown()

        # Registering during shutdown should still work
        # (middleware will prevent new requests, but this tests the manager)
        await manager.register_request("req-late")
        assert await manager.get_in_flight_count() == 1


class TestShutdownIntegration:
    """Integration tests for shutdown with proxy server"""

    @pytest.mark.asyncio
    async def test_shutdown_manager_lifecycle(self):
        """Test full shutdown manager lifecycle"""
        manager = GracefulShutdownManager(timeout=10)

        # Simulate multiple requests starting and completing
        async def simulate_request(request_id, duration):
            await manager.register_request(request_id)
            await asyncio.sleep(duration)
            await manager.unregister_request(request_id)

        # Start several requests
        tasks = [
            asyncio.create_task(simulate_request("req-1", 0.5)),
            asyncio.create_task(simulate_request("req-2", 1.0)),
            asyncio.create_task(simulate_request("req-3", 1.5)),
        ]

        # Wait a bit for requests to start
        await asyncio.sleep(0.1)
        assert await manager.get_in_flight_count() == 3

        # Request shutdown
        manager.request_shutdown()

        # Wait for shutdown sequence
        result = await manager.shutdown_sequence()

        # All requests should complete
        assert result is True
        assert await manager.get_in_flight_count() == 0

        # All tasks should be done
        await asyncio.gather(*tasks)
