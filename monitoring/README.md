# YORI Monitoring

This directory contains monitoring and observability configuration for YORI.

## Contents

- `grafana/` - Grafana dashboard templates
- This README with setup instructions

## Grafana Dashboard

### Quick Start

1. **Import the dashboard:**
   ```bash
   # In Grafana UI: Dashboards → Import → Upload JSON file
   # Select: monitoring/grafana/yori-dashboard.json
   ```

2. **Configure Prometheus data source:**
   - Data source type: Prometheus
   - URL: http://localhost:9090 (or your Prometheus server)
   - Save & Test

3. **View the dashboard:**
   - The dashboard will automatically populate with YORI metrics
   - Refresh rate: 10 seconds
   - Default time range: Last 1 hour

### Dashboard Sections

The dashboard includes the following sections:

#### Overview
- Request rate (requests/sec) by method, path, and status
- Error rate (4xx/5xx errors)
- Active requests gauge
- Memory usage
- Active connections

#### Latency
- Request latency percentiles (p50, p95, p99)
- Upstream API latency percentiles

#### Enforcement
- Enforcement activity (blocks vs allows)
- Block rate percentage (with alert at >10%)
- Override attempts (successful/failed/rate-limited)
- Total blocks by policy

#### Upstream
- Upstream request rate by host and method
- Upstream errors by type (timeout, connection_error, etc.)

#### Health
- Component health status (visual indicator)
- Health check duration by component

#### Audit Database
- Audit log write rate (successful/failed)
- Audit database size

### Alerts

The dashboard includes pre-configured alerts:

1. **High Block Rate** - Triggers when >10% of requests are blocked
2. **High Upstream Error Rate** - Triggers when upstream error rate >5%

To enable alerts, configure notification channels in Grafana.

## Prometheus Setup

### Quick Prometheus Configuration

Create a `prometheus.yml` configuration:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'yori'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
```

### Run Prometheus

```bash
# Using Docker
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Or install natively
# See: https://prometheus.io/download/
```

### Verify Metrics Collection

1. Open Prometheus UI: http://localhost:9090
2. Check targets: Status → Targets
3. Verify YORI target is UP
4. Query metrics: `yori_requests_total`

## Running YORI with Metrics

Start YORI proxy server normally:

```bash
# The /metrics endpoint is automatically available
yori proxy --config config.yaml

# Verify metrics endpoint
curl http://localhost:8080/metrics
```

## Example Queries

### Request Rate
```promql
rate(yori_requests_total[5m])
```

### Error Rate
```promql
sum(rate(yori_requests_total{status_code=~"5.."}[5m]))
```

### Latency p95
```promql
histogram_quantile(0.95, rate(yori_request_duration_seconds_bucket[5m]))
```

### Block Rate
```promql
rate(yori_enforcement_blocks_total[5m]) / rate(yori_requests_total[5m])
```

## Metrics Documentation

See `docs/METRICS.md` for detailed documentation on all available metrics.

## Troubleshooting

### No data in Grafana

1. Check Prometheus is scraping YORI:
   - Open Prometheus UI: http://localhost:9090
   - Go to Status → Targets
   - Verify YORI endpoint is UP

2. Check YORI metrics endpoint:
   ```bash
   curl http://localhost:8080/metrics
   ```

3. Verify Grafana data source:
   - Configuration → Data Sources
   - Test the Prometheus connection

### High cardinality warnings

If you see high cardinality warnings:
- Check path normalization is working
- Avoid labeling by user IDs or device IDs
- Review metric labels in `python/yori/metrics.py`

### Metrics endpoint is slow

The metrics endpoint should respond in <1ms. If slow:
- Check system metrics collection (psutil)
- Reduce scrape frequency in Prometheus
- Review metric collector performance

## Production Best Practices

1. **Scrape interval**: 15-30 seconds recommended
2. **Retention**: Keep metrics for at least 30 days
3. **Alerting**: Set up alerts for critical metrics
4. **Cardinality**: Monitor metric cardinality regularly
5. **Security**: Protect /metrics endpoint (use network policies or authentication)

## Load Testing

To verify metrics accuracy and performance under load, use the included load test script:

```bash
# Install dependencies
pip install httpx rich

# Run load test (60 seconds, 10 workers)
python monitoring/load_test.py --url http://localhost:8080 --duration 60 --workers 10

# Custom configuration
python monitoring/load_test.py --url http://localhost:8080 --duration 120 --workers 20
```

The load test will:
1. Generate sustained load against the YORI proxy
2. Verify metrics are accurately recorded
3. Check metrics endpoint performance (<10ms under load)
4. Validate metric count (20+ YORI metrics expected)
5. Report error rates and latency percentiles

### Expected Results

Under load, YORI should maintain:
- Error rate < 1%
- P95 latency < 100ms for /health endpoint
- Metrics endpoint response < 10ms
- 20+ unique YORI metrics exposed

## Next Steps

- Configure alerting rules in Prometheus
- Set up notification channels in Grafana
- Create custom dashboards for specific use cases
- Add recording rules for frequently-used queries
- Set up long-term metric storage (e.g., Thanos, Cortex)
- Run periodic load tests to validate metrics accuracy
