# YORI Test Suite

Comprehensive test suite for the YORI LLM governance gateway.

## Test Structure

```
tests/
├── unit/               # Fast, isolated unit tests
├── integration/        # Integration tests with real components
├── e2e/               # End-to-end system tests
├── performance/       # Performance and benchmark tests
├── reports/           # Generated test reports
└── conftest.py        # Shared pytest fixtures
```

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Performance Tests
```bash
pytest tests/performance/ -v
```

### With Coverage
```bash
pytest tests/ --cov=yori --cov-report=html
firefox htmlcov/index.html
```

## Test Categories

### Unit Tests (Fast)
- **test_config.py**: Configuration management
- **test_proxy.py**: Proxy server logic
- **test_policy.py**: Policy engine wrapper

### Integration Tests (Medium)
- **test_e2e_proxy.py**: End-to-end proxy flow
- **test_policy_eval.py**: Policy evaluation integration

### Performance Tests (Benchmarks)
- **test_latency.py**: Latency measurements (target: <10ms p95)
- **test_throughput.py**: Throughput testing (target: 50 req/sec)

## Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

## Coverage Targets

- **Overall**: >80% code coverage
- **Python**: >80% coverage
- **Rust**: >80% coverage

Check coverage:
```bash
pytest --cov=yori --cov-report=term-missing
```

## Performance Targets

All targets from PROJECT_PLAN.md:

- **Latency**: <10ms overhead (p95)
- **Throughput**: 50 requests/sec sustained
- **Memory**: <256MB RSS under normal load
- **SQLite**: Query time <100ms for 100k+ records
- **Policy Eval**: <5ms per request

## Continuous Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Branch pushes matching `cz*/**`

See `.github/workflows/tests.yml` for CI configuration.

## Writing Tests

### Unit Test Template
```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    def test_basic_functionality(self):
        # Arrange
        ...
        # Act
        ...
        # Assert
        assert ...
```

### Integration Test Template
```python
import pytest

@pytest.mark.integration
class TestMyIntegration:
    @pytest.mark.asyncio
    async def test_with_real_components(self):
        # Test with real components
        ...
```

### Performance Test Template
```python
import pytest
import time

@pytest.mark.performance
class TestMyPerformance:
    def test_latency(self):
        start = time.perf_counter()
        # ... operation ...
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        assert latency_ms < target_ms
```

## Fixtures

Common fixtures are defined in `conftest.py`:

- `test_config`: Test configuration
- `proxy_server`: ProxyServer instance
- `test_client`: FastAPI test client
- `async_client`: Async HTTP client
- `mock_policy_engine`: Mocked policy engine
- `mock_cache`: Mocked cache
- `sample_llm_request`: Sample LLM API request
- `sample_policy_input`: Sample policy evaluation input
- `audit_db`: Temporary audit database

## Troubleshooting

### Rust Module Not Built
If you see "Rust module not built" errors, build it first:
```bash
maturin develop
```

### Coverage Not Working
Install coverage tools:
```bash
pip install pytest-cov coverage
cargo install cargo-tarpaulin  # For Rust coverage
```

### Tests Timing Out
Increase timeout for slow tests:
```bash
pytest --timeout=300
```

## Contributing

When adding new features:
1. Write unit tests first (TDD)
2. Add integration tests for component interactions
3. Add performance tests if feature affects performance
4. Ensure >80% coverage for new code
5. Run full test suite before committing
