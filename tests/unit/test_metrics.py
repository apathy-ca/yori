"""
Unit tests for metrics module.

Tests metric definitions, path normalization, and metric collection functions.
"""

import pytest
from prometheus_client import CollectorRegistry

from yori.metrics import (
    normalize_path,
    initialize_info_metrics,
    update_system_metrics,
    generate_metrics,
)


class TestPathNormalization:
    """Test path normalization to avoid cardinality explosion"""

    def test_normalize_known_endpoints(self):
        """Known API endpoints should not be normalized"""
        assert normalize_path("/health") == "/health"
        assert normalize_path("/metrics") == "/metrics"
        assert normalize_path("/v1/chat/completions") == "/v1/chat/completions"
        assert normalize_path("/v1/completions") == "/v1/completions"
        assert normalize_path("/v1/models") == "/v1/models"

    def test_normalize_paths_with_ids(self):
        """Paths with IDs should be normalized to :id"""
        # Model IDs
        assert normalize_path("/v1/models/gpt-4") == "/v1/models/:id"
        assert normalize_path("/v1/models/gpt-3.5-turbo") == "/v1/models/:id"

        # File IDs
        assert normalize_path("/v1/files/file-abc123def456") == "/v1/files/:id"
        assert normalize_path("/v1/files/file_xyz") == "/v1/files/:id"

        # Fine-tune IDs
        assert normalize_path("/v1/fine-tunes/ft-abc123") == "/v1/fine-tunes/:id"

    def test_normalize_long_alphanumeric_ids(self):
        """Long alphanumeric strings should be treated as IDs"""
        path = "/v1/something/abcdef1234567890"
        assert ":id" in normalize_path(path)

    def test_normalize_preserves_known_segments(self):
        """Known API segments should be preserved"""
        path = "/v1/images/generations"
        assert normalize_path(path) == "/v1/images/generations"

        path = "/v1/audio/transcriptions"
        assert normalize_path(path) == "/v1/audio/transcriptions"

    def test_normalize_empty_path(self):
        """Empty path should remain empty"""
        assert normalize_path("") == ""

    def test_normalize_root_path(self):
        """Root path should be preserved"""
        assert normalize_path("/") == "/"


class TestMetricsGeneration:
    """Test metrics generation and export"""

    def test_generate_metrics_returns_bytes(self):
        """Metrics should be generated as bytes"""
        metrics = generate_metrics()
        assert isinstance(metrics, bytes)

    def test_generate_metrics_contains_yori_metrics(self):
        """Generated metrics should contain YORI metric names"""
        metrics = generate_metrics().decode('utf-8')

        # Check for key metrics
        assert "yori_requests_total" in metrics or "# TYPE yori_requests_total" in metrics
        assert "yori_active_requests" in metrics or "# TYPE yori_active_requests" in metrics
        assert "yori_process_memory_bytes" in metrics or "# TYPE yori_process_memory_bytes" in metrics

    def test_generate_metrics_valid_prometheus_format(self):
        """Generated metrics should be in valid Prometheus format"""
        metrics = generate_metrics().decode('utf-8')

        # Should have HELP and TYPE declarations
        lines = metrics.split('\n')
        has_help = any(line.startswith('# HELP') for line in lines)
        has_type = any(line.startswith('# TYPE') for line in lines)

        assert has_help or has_type  # At least one should be present

    def test_initialize_info_metrics(self):
        """Info metrics should be initialized with version and mode"""
        initialize_info_metrics(version="0.2.0", mode="enforce")

        metrics = generate_metrics().decode('utf-8')
        assert 'yori_info' in metrics or 'yori_target_info' in metrics

    def test_update_system_metrics(self):
        """System metrics should be updated without errors"""
        # Should not raise any exceptions
        update_system_metrics()

        metrics = generate_metrics().decode('utf-8')
        # Memory metric should have a value
        assert "yori_process_memory_bytes" in metrics


class TestMetricTypes:
    """Test that metrics have correct types"""

    def test_counter_metrics_exist(self):
        """Counter metrics should be defined"""
        from yori.metrics import (
            requests_total,
            upstream_requests_total,
            enforcement_blocks_total,
            enforcement_allows_total,
            override_attempts_total,
        )

        # Should be able to increment counters
        requests_total.labels(method="GET", path="/test", status_code="200").inc()
        upstream_requests_total.labels(host="test.com", status_code="200", method="GET").inc()
        enforcement_blocks_total.labels(policy_name="test", reason="violation").inc()
        enforcement_allows_total.labels(action="allowed").inc()
        override_attempts_total.labels(success="true", emergency="false").inc()

    def test_gauge_metrics_exist(self):
        """Gauge metrics should be defined"""
        from yori.metrics import (
            active_requests,
            process_memory_bytes,
            active_connections,
            health_status,
        )

        # Should be able to set gauges
        active_requests.set(10)
        process_memory_bytes.set(1024000)
        active_connections.set(5)
        health_status.labels(component="test").set(1)

    def test_histogram_metrics_exist(self):
        """Histogram metrics should be defined"""
        from yori.metrics import (
            request_duration_seconds,
            upstream_duration_seconds,
            health_check_duration_seconds,
        )

        # Should be able to observe values
        request_duration_seconds.labels(method="POST", path="/test").observe(0.5)
        upstream_duration_seconds.labels(host="test.com", method="POST").observe(1.0)
        health_check_duration_seconds.labels(component="test").observe(0.01)


class TestMetricLabels:
    """Test metric label validation"""

    def test_request_metrics_labels(self):
        """Request metrics should have correct labels"""
        from yori.metrics import requests_total, request_duration_seconds

        # Should accept valid labels
        requests_total.labels(method="POST", path="/v1/chat/completions", status_code="200").inc()
        request_duration_seconds.labels(method="POST", path="/v1/chat/completions").observe(0.5)

    def test_enforcement_metrics_labels(self):
        """Enforcement metrics should have correct labels"""
        from yori.metrics import enforcement_blocks_total, enforcement_allows_total

        enforcement_blocks_total.labels(policy_name="content_filter", reason="violation").inc()
        enforcement_allows_total.labels(action="allowed").inc()

    def test_override_metrics_labels(self):
        """Override metrics should have correct labels"""
        from yori.metrics import override_attempts_total

        override_attempts_total.labels(success="true", emergency="false").inc()
        override_attempts_total.labels(success="false", emergency="true").inc()

    def test_health_metrics_labels(self):
        """Health metrics should have correct labels"""
        from yori.metrics import health_status

        health_status.labels(component="proxy").set(1)
        health_status.labels(component="upstream_api").set(1)
        health_status.labels(component="audit_db").set(0)
