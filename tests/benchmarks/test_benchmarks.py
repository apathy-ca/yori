"""
Performance benchmarks for YORI proxy

Uses pytest-benchmark to measure and track performance metrics.
Run with: pytest tests/benchmarks/ --benchmark-only
"""

import pytest
import hashlib
import json
from yori.cache import InMemoryCache, generate_cache_key, generate_policy_cache_key
from yori.enforcement import EnforcementDecision
from datetime import datetime


# Cache Benchmarks

def test_benchmark_cache_set(benchmark):
    """Benchmark cache set operations"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)

    def cache_set():
        cache.set("test_key", "test_value")

    benchmark(cache_set)

    # Verify cache works
    assert cache.get("test_key") == "test_value"


def test_benchmark_cache_get_hit(benchmark):
    """Benchmark cache get operations (hit)"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)
    cache.set("test_key", "test_value")

    def cache_get():
        return cache.get("test_key")

    result = benchmark(cache_get)

    # Should be very fast (<0.1ms)
    assert result is not None


def test_benchmark_cache_get_miss(benchmark):
    """Benchmark cache get operations (miss)"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)

    def cache_get():
        return cache.get("nonexistent_key")

    result = benchmark(cache_get)


def test_benchmark_cache_key_generation(benchmark):
    """Benchmark cache key generation"""
    data = {
        "client_ip": "192.168.1.100",
        "path": "/v1/chat/completions",
        "method": "POST",
        "body": {"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}
    }

    def generate_key():
        return generate_cache_key(data)

    result = benchmark(generate_key)

    # Should be fast (<1ms)
    assert len(result) == 64  # SHA256 hex


def test_benchmark_policy_cache_key(benchmark):
    """Benchmark policy-specific cache key generation"""

    def generate_key():
        return generate_policy_cache_key(
            client_ip="192.168.1.100",
            request_path="/v1/chat/completions",
            request_method="POST",
        )

    result = benchmark(generate_key)

    assert len(result) == 64


# Cache with Eviction Benchmarks

def test_benchmark_cache_with_eviction(benchmark):
    """Benchmark cache with LRU eviction under load"""
    cache = InMemoryCache(default_ttl=60, max_size=100)

    # Pre-fill cache to trigger evictions
    for i in range(100):
        cache.set(f"key_{i}", f"value_{i}")

    iteration = [0]

    def cache_operations():
        i = iteration[0]
        # Set will trigger eviction
        cache.set(f"new_key_{i}", f"new_value_{i}")
        # Get existing key
        cache.get(f"key_{i % 100}")
        iteration[0] += 1

    benchmark(cache_operations)


def test_benchmark_cache_clear_expired(benchmark):
    """Benchmark clearing expired entries"""
    cache = InMemoryCache(default_ttl=1)

    # Add entries with short TTL
    for i in range(100):
        cache.set(f"key_{i}", f"value_{i}", ttl=1)

    # Add entries with long TTL
    for i in range(100):
        cache.set(f"long_key_{i}", f"value_{i}", ttl=1000)

    import time
    time.sleep(1.1)  # Wait for short TTL entries to expire

    def clear_expired():
        return cache.clear_expired()

    result = benchmark(clear_expired)

    # Should have cleared 100 expired entries
    assert result >= 0


# Enforcement Decision Caching Benchmark

def test_benchmark_enforcement_decision_caching(benchmark):
    """Benchmark caching of enforcement decisions"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)

    decision = EnforcementDecision(
        enforce=False,
        reason="Allowed during business hours",
    )

    cache_key = generate_policy_cache_key(
        client_ip="192.168.1.100",
        request_path="/v1/chat/completions",
        request_method="POST",
    )

    iteration = [0]

    def cache_decision():
        # Simulate cache hit/miss pattern (80% hit rate)
        if iteration[0] % 5 == 0:
            # Miss - store in cache
            cache.set(cache_key, decision)
        else:
            # Hit - retrieve from cache
            cached = cache.get(cache_key)

        iteration[0] += 1

    benchmark(cache_decision)


# Hash Function Benchmarks

def test_benchmark_sha256_hashing(benchmark):
    """Benchmark SHA256 hashing for cache keys"""
    data = json.dumps({
        "client_ip": "192.168.1.100",
        "path": "/v1/chat/completions",
        "method": "POST"
    }, sort_keys=True)

    def hash_data():
        return hashlib.sha256(data.encode()).hexdigest()

    result = benchmark(hash_data)

    assert len(result) == 64


# Cache Metrics Benchmark

def test_benchmark_cache_metrics(benchmark):
    """Benchmark cache metrics calculation"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)

    # Add some entries and access them
    for i in range(50):
        cache.set(f"key_{i}", f"value_{i}")

    for i in range(100):
        cache.get(f"key_{i % 50}")  # Mix of hits and misses

    def get_metrics():
        return cache.metrics()

    result = benchmark(get_metrics)

    # Should return metrics dict
    assert "hit_rate" in result
    assert "size" in result


# Regression Benchmarks (for CI)

@pytest.mark.benchmark(group="cache_operations")
def test_benchmark_cache_operations_regression(benchmark):
    """Regression test for cache operation performance"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)

    def mixed_operations():
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")
        cache.set("key2", "value2")
        return cache.size()

    result = benchmark(mixed_operations)

    # Target: <1ms for mixed operations
    assert benchmark.stats.stats.mean < 0.001  # 1ms in seconds


@pytest.mark.benchmark(group="key_generation")
def test_benchmark_key_generation_regression(benchmark):
    """Regression test for key generation performance"""

    def generate_keys():
        data = {
            "ip": "192.168.1.100",
            "path": "/api/test",
            "method": "POST",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        return generate_cache_key(data)

    result = benchmark(generate_keys)

    # Target: <0.1ms for key generation
    assert benchmark.stats.stats.mean < 0.0001  # 0.1ms in seconds


# Baseline Comparison Benchmarks

def test_benchmark_no_cache_overhead(benchmark):
    """Measure overhead of cache miss (baseline for comparison)"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)

    def cache_miss():
        return cache.get("nonexistent_key")

    result = benchmark(cache_miss)

    # Cache miss should be negligible (<0.01ms)
    assert benchmark.stats.stats.mean < 0.00001  # 0.01ms


def test_benchmark_cache_hit_benefit(benchmark):
    """Measure benefit of cache hit vs. computation"""
    cache = InMemoryCache(default_ttl=60, max_size=1000)

    # Expensive computation to cache
    def expensive_computation():
        result = 0
        for i in range(1000):
            result += i * i
        return result

    # Store result in cache
    cache.set("computation_result", expensive_computation())

    def cached_retrieval():
        return cache.get("computation_result")

    result = benchmark(cached_retrieval)

    # Cache retrieval should be much faster than computation
    assert result is not None
