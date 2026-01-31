#!/usr/bin/env python3
"""
Baseline Performance Profiling for YORI Proxy

Measures:
- Requests per second (sustained throughput)
- Latency percentiles (p50, p95, p99)
- Memory usage (RSS, heap)
- Connection overhead
"""

import asyncio
import httpx
import time
import psutil
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
import json
import sys


@dataclass
class PerformanceMetrics:
    """Performance measurement results"""
    total_requests: int
    duration_seconds: float
    requests_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_avg_ms: float
    latency_min_ms: float
    latency_max_ms: float
    memory_start_mb: float
    memory_peak_mb: float
    memory_end_mb: float
    errors: int
    success_rate: float


async def measure_latency(client: httpx.AsyncClient, url: str, num_requests: int = 100) -> List[float]:
    """Measure request latency"""
    latencies = []

    for i in range(num_requests):
        start = time.perf_counter()
        try:
            response = await client.get(url)
            end = time.perf_counter()

            if response.status_code == 200:
                latencies.append((end - start) * 1000)  # Convert to ms
        except Exception as e:
            print(f"Request {i} failed: {e}")

    return latencies


async def measure_throughput(
    base_url: str,
    duration_seconds: int = 10,
    concurrency: int = 10
) -> PerformanceMetrics:
    """Measure sustained throughput with concurrent requests"""

    print(f"\n{'='*60}")
    print(f"Baseline Performance Profile")
    print(f"{'='*60}")
    print(f"Target URL: {base_url}")
    print(f"Duration: {duration_seconds}s")
    print(f"Concurrency: {concurrency} concurrent clients")
    print(f"{'='*60}\n")

    # Get current process for memory monitoring
    process = psutil.Process()
    memory_start = process.memory_info().rss / 1024 / 1024  # MB

    latencies = []
    errors = 0
    successful_requests = 0

    async def worker(client: httpx.AsyncClient, url: str, stop_time: float):
        """Worker that makes requests until stop_time"""
        nonlocal errors, successful_requests

        while time.time() < stop_time:
            start = time.perf_counter()
            try:
                response = await client.get(url)
                end = time.perf_counter()

                if response.status_code == 200:
                    latencies.append((end - start) * 1000)  # ms
                    successful_requests += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                end = time.perf_counter()

            # Small delay to prevent overwhelming the server
            await asyncio.sleep(0.01)

    # Create async client with connection pooling
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(max_connections=concurrency * 2)
    ) as client:
        # Warm up
        print("Warming up...")
        await measure_latency(client, f"{base_url}/health", num_requests=10)

        # Reset memory baseline after warmup
        memory_start = process.memory_info().rss / 1024 / 1024

        # Start monitoring
        print(f"Starting {duration_seconds}s throughput test...")
        start_time = time.time()
        stop_time = start_time + duration_seconds

        # Launch concurrent workers
        tasks = [
            worker(client, f"{base_url}/health", stop_time)
            for _ in range(concurrency)
        ]

        # Monitor memory during test
        memory_samples = []
        async def monitor_memory():
            while time.time() < stop_time:
                memory_samples.append(process.memory_info().rss / 1024 / 1024)
                await asyncio.sleep(0.5)

        # Run workers and memory monitor
        await asyncio.gather(monitor_memory(), *tasks)

        end_time = time.time()

    # Get final memory usage
    memory_end = process.memory_info().rss / 1024 / 1024
    memory_peak = max(memory_samples) if memory_samples else memory_end

    # Calculate metrics
    duration = end_time - start_time
    total_requests = successful_requests + errors
    rps = successful_requests / duration if duration > 0 else 0
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

    # Calculate latency percentiles
    if latencies:
        latencies_sorted = sorted(latencies)
        p50 = statistics.median(latencies_sorted)
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        avg = statistics.mean(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
    else:
        p50 = p95 = p99 = avg = min_lat = max_lat = 0.0

    return PerformanceMetrics(
        total_requests=total_requests,
        duration_seconds=duration,
        requests_per_second=rps,
        latency_p50_ms=p50,
        latency_p95_ms=p95,
        latency_p99_ms=p99,
        latency_avg_ms=avg,
        latency_min_ms=min_lat,
        latency_max_ms=max_lat,
        memory_start_mb=memory_start,
        memory_peak_mb=memory_peak,
        memory_end_mb=memory_end,
        errors=errors,
        success_rate=success_rate,
    )


def print_metrics(metrics: PerformanceMetrics, targets: Dict[str, Any] = None):
    """Print performance metrics in a formatted way"""

    if targets is None:
        targets = {
            'rps': 100,
            'latency_p99': 50,
            'memory_peak': 100,
        }

    print(f"\n{'='*60}")
    print("Performance Results")
    print(f"{'='*60}\n")

    # Throughput
    print("THROUGHPUT")
    print(f"  Total Requests: {metrics.total_requests}")
    print(f"  Duration: {metrics.duration_seconds:.2f}s")
    print(f"  Requests/sec: {metrics.requests_per_second:.2f}")
    rps_status = "✓ PASS" if metrics.requests_per_second >= targets['rps'] else "✗ FAIL"
    print(f"  Target: {targets['rps']} req/s [{rps_status}]")

    # Latency
    print(f"\nLATENCY (ms)")
    print(f"  Min: {metrics.latency_min_ms:.2f}")
    print(f"  Avg: {metrics.latency_avg_ms:.2f}")
    print(f"  p50: {metrics.latency_p50_ms:.2f}")
    print(f"  p95: {metrics.latency_p95_ms:.2f}")
    print(f"  p99: {metrics.latency_p99_ms:.2f}")
    print(f"  Max: {metrics.latency_max_ms:.2f}")
    lat_status = "✓ PASS" if metrics.latency_p99_ms <= targets['latency_p99'] else "✗ FAIL"
    print(f"  Target: <{targets['latency_p99']}ms p99 [{lat_status}]")

    # Memory
    print(f"\nMEMORY (MB)")
    print(f"  Start: {metrics.memory_start_mb:.2f}")
    print(f"  Peak: {metrics.memory_peak_mb:.2f}")
    print(f"  End: {metrics.memory_end_mb:.2f}")
    print(f"  Delta: {metrics.memory_end_mb - metrics.memory_start_mb:.2f}")
    mem_status = "✓ PASS" if metrics.memory_peak_mb <= targets['memory_peak'] else "✗ FAIL"
    print(f"  Target: <{targets['memory_peak']}MB peak [{mem_status}]")

    # Reliability
    print(f"\nRELIABILITY")
    print(f"  Successful: {metrics.total_requests - metrics.errors}")
    print(f"  Errors: {metrics.errors}")
    print(f"  Success Rate: {metrics.success_rate:.2f}%")

    print(f"\n{'='*60}\n")

    # Overall status
    all_pass = (
        metrics.requests_per_second >= targets['rps'] and
        metrics.latency_p99_ms <= targets['latency_p99'] and
        metrics.memory_peak_mb <= targets['memory_peak']
    )

    if all_pass:
        print("✓ ALL TARGETS MET")
    else:
        print("✗ SOME TARGETS NOT MET")
        if metrics.requests_per_second < targets['rps']:
            print(f"  - Throughput: {metrics.requests_per_second:.1f} < {targets['rps']} req/s")
        if metrics.latency_p99_ms > targets['latency_p99']:
            print(f"  - Latency: {metrics.latency_p99_ms:.1f} > {targets['latency_p99']}ms p99")
        if metrics.memory_peak_mb > targets['memory_peak']:
            print(f"  - Memory: {metrics.memory_peak_mb:.1f} > {targets['memory_peak']}MB")

    print()


async def main():
    """Run baseline performance profile"""

    # Configuration
    proxy_url = "http://localhost:8080"  # YORI proxy
    duration = 30  # seconds
    concurrency = 20  # concurrent clients

    # Performance targets
    targets = {
        'rps': 100,  # requests per second
        'latency_p99': 50,  # ms (proxy overhead only)
        'memory_peak': 100,  # MB
    }

    # Check if proxy is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{proxy_url}/health", timeout=2.0)
            if response.status_code != 200:
                print(f"ERROR: Proxy health check failed (status {response.status_code})")
                sys.exit(1)
    except Exception as e:
        print(f"ERROR: Cannot connect to proxy at {proxy_url}")
        print(f"Make sure the proxy is running first:")
        print(f"  python -m yori.proxy_server")
        sys.exit(1)

    # Run performance test
    metrics = await measure_throughput(
        base_url=proxy_url,
        duration_seconds=duration,
        concurrency=concurrency
    )

    # Print results
    print_metrics(metrics, targets)

    # Save results to file
    results_file = "performance_baseline.json"
    with open(results_file, "w") as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {
                'total_requests': metrics.total_requests,
                'duration_seconds': metrics.duration_seconds,
                'requests_per_second': metrics.requests_per_second,
                'latency_p50_ms': metrics.latency_p50_ms,
                'latency_p95_ms': metrics.latency_p95_ms,
                'latency_p99_ms': metrics.latency_p99_ms,
                'latency_avg_ms': metrics.latency_avg_ms,
                'memory_peak_mb': metrics.memory_peak_mb,
                'errors': metrics.errors,
                'success_rate': metrics.success_rate,
            },
            'targets': targets,
        }, f, indent=2)

    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
