"""
Performance verification for block page and override functionality

Targets:
- Page Render: <50ms to generate block page
- Override Check: <100ms to validate password
"""

import time
from datetime import datetime
from yori.enforcement import EnforcementDecision
from yori.block_page import render_block_page
from yori.override import validate_override_password, hash_password


def benchmark(func, *args, iterations=1000, **kwargs):
    """Benchmark a function"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to milliseconds

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    return {
        'avg': avg_time,
        'min': min_time,
        'max': max_time,
    }


def test_block_page_render_performance():
    """Test block page rendering performance"""
    decision = EnforcementDecision(
        should_block=True,
        policy_name="bedtime.rego",
        reason="LLM access not allowed after 21:00",
        timestamp=datetime.now(),
        allow_override=True,
        request_id="perf-test-123",
    )

    print("\n=== Block Page Rendering Performance ===")
    stats = benchmark(render_block_page, decision, iterations=1000)

    print(f"Average: {stats['avg']:.2f}ms")
    print(f"Min: {stats['min']:.2f}ms")
    print(f"Max: {stats['max']:.2f}ms")

    target = 50  # ms
    if stats['avg'] < target:
        print(f"✓ PASS: Average {stats['avg']:.2f}ms < {target}ms target")
    else:
        print(f"✗ FAIL: Average {stats['avg']:.2f}ms >= {target}ms target")

    return stats['avg'] < target


def test_override_validation_performance():
    """Test override password validation performance"""
    password = "test_password_123"
    password_hash = hash_password(password)

    print("\n=== Override Password Validation Performance ===")
    stats = benchmark(validate_override_password, password, password_hash, iterations=1000)

    print(f"Average: {stats['avg']:.2f}ms")
    print(f"Min: {stats['min']:.2f}ms")
    print(f"Max: {stats['max']:.2f}ms")

    target = 100  # ms
    if stats['avg'] < target:
        print(f"✓ PASS: Average {stats['avg']:.2f}ms < {target}ms target")
    else:
        print(f"✗ FAIL: Average {stats['avg']:.2f}ms >= {target}ms target")

    return stats['avg'] < target


if __name__ == "__main__":
    print("Running performance tests...\n")

    render_pass = test_block_page_render_performance()
    override_pass = test_override_validation_performance()

    print("\n=== Summary ===")
    if render_pass and override_pass:
        print("✓ All performance targets met!")
    else:
        print("✗ Some performance targets not met")
        if not render_pass:
            print("  - Block page rendering too slow")
        if not override_pass:
            print("  - Override validation too slow")
