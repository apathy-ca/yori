# YORI Metrics Documentation

This document describes all Prometheus metrics exposed by the YORI proxy server.

## Metrics Endpoint

Metrics are exposed at `/metrics` in Prometheus text format.

## Metric Naming Convention

All YORI metrics follow the pattern: `yori_<subsystem>_<metric>_<unit>`

- **Prefix**: All metrics start with `yori_`
- **Subsystem**: Component being measured (requests, upstream, enforcement, etc.)
- **Unit suffix**: `_total` for counters, `_seconds` for time, `_bytes` for size

## Request Metrics

### yori_requests_total
- **Type**: Counter
- **Description**: Total number of HTTP requests received by the proxy
- **Labels**:
  - `method`: HTTP method (GET, POST, etc.)
  - `path`: Request path (normalized to avoid high cardinality)
  - `status_code`: HTTP response status code
- **Example**: `yori_requests_total{method="POST",path="/v1/chat/completions",status_code="200"} 1547`

### yori_request_duration_seconds
- **Type**: Histogram
- **Description**: Request duration from receipt to response
- **Labels**:
  - `method`: HTTP method
  - `path`: Request path (normalized)
- **Buckets**: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
- **Example queries**:
  - p50: `histogram_quantile(0.5, rate(yori_request_duration_seconds_bucket[5m]))`
  - p95: `histogram_quantile(0.95, rate(yori_request_duration_seconds_bucket[5m]))`
  - p99: `histogram_quantile(0.99, rate(yori_request_duration_seconds_bucket[5m]))`

### yori_active_requests
- **Type**: Gauge
- **Description**: Number of requests currently being processed
- **Labels**: None
- **Example**: `yori_active_requests 12`

### yori_request_size_bytes
- **Type**: Histogram
- **Description**: Size of HTTP request bodies in bytes
- **Labels**:
  - `method`: HTTP method
  - `path`: Request path (normalized)
- **Buckets**: 100, 1000, 10000, 100000, 1000000, 10000000

### yori_response_size_bytes
- **Type**: Histogram
- **Description**: Size of HTTP response bodies in bytes
- **Labels**:
  - `path`: Request path (normalized)
  - `status_code`: HTTP response status code
- **Buckets**: 100, 1000, 10000, 100000, 1000000, 10000000

## Upstream API Metrics

### yori_upstream_requests_total
- **Type**: Counter
- **Description**: Total number of requests forwarded to upstream APIs
- **Labels**:
  - `host`: Upstream API host (e.g., "api.openai.com")
  - `status_code`: HTTP response status code from upstream
  - `method`: HTTP method
- **Example**: `yori_upstream_requests_total{host="api.openai.com",status_code="200",method="POST"} 1523`

### yori_upstream_duration_seconds
- **Type**: Histogram
- **Description**: Duration of upstream API requests
- **Labels**:
  - `host`: Upstream API host
  - `method`: HTTP method
- **Buckets**: 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0
- **Example query** (upstream p95): `histogram_quantile(0.95, rate(yori_upstream_duration_seconds_bucket{host="api.openai.com"}[5m]))`

### yori_upstream_errors_total
- **Type**: Counter
- **Description**: Total number of upstream API errors
- **Labels**:
  - `host`: Upstream API host
  - `error_type`: Type of error (timeout, connection_error, http_error, etc.)
- **Example**: `yori_upstream_errors_total{host="api.openai.com",error_type="timeout"} 5`

## Enforcement Metrics

### yori_enforcement_blocks_total
- **Type**: Counter
- **Description**: Total number of requests blocked by enforcement policies
- **Labels**:
  - `policy_name`: Name of the policy that triggered the block
  - `reason`: Reason category (policy_violation, rate_limit, etc.)
- **Example**: `yori_enforcement_blocks_total{policy_name="content_filter",reason="policy_violation"} 23`

### yori_enforcement_allows_total
- **Type**: Counter
- **Description**: Total number of requests allowed (not blocked)
- **Labels**:
  - `action`: Action taken (allowed, allowlisted, consent_mode, etc.)
- **Example**: `yori_enforcement_allows_total{action="allowed"} 1524`

### yori_override_attempts_total
- **Type**: Counter
- **Description**: Total number of override attempts
- **Labels**:
  - `success`: Whether the override was successful (true/false)
  - `emergency`: Whether it was an emergency override (true/false)
- **Example**: `yori_override_attempts_total{success="true",emergency="false"} 12`

### yori_override_rate_limits_total
- **Type**: Counter
- **Description**: Total number of override attempts rejected due to rate limiting
- **Labels**: None
- **Example**: `yori_override_rate_limits_total 3`

## System Metrics

### yori_info
- **Type**: Info
- **Description**: YORI proxy server information
- **Labels**:
  - `version`: YORI version
  - `mode`: Operating mode (proxy, monitor, enforce)
  - `python_version`: Python interpreter version
- **Example**: `yori_info{version="0.2.0",mode="enforce",python_version="3.11.5"} 1`

### yori_process_memory_bytes
- **Type**: Gauge
- **Description**: Memory usage of the YORI process in bytes (RSS)
- **Labels**: None
- **Example**: `yori_process_memory_bytes 52428800`

### yori_active_connections
- **Type**: Gauge
- **Description**: Number of active HTTP connections
- **Labels**: None
- **Example**: `yori_active_connections 8`

### yori_http_client_pool_connections
- **Type**: Gauge
- **Description**: Number of connections in the HTTP client connection pool
- **Labels**:
  - `state`: Connection state (active, idle)
- **Example**: `yori_http_client_pool_connections{state="idle"} 5`

## Health Check Metrics

### yori_health_status
- **Type**: Gauge
- **Description**: Health status of YORI components (1=healthy, 0=unhealthy)
- **Labels**:
  - `component`: Component name (proxy, upstream_api, audit_db, etc.)
- **Example**: `yori_health_status{component="upstream_api"} 1`

### yori_health_check_duration_seconds
- **Type**: Histogram
- **Description**: Duration of health check operations
- **Labels**:
  - `component`: Component being checked
- **Buckets**: 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0

## Audit Database Metrics

### yori_audit_log_writes_total
- **Type**: Counter
- **Description**: Total number of audit log writes
- **Labels**:
  - `event_type`: Type of event (block, request, response, override)
  - `success`: Whether the write was successful (true/false)
- **Example**: `yori_audit_log_writes_total{event_type="block",success="true"} 23`

### yori_audit_db_size_bytes
- **Type**: Gauge
- **Description**: Size of the audit database file in bytes
- **Labels**: None
- **Example**: `yori_audit_db_size_bytes 10485760`

## Path Normalization

To avoid metric cardinality explosion, request paths are normalized:

- `/v1/chat/completions` → `/v1/chat/completions`
- `/v1/models/gpt-4` → `/v1/models/:id`
- `/v1/files/file-abc123` → `/v1/files/:id`
- Unknown paths with IDs → `/:id/:id/...`

## Recommended Alerts

### High Error Rate
```promql
rate(yori_requests_total{status_code=~"5.."}[5m]) > 0.05
```
Alert when 5xx error rate exceeds 5%.

### Upstream Timeouts
```promql
rate(yori_upstream_errors_total{error_type="timeout"}[5m]) > 0.01
```
Alert when upstream timeout rate is significant.

### High Latency
```promql
histogram_quantile(0.95, rate(yori_request_duration_seconds_bucket[5m])) > 5.0
```
Alert when p95 latency exceeds 5 seconds.

### High Block Rate
```promql
rate(yori_enforcement_blocks_total[5m]) / rate(yori_requests_total[5m]) > 0.1
```
Alert when more than 10% of requests are blocked.

### Memory Growth
```promql
rate(yori_process_memory_bytes[5m]) > 0
```
Alert on sustained memory growth.

### Unhealthy Components
```promql
yori_health_status{component="upstream_api"} == 0
```
Alert when critical components are unhealthy.

## Example Grafana Queries

### Request Rate (requests/sec)
```promql
rate(yori_requests_total[5m])
```

### Error Rate by Status Code
```promql
sum by (status_code) (rate(yori_requests_total{status_code=~"4..|5.."}[5m]))
```

### Latency Percentiles
```promql
# p50
histogram_quantile(0.50, rate(yori_request_duration_seconds_bucket[5m]))

# p95
histogram_quantile(0.95, rate(yori_request_duration_seconds_bucket[5m]))

# p99
histogram_quantile(0.99, rate(yori_request_duration_seconds_bucket[5m]))
```

### Block Rate
```promql
sum(rate(yori_enforcement_blocks_total[5m]))
```

### Upstream API Health
```promql
yori_health_status{component="upstream_api"}
```

## Metric Collection Best Practices

1. **Scrape interval**: 15-30 seconds recommended
2. **Retention**: Keep metrics for at least 30 days
3. **Cardinality**: Monitor metric cardinality to prevent explosion
4. **Labels**: Use low-cardinality labels only (no user IDs, device IDs, etc.)
5. **Performance**: Metrics endpoint should respond in <1ms under normal load

## Testing Metrics

To verify metrics are working:

```bash
# Check metrics endpoint
curl http://localhost:8080/metrics

# Verify specific metric exists
curl http://localhost:8080/metrics | grep yori_requests_total

# Count number of metrics
curl -s http://localhost:8080/metrics | grep "^yori_" | wc -l
```

Expected: 20+ unique metric families exposed.
