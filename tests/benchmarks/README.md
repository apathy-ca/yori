# YORI Performance Benchmarks

Comprehensive benchmark suite for measuring and tracking YORI proxy performance.

## Running Benchmarks

### Run all benchmarks

```bash
pytest tests/benchmarks/ --benchmark-only
```

### Run with detailed output

```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-columns=mean,stddev,min,max,rounds
```

### Save benchmark results

```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-save=baseline
```

### Compare against baseline

```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-compare=baseline
```

## Benchmark Categories

### Cache Operations
- `test_benchmark_cache_set` - Cache write performance
- `test_benchmark_cache_get_hit` - Cache read performance (hit)
- `test_benchmark_cache_get_miss` - Cache read performance (miss)
- `test_benchmark_cache_metrics` - Metrics calculation overhead

### Key Generation
- `test_benchmark_cache_key_generation` - General cache key generation
- `test_benchmark_policy_cache_key` - Policy-specific key generation
- `test_benchmark_sha256_hashing` - Hash function performance

### Eviction & Cleanup
- `test_benchmark_cache_with_eviction` - LRU eviction performance
- `test_benchmark_cache_clear_expired` - TTL cleanup performance

### Integration
- `test_benchmark_enforcement_decision_caching` - End-to-end caching workflow

### Regression Tests
- `test_benchmark_cache_operations_regression` - Target: <1ms
- `test_benchmark_key_generation_regression` - Target: <0.1ms
- `test_benchmark_no_cache_overhead` - Baseline overhead measurement
- `test_benchmark_cache_hit_benefit` - Cache vs. computation comparison

## Performance Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| Cache Get (hit) | <1 μs | ~320 ns |
| Cache Get (miss) | <0.5 μs | ~110 ns |
| Cache Set | <2 μs | ~1 μs |
| Key Generation | <5 μs | ~3.3 μs |
| Cache Operations (mixed) | <10 μs | ~2.2 μs |

## CI Integration

Add to CI pipeline to detect performance regressions:

```yaml
- name: Run benchmarks
  run: |
    pytest tests/benchmarks/ --benchmark-only --benchmark-autosave

- name: Compare with baseline
  run: |
    pytest tests/benchmarks/ --benchmark-only --benchmark-compare=0001
  continue-on-error: true
```

## Interpreting Results

### Mean
Average execution time - primary metric for performance

### StdDev
Standard deviation - lower is better (more consistent)

### Min/Max
Best and worst case times - watch for outliers

### Rounds
Number of iterations - more rounds = more confidence

## Adding New Benchmarks

```python
def test_benchmark_my_feature(benchmark):
    """Benchmark description"""

    def operation():
        # Code to benchmark
        return result

    result = benchmark(operation)

    # Optional assertions
    assert result is not None
```

## Notes

- Benchmarks run with `timer=time.perf_counter` for nanosecond precision
- GC is enabled during benchmarks (realistic conditions)
- Minimum 5 rounds per benchmark for statistical significance
- Outliers are automatically detected and reported
- Results may vary based on system load and hardware

## Baseline Results (2026-01-29)

```
Test Platform: Linux, Python 3.11.14
Processor: Intel/AMD x86_64

Cache Operations:
- Cache get (miss): ~110 ns
- Cache get (hit): ~320 ns
- Cache set: ~1,060 ns
- Mixed operations: ~2.2 μs

Key Generation:
- Policy key: ~3.2 μs
- General key: ~4.0 μs
- SHA256 hash: ~540 ns

All targets met ✓
```
