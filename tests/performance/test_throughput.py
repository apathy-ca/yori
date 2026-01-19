"""
Performance Tests: Throughput Testing

Tests that YORI can handle target throughput of 50 req/sec.
"""

import pytest
import time
import asyncio
from fastapi.testclient import TestClient
import httpx


@pytest.mark.performance
class TestProxyThroughput:
    """Test proxy throughput performance"""

    def test_synchronous_throughput(self, test_client: TestClient):
        """Test synchronous request throughput"""
        num_requests = 100
        start_time = time.perf_counter()

        for _ in range(num_requests):
            response = test_client.get("/health")
            assert response.status_code == 200

        end_time = time.perf_counter()
        duration = end_time - start_time
        throughput = num_requests / duration

        print(f"\nSynchronous throughput: {throughput:.2f} req/sec")
        print(f"Time for {num_requests} requests: {duration:.2f}s")

        # Should handle more than target of 50 req/sec
        assert throughput > 50, f"Throughput {throughput:.2f} req/sec below 50 req/sec target"

    @pytest.mark.asyncio
    async def test_async_throughput(self, async_client: httpx.AsyncClient):
        """Test asynchronous request throughput"""
        num_requests = 100

        async def make_request():
            response = await async_client.get("/health")
            return response.status_code

        start_time = time.perf_counter()
        tasks = [make_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()

        duration = end_time - start_time
        throughput = num_requests / duration

        print(f"\nAsync throughput: {throughput:.2f} req/sec")
        print(f"Time for {num_requests} concurrent requests: {duration:.2f}s")

        assert all(status == 200 for status in results)
        # Async should be much faster
        assert throughput > 100, f"Async throughput {throughput:.2f} req/sec unexpectedly low"

    @pytest.mark.asyncio
    async def test_sustained_load(self, async_client: httpx.AsyncClient, performance_config: dict):
        """Test sustained load over time"""
        duration_seconds = 10  # Shorter for testing
        requests_per_second = 50

        async def make_request():
            return await async_client.get("/health")

        start_time = time.perf_counter()
        total_requests = 0
        successful = 0

        while time.perf_counter() - start_time < duration_seconds:
            batch_start = time.perf_counter()

            # Send batch of requests
            tasks = [make_request() for _ in range(requests_per_second)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_requests += len(results)
            successful += sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)

            # Sleep to maintain target rate
            batch_duration = time.perf_counter() - batch_start
            if batch_duration < 1.0:
                await asyncio.sleep(1.0 - batch_duration)

        actual_duration = time.perf_counter() - start_time
        actual_throughput = total_requests / actual_duration
        success_rate = (successful / total_requests) * 100

        print(f"\nSustained load test:")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful: {successful}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Throughput: {actual_throughput:.2f} req/sec")

        assert success_rate > 95, f"Success rate {success_rate:.1f}% below 95%"
        assert actual_throughput >= 45, f"Throughput {actual_throughput:.2f} req/sec below target"

    def test_concurrent_clients(self, test_config):
        """Test multiple concurrent clients"""
        import concurrent.futures

        def client_worker(client_id, num_requests):
            client = TestClient(ProxyServer(test_config).app)
            successful = 0
            for _ in range(num_requests):
                try:
                    response = client.get("/health")
                    if response.status_code == 200:
                        successful += 1
                except Exception:
                    pass
            return successful

        num_clients = 5
        requests_per_client = 20

        start_time = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_clients) as executor:
            futures = [executor.submit(client_worker, i, requests_per_client) for i in range(num_clients)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        end_time = time.perf_counter()
        duration = end_time - start_time
        total_requests = num_clients * requests_per_client
        successful = sum(results)
        throughput = total_requests / duration

        print(f"\nConcurrent clients test:")
        print(f"  Clients: {num_clients}")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful: {successful}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} req/sec")

        assert successful == total_requests, f"Only {successful}/{total_requests} requests successful"


# Import late to avoid circular dependency
from yori.proxy import ProxyServer
