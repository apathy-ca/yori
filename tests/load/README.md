## YORI Load Testing Guide

This directory contains comprehensive load testing, soak testing, and chaos engineering tests for the YORI proxy server.

### Test Suite Overview

| Test Type | Location | Purpose | Duration |
|-----------|----------|---------|----------|
| Load Tests | `tests/load/` | Verify performance under load | 5-30 min |
| Soak Tests | `tests/soak/` | Detect memory leaks and degradation | 24 hours |
| Chaos Tests | `tests/chaos/` | Verify resilience and recovery | 10-20 min |

### Prerequisites

Install load testing dependencies:

```bash
pip install -e ".[load-testing]"
```

Or install manually:

```bash
pip install locust psutil memory-profiler matplotlib
```

### Running Load Tests

#### Quick Start

Start the YORI proxy in one terminal:

```bash
python -m yori --config yori.conf.example --port 8080
```

Run basic load test in another terminal:

```bash
cd tests/load
locust -f locustfile.py --host http://localhost:8080
```

Then open http://localhost:8089 in your browser to control the test.

#### Headless Mode (CI/CD)

Run without web UI:

```bash
locust -f tests/load/locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --host http://localhost:8080 \
  --html tests/load/report.html
```

Parameters:
- `--users`: Total number of concurrent users
- `--spawn-rate`: Users to spawn per second
- `--run-time`: Test duration (e.g., 5m, 1h)
- `--html`: Generate HTML report

#### Target Achievement Tests

**Test 1: 100 concurrent users**
```bash
locust -f tests/load/locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --host http://localhost:8080
```

Expected results:
- P95 latency < 50ms
- Failure rate < 1%
- RPS > 100

**Test 2: 1000 concurrent users** (success criteria)
```bash
locust -f tests/load/locustfile.py \
  --headless \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 15m \
  --host http://localhost:8080
```

Expected results:
- P95 latency < 100ms
- Failure rate < 5%
- System remains stable

#### Distributed Load Testing

For very high load, run Locust in distributed mode:

Master:
```bash
locust -f tests/load/locustfile.py --master --host http://localhost:8080
```

Workers (run on multiple machines):
```bash
locust -f tests/load/locustfile.py --worker --master-host <master-ip>
```

### Running Soak Tests

Soak tests run for 24 hours to detect memory leaks and performance degradation.

#### Full 24-Hour Test

```bash
python tests/soak/soak_test.py
```

This will:
1. Start Locust with moderate load (50 users)
2. Monitor memory, CPU, connections every minute
3. Run for 24 hours
4. Generate metrics report

#### Quick Soak Test (5 minutes)

For validation:

```bash
python tests/soak/soak_test.py --quick-test
```

#### Custom Duration

```bash
python tests/soak/soak_test.py --hours 12 --interval 30
```

Parameters:
- `--hours`: Test duration in hours (default: 24)
- `--interval`: Sample interval in seconds (default: 60)

#### Monitoring

While soak test runs, monitor in another terminal:

```bash
# Watch memory usage
watch -n 10 'ps aux | grep yori'

# Watch connections
watch -n 10 'netstat -an | grep 8080 | wc -l'
```

#### Results

Results are saved to:
- `tests/soak/soak_test_metrics.json` - Raw metrics
- `tests/soak/soak_test_report.html` - Locust report
- `tests/soak/soak_test_stats.csv` - Request statistics

### Running Chaos Tests

Chaos tests verify system resilience under failure conditions.

#### Run All Chaos Tests

```bash
python tests/chaos/chaos_test.py
```

#### Individual Test Categories

```bash
# Test only upstream failures
python tests/chaos/chaos_test.py --test upstream

# Test only resource exhaustion
python tests/chaos/chaos_test.py --test resources

# Test only process failures
python tests/chaos/chaos_test.py --test process
```

#### Chaos Test Scenarios

1. **Upstream API Failures**
   - 500 errors from upstream
   - Connection timeouts
   - Connection refused

2. **Network Issues**
   - High latency injection
   - Request bursts
   - Concurrent connections

3. **Resource Exhaustion**
   - Memory pressure
   - File descriptor limits
   - Database locks

4. **Process Failures**
   - Graceful shutdown (SIGTERM)
   - Forced kill (SIGKILL)
   - Recovery validation

### Performance Targets

| Metric | Target | Test |
|--------|--------|------|
| P95 Latency | < 50ms | Load test (100 users) |
| P95 Latency | < 100ms | Load test (1000 users) |
| Memory Usage | < 100MB | Soak test |
| Memory Growth | < 20% | Soak test (24h) |
| Failure Rate | < 1% | Load test (normal) |
| Failure Rate | < 5% | Load test (1000 users) |
| Recovery Time | < 10s | Chaos tests |

### Interpreting Results

#### Load Test Metrics

Check the HTML report (`report.html`) for:

1. **Response Times**
   - Median (p50): Should be very low (<20ms)
   - P95: Target <50ms
   - P99: May be higher, but <200ms acceptable

2. **Request Rate (RPS)**
   - Higher is better
   - Should be stable throughout test
   - Target: >100 RPS for 100 users

3. **Failure Rate**
   - Target: <1% under normal load
   - Some failures acceptable at 1000 users

4. **Charts**
   - Look for performance degradation over time
   - Memory should be stable
   - Response time should not increase

#### Soak Test Metrics

Check `soak_test_metrics.json` for:

1. **Memory Growth**
   - Should be <20% over 24 hours
   - Stable after initial ramp-up
   - No steady upward trend

2. **CPU Usage**
   - Should be stable
   - No gradual increase

3. **Connections**
   - Should not leak
   - Final count ≈ initial count

#### Chaos Test Results

All chaos tests should pass (✓):

- ✓ System handles upstream errors
- ✓ System handles timeouts
- ✓ System handles rapid bursts
- ✓ System handles concurrent load
- ✓ System manages memory under pressure
- ✓ System shuts down gracefully
- ✓ System recovers from forced kill

### Troubleshooting

#### "Connection refused" errors

Ensure YORI proxy is running:
```bash
python -m yori --port 8080
```

#### High latency

1. Check if upstream APIs are slow
2. Verify database is not locked
3. Check for memory swapping

#### Memory leaks

1. Run with memory profiler:
   ```bash
   mprof run python -m yori
   mprof plot
   ```

2. Check for unclosed connections
3. Review database connection pooling

#### Test failures

1. Check YORI logs
2. Verify configuration is correct
3. Ensure no firewall blocking
4. Check system resources (RAM, CPU)

### Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Load Tests

on: [push, pull_request]

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[load-testing]"
      - name: Start YORI
        run: python -m yori --port 8080 &
      - name: Wait for startup
        run: sleep 5
      - name: Run load tests
        run: |
          locust -f tests/load/locustfile.py \
            --headless \
            --users 100 \
            --spawn-rate 10 \
            --run-time 5m \
            --host http://localhost:8080 \
            --html report.html
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-report
          path: report.html
```

### Advanced Topics

#### Custom Test Scenarios

Add custom scenarios to `locustfile.py`:

```python
@task(weight)
def custom_scenario(self):
    """Your custom test"""
    with self.client.get("/custom/endpoint") as response:
        if response.status_code == 200:
            response.success()
```

#### Performance Profiling

Profile YORI during load test:

```bash
python -m cProfile -o yori.prof -m yori
```

Analyze results:

```python
import pstats
p = pstats.Stats('yori.prof')
p.sort_stats('cumulative').print_stats(20)
```

#### Memory Profiling

```bash
mprof run python -m yori
mprof plot
```

### Best Practices

1. **Baseline First**: Run tests on current version to establish baseline
2. **Incremental Load**: Start with low load, gradually increase
3. **Monitor System**: Watch CPU, memory, disk I/O during tests
4. **Test Realistic Scenarios**: Use realistic request patterns
5. **Soak Test Regularly**: Run overnight/weekend soak tests
6. **Chaos Test Before Release**: Verify resilience before deployment
7. **Document Results**: Keep history of test results for comparison

### Support

For issues or questions:
- Check GitHub Issues: https://github.com/apathy-ca/yori/issues
- Review documentation: `docs/testing/`
- Check CI/CD logs for test failures
