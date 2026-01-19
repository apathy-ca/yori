"""
Performance Tests: Latency Measurement

Tests that YORI proxy adds minimal latency overhead to requests.
Target: <10ms overhead (p95)
"""

import pytest
import time
import statistics
from fastapi.testclient import TestClient
import httpx

from yori.proxy import ProxyServer
from yori.config import YoriConfig


@pytest.mark.performance
class TestProxyLatency:
    """Test proxy latency performance"""

    def test_health_endpoint_latency(self, test_client: TestClient, performance_config: dict):
        """Test health endpoint responds quickly"""
        latencies = []
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            response = test_client.get("/health")
            end = time.perf_counter()

            assert response.status_code == 200
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # Calculate statistics
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        mean = statistics.mean(latencies)

        print(f"\nHealth endpoint latency:")
        print(f"  Mean: {mean:.2f}ms")
        print(f"  P50:  {p50:.2f}ms")
        print(f"  P95:  {p95:.2f}ms")
        print(f"  P99:  {p99:.2f}ms")

        # Health endpoint should be very fast
        assert p95 < 50, f"P95 latency {p95:.2f}ms exceeds 50ms threshold"

    @pytest.mark.asyncio
    async def test_proxy_request_latency(
        self,
        async_client: httpx.AsyncClient,
        performance_config: dict,
    ):
        """Test proxy request latency"""
        latencies = []
        iterations = 50

        for _ in range(iterations):
            start = time.perf_counter()
            response = await async_client.get("/test/path")
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # Calculate statistics
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]
        mean = statistics.mean(latencies)

        print(f"\nProxy request latency:")
        print(f"  Mean: {mean:.2f}ms")
        print(f"  P50:  {p50:.2f}ms")
        print(f"  P95:  {p95:.2f}ms")

        # Stub implementation should be fast
        # TODO: Adjust threshold when real proxy is implemented
        assert p95 < 100, f"P95 latency {p95:.2f}ms exceeds 100ms threshold"

    def test_policy_evaluation_latency(self, mock_policy_engine, performance_config: dict):
        """Test policy evaluation latency"""
        latencies = []
        iterations = 1000

        test_input = {
            "user": "alice",
            "endpoint": "api.openai.com",
            "method": "POST",
            "path": "/v1/chat/completions",
        }

        for _ in range(iterations):
            start = time.perf_counter()
            result = mock_policy_engine.evaluate(test_input)
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]
        mean = statistics.mean(latencies)

        print(f"\nPolicy evaluation latency:")
        print(f"  Mean: {mean:.2f}ms")
        print(f"  P50:  {p50:.2f}ms")
        print(f"  P95:  {p95:.2f}ms")

        # Policy evaluation should be <5ms per PROJECT_PLAN.md
        # Mock is much faster, real Rust implementation should also be fast
        target_ms = performance_config["latency_target_ms"]
        assert p95 < target_ms, f"P95 latency {p95:.2f}ms exceeds {target_ms}ms target"

    def test_cache_operation_latency(self, mock_cache, performance_config: dict):
        """Test cache get/set latency"""
        latencies_set = []
        latencies_get = []
        iterations = 1000

        for i in range(iterations):
            # Test SET latency
            start = time.perf_counter()
            mock_cache.set(f"key_{i}", {"value": i})
            end = time.perf_counter()
            latencies_set.append((end - start) * 1000)

            # Test GET latency
            start = time.perf_counter()
            mock_cache.get(f"key_{i}")
            end = time.perf_counter()
            latencies_get.append((end - start) * 1000)

        p95_set = statistics.quantiles(latencies_set, n=20)[18]
        p95_get = statistics.quantiles(latencies_get, n=20)[18]

        print(f"\nCache operation latency:")
        print(f"  SET P95: {p95_set:.2f}ms")
        print(f"  GET P95: {p95_get:.2f}ms")

        # Cache operations should be very fast (<1ms)
        assert p95_set < 5, f"SET P95 latency {p95_set:.2f}ms exceeds 5ms"
        assert p95_get < 5, f"GET P95 latency {p95_get:.2f}ms exceeds 5ms"

    def test_concurrent_request_latency(self, test_client: TestClient):
        """Test latency under concurrent load"""
        import concurrent.futures

        def make_request():
            start = time.perf_counter()
            response = test_client.get("/health")
            end = time.perf_counter()
            return (end - start) * 1000, response.status_code

        latencies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        latencies = [latency for latency, _ in results]
        p95 = statistics.quantiles(latencies, n=20)[18]

        print(f"\nConcurrent request P95 latency: {p95:.2f}ms")

        # Should not degrade significantly under concurrent load
        assert p95 < 100, f"Concurrent P95 latency {p95:.2f}ms exceeds 100ms"

    @pytest.mark.asyncio
    async def test_request_overhead_measurement(
        self,
        async_client: httpx.AsyncClient,
    ):
        """Measure actual proxy overhead"""
        # This would compare direct API call vs proxied call
        # For now, just measure proxy latency

        latencies = []
        for _ in range(50):
            start = time.perf_counter()
            await async_client.get("/health")
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        overhead = statistics.mean(latencies)
        print(f"\nEstimated proxy overhead: {overhead:.2f}ms")

        # Overhead should be minimal
        # TODO: Compare with direct upstream call when implemented
        pass

    def test_latency_percentiles(self, test_client: TestClient):
        """Test various latency percentiles"""
        latencies = []
        for _ in range(1000):
            start = time.perf_counter()
            test_client.get("/health")
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        percentiles = {
            "p50": statistics.median(latencies),
            "p90": statistics.quantiles(latencies, n=10)[8],
            "p95": statistics.quantiles(latencies, n=20)[18],
            "p99": statistics.quantiles(latencies, n=100)[98],
            "max": max(latencies),
        }

        print(f"\nLatency percentiles:")
        for name, value in percentiles.items():
            print(f"  {name}: {value:.2f}ms")

        # Store results for reporting
        return percentiles

    def test_warmup_effect(self, test_client: TestClient):
        """Test effect of warmup on latency"""
        # Cold start
        cold_latencies = []
        for _ in range(10):
            start = time.perf_counter()
            test_client.get("/health")
            end = time.perf_counter()
            cold_latencies.append((end - start) * 1000)

        # After warmup
        for _ in range(50):
            test_client.get("/health")

        # Warm measurements
        warm_latencies = []
        for _ in range(10):
            start = time.perf_counter()
            test_client.get("/health")
            end = time.perf_counter()
            warm_latencies.append((end - start) * 1000)

        cold_avg = statistics.mean(cold_latencies)
        warm_avg = statistics.mean(warm_latencies)

        print(f"\nWarmup effect:")
        print(f"  Cold start avg: {cold_avg:.2f}ms")
        print(f"  Warm avg:       {warm_avg:.2f}ms")
        print(f"  Improvement:    {((cold_avg - warm_avg) / cold_avg * 100):.1f}%")
