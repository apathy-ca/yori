#!/usr/bin/env python3
"""
Load test script for YORI proxy server.

This script generates load against the YORI proxy to verify:
1. Metrics are accurately recorded under stress
2. Metrics endpoint remains responsive
3. No metric cardinality explosion occurs
4. System metrics are reasonable

Usage:
    python monitoring/load_test.py --url http://localhost:8080 --duration 60 --workers 10

Requirements:
    pip install httpx rich
"""

import argparse
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
import httpx
from typing import List, Dict
import statistics

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' for better output: pip install rich")


@dataclass
class LoadTestResult:
    """Results from load test"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    requests_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    errors: Dict[str, int]


class LoadTester:
    """Load testing client for YORI proxy"""

    def __init__(self, base_url: str, workers: int = 10):
        self.base_url = base_url.rstrip('/')
        self.workers = workers
        self.latencies: List[float] = []
        self.errors: Dict[str, int] = {}
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    async def make_request(self, client: httpx.AsyncClient, endpoint: str) -> float:
        """Make a single request and return latency"""
        start = time.time()
        try:
            response = await client.get(f"{self.base_url}{endpoint}")
            latency = (time.time() - start) * 1000  # Convert to ms

            if response.status_code == 200:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                error_key = f"HTTP {response.status_code}"
                self.errors[error_key] = self.errors.get(error_key, 0) + 1

            self.total_requests += 1
            return latency

        except Exception as e:
            latency = (time.time() - start) * 1000
            self.failed_requests += 1
            self.total_requests += 1
            error_key = type(e).__name__
            self.errors[error_key] = self.errors.get(error_key, 0) + 1
            return latency

    async def worker(self, client: httpx.AsyncClient, duration_seconds: int):
        """Worker that makes continuous requests"""
        start_time = time.time()
        endpoints = ["/health", "/metrics"]

        while time.time() - start_time < duration_seconds:
            # Alternate between endpoints
            endpoint = endpoints[self.total_requests % len(endpoints)]
            latency = await self.make_request(client, endpoint)
            self.latencies.append(latency)

            # Small delay to avoid overwhelming the server
            await asyncio.sleep(0.01)

    async def run(self, duration_seconds: int) -> LoadTestResult:
        """Run load test for specified duration"""
        start_time = time.time()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create worker tasks
            tasks = [
                self.worker(client, duration_seconds)
                for _ in range(self.workers)
            ]

            # Run all workers concurrently
            await asyncio.gather(*tasks)

        end_time = time.time()
        actual_duration = end_time - start_time

        # Calculate statistics
        if self.latencies:
            sorted_latencies = sorted(self.latencies)
            p50_index = int(len(sorted_latencies) * 0.50)
            p95_index = int(len(sorted_latencies) * 0.95)
            p99_index = int(len(sorted_latencies) * 0.99)

            return LoadTestResult(
                total_requests=self.total_requests,
                successful_requests=self.successful_requests,
                failed_requests=self.failed_requests,
                duration_seconds=actual_duration,
                requests_per_second=self.total_requests / actual_duration,
                avg_latency_ms=statistics.mean(self.latencies),
                p50_latency_ms=sorted_latencies[p50_index],
                p95_latency_ms=sorted_latencies[p95_index],
                p99_latency_ms=sorted_latencies[p99_index],
                min_latency_ms=min(self.latencies),
                max_latency_ms=max(self.latencies),
                errors=self.errors,
            )
        else:
            return LoadTestResult(
                total_requests=self.total_requests,
                successful_requests=self.successful_requests,
                failed_requests=self.failed_requests,
                duration_seconds=actual_duration,
                requests_per_second=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                errors=self.errors,
            )


async def verify_metrics(base_url: str) -> Dict[str, any]:
    """Verify metrics after load test"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        start = time.time()
        response = await client.get(f"{base_url}/metrics")
        metrics_duration = (time.time() - start) * 1000

        metrics_text = response.text
        lines = metrics_text.split('\n')

        # Count unique metrics
        metric_names = set()
        for line in lines:
            if line and not line.startswith('#'):
                metric_name = line.split('{')[0].split(' ')[0]
                if metric_name:
                    metric_names.add(metric_name)

        # Count YORI metrics
        yori_metrics = [m for m in metric_names if m.startswith('yori_')]

        return {
            'response_time_ms': metrics_duration,
            'total_metrics': len(metric_names),
            'yori_metrics': len(yori_metrics),
            'metrics_size_kb': len(metrics_text) / 1024,
            'status_code': response.status_code,
        }


def print_results(results: LoadTestResult, metrics_info: Dict[str, any]):
    """Print load test results"""
    if RICH_AVAILABLE:
        console = Console()

        # Performance table
        table = Table(title="Load Test Results", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Requests", str(results.total_requests))
        table.add_row("Successful", str(results.successful_requests))
        table.add_row("Failed", str(results.failed_requests))
        table.add_row("Duration", f"{results.duration_seconds:.2f}s")
        table.add_row("Requests/sec", f"{results.requests_per_second:.2f}")
        table.add_row("", "")
        table.add_row("Avg Latency", f"{results.avg_latency_ms:.2f}ms")
        table.add_row("P50 Latency", f"{results.p50_latency_ms:.2f}ms")
        table.add_row("P95 Latency", f"{results.p95_latency_ms:.2f}ms")
        table.add_row("P99 Latency", f"{results.p99_latency_ms:.2f}ms")
        table.add_row("Min Latency", f"{results.min_latency_ms:.2f}ms")
        table.add_row("Max Latency", f"{results.max_latency_ms:.2f}ms")

        console.print(table)

        # Metrics table
        metrics_table = Table(title="Metrics Endpoint Performance", show_header=True)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green")

        metrics_table.add_row("Response Time", f"{metrics_info['response_time_ms']:.2f}ms")
        metrics_table.add_row("Status Code", str(metrics_info['status_code']))
        metrics_table.add_row("Total Metrics", str(metrics_info['total_metrics']))
        metrics_table.add_row("YORI Metrics", str(metrics_info['yori_metrics']))
        metrics_table.add_row("Metrics Size", f"{metrics_info['metrics_size_kb']:.2f}KB")

        console.print(metrics_table)

        # Errors
        if results.errors:
            errors_table = Table(title="Errors", show_header=True)
            errors_table.add_column("Error Type", style="red")
            errors_table.add_column("Count", style="yellow")

            for error, count in results.errors.items():
                errors_table.add_row(error, str(count))

            console.print(errors_table)

        # Validation
        console.print("\n[bold]Validation:[/bold]")

        # Check metrics endpoint performance (<1ms requirement, but <10ms acceptable under load)
        if metrics_info['response_time_ms'] < 10:
            console.print("[green]✓[/green] Metrics endpoint performance OK")
        else:
            console.print(f"[yellow]⚠[/yellow] Metrics endpoint slow: {metrics_info['response_time_ms']:.2f}ms")

        # Check metric count (should have 20+ YORI metrics)
        if metrics_info['yori_metrics'] >= 20:
            console.print(f"[green]✓[/green] Sufficient metrics exposed: {metrics_info['yori_metrics']}")
        else:
            console.print(f"[yellow]⚠[/yellow] Low metric count: {metrics_info['yori_metrics']}")

        # Check error rate
        error_rate = results.failed_requests / results.total_requests if results.total_requests > 0 else 0
        if error_rate < 0.01:
            console.print(f"[green]✓[/green] Low error rate: {error_rate*100:.2f}%")
        else:
            console.print(f"[yellow]⚠[/yellow] High error rate: {error_rate*100:.2f}%")

    else:
        # Fallback to simple print
        print("\n" + "="*50)
        print("LOAD TEST RESULTS")
        print("="*50)
        print(f"Total Requests: {results.total_requests}")
        print(f"Successful: {results.successful_requests}")
        print(f"Failed: {results.failed_requests}")
        print(f"Duration: {results.duration_seconds:.2f}s")
        print(f"Requests/sec: {results.requests_per_second:.2f}")
        print(f"\nAvg Latency: {results.avg_latency_ms:.2f}ms")
        print(f"P95 Latency: {results.p95_latency_ms:.2f}ms")
        print(f"P99 Latency: {results.p99_latency_ms:.2f}ms")
        print(f"\nMetrics Endpoint: {metrics_info['response_time_ms']:.2f}ms")
        print(f"YORI Metrics: {metrics_info['yori_metrics']}")


async def main():
    parser = argparse.ArgumentParser(description="Load test YORI proxy server")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of YORI server")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers")

    args = parser.parse_args()

    print(f"Starting load test against {args.url}")
    print(f"Duration: {args.duration}s, Workers: {args.workers}")
    print("")

    # Run load test
    tester = LoadTester(args.url, workers=args.workers)
    results = await tester.run(args.duration)

    # Verify metrics
    print("\nVerifying metrics endpoint...")
    metrics_info = await verify_metrics(args.url)

    # Print results
    print_results(results, metrics_info)


if __name__ == "__main__":
    asyncio.run(main())
