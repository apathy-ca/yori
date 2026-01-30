"""
Prometheus metrics for YORI proxy server.

This module defines all Prometheus metrics exported by YORI.
See docs/METRICS.md for detailed documentation.
"""

import sys
import os
import psutil
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Create a custom registry to avoid conflicts with other Prometheus clients
REGISTRY = CollectorRegistry()

# ============================================================================
# Request Metrics
# ============================================================================

requests_total = Counter(
    "yori_requests_total",
    "Total number of HTTP requests received by the proxy",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)

request_duration_seconds = Histogram(
    "yori_request_duration_seconds",
    "Request duration from receipt to response",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

active_requests = Gauge(
    "yori_active_requests",
    "Number of requests currently being processed",
    registry=REGISTRY,
)

request_size_bytes = Histogram(
    "yori_request_size_bytes",
    "Size of HTTP request bodies in bytes",
    ["method", "path"],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000),
    registry=REGISTRY,
)

response_size_bytes = Histogram(
    "yori_response_size_bytes",
    "Size of HTTP response bodies in bytes",
    ["path", "status_code"],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000),
    registry=REGISTRY,
)

# ============================================================================
# Upstream API Metrics
# ============================================================================

upstream_requests_total = Counter(
    "yori_upstream_requests_total",
    "Total number of requests forwarded to upstream APIs",
    ["host", "status_code", "method"],
    registry=REGISTRY,
)

upstream_duration_seconds = Histogram(
    "yori_upstream_duration_seconds",
    "Duration of upstream API requests",
    ["host", "method"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

upstream_errors_total = Counter(
    "yori_upstream_errors_total",
    "Total number of upstream API errors",
    ["host", "error_type"],
    registry=REGISTRY,
)

# ============================================================================
# Enforcement Metrics
# ============================================================================

enforcement_blocks_total = Counter(
    "yori_enforcement_blocks_total",
    "Total number of requests blocked by enforcement policies",
    ["policy_name", "reason"],
    registry=REGISTRY,
)

enforcement_allows_total = Counter(
    "yori_enforcement_allows_total",
    "Total number of requests allowed (not blocked)",
    ["action"],
    registry=REGISTRY,
)

override_attempts_total = Counter(
    "yori_override_attempts_total",
    "Total number of override attempts",
    ["success", "emergency"],
    registry=REGISTRY,
)

override_rate_limits_total = Counter(
    "yori_override_rate_limits_total",
    "Total number of override attempts rejected due to rate limiting",
    registry=REGISTRY,
)

# ============================================================================
# System Metrics
# ============================================================================

yori_info = Info(
    "yori",
    "YORI proxy server information",
    registry=REGISTRY,
)

process_memory_bytes = Gauge(
    "yori_process_memory_bytes",
    "Memory usage of the YORI process in bytes (RSS)",
    registry=REGISTRY,
)

active_connections = Gauge(
    "yori_active_connections",
    "Number of active HTTP connections",
    registry=REGISTRY,
)

http_client_pool_connections = Gauge(
    "yori_http_client_pool_connections",
    "Number of connections in the HTTP client connection pool",
    ["state"],
    registry=REGISTRY,
)

# ============================================================================
# Health Check Metrics
# ============================================================================

health_status = Gauge(
    "yori_health_status",
    "Health status of YORI components (1=healthy, 0=unhealthy)",
    ["component"],
    registry=REGISTRY,
)

health_check_duration_seconds = Histogram(
    "yori_health_check_duration_seconds",
    "Duration of health check operations",
    ["component"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=REGISTRY,
)

# ============================================================================
# Audit Database Metrics
# ============================================================================

audit_log_writes_total = Counter(
    "yori_audit_log_writes_total",
    "Total number of audit log writes",
    ["event_type", "success"],
    registry=REGISTRY,
)

audit_db_size_bytes = Gauge(
    "yori_audit_db_size_bytes",
    "Size of the audit database file in bytes",
    registry=REGISTRY,
)

# ============================================================================
# Utility Functions
# ============================================================================


def normalize_path(path: str) -> str:
    """
    Normalize request path to avoid metric cardinality explosion.

    Examples:
        /v1/chat/completions -> /v1/chat/completions
        /v1/models/gpt-4 -> /v1/models/:id
        /v1/files/file-abc123 -> /v1/files/:id
    """
    # Known API endpoints that should not be normalized
    known_endpoints = {
        "/health",
        "/metrics",
        "/yori/override",
        "/v1/chat/completions",
        "/v1/completions",
        "/v1/edits",
        "/v1/embeddings",
        "/v1/models",
        "/v1/files",
        "/v1/fine-tunes",
        "/v1/images/generations",
        "/v1/images/edits",
        "/v1/images/variations",
        "/v1/audio/transcriptions",
        "/v1/audio/translations",
        "/v1/moderations",
    }

    if path in known_endpoints:
        return path

    # Normalize paths with resource IDs
    parts = path.split("/")
    normalized_parts = []

    for i, part in enumerate(parts):
        if not part:
            continue

        # Check if this part looks like an ID
        # IDs typically contain hyphens, underscores, or are long alphanumeric strings
        is_id = (
            len(part) > 20 or
            "-" in part or
            "_" in part or
            (len(part) > 8 and part.isalnum())
        )

        # Known API path segments that should be preserved
        known_segments = {"v1", "chat", "completions", "models", "files", "edits",
                         "embeddings", "fine-tunes", "images", "audio", "moderations",
                         "generations", "variations", "transcriptions", "translations",
                         "yori", "override", "health", "metrics"}

        if part in known_segments:
            normalized_parts.append(part)
        elif is_id:
            normalized_parts.append(":id")
        else:
            normalized_parts.append(part)

    return "/" + "/".join(normalized_parts) if normalized_parts else path


def update_system_metrics():
    """Update system metrics (memory, connections, etc.)"""
    try:
        # Get current process
        process = psutil.Process(os.getpid())

        # Update memory usage
        memory_info = process.memory_info()
        process_memory_bytes.set(memory_info.rss)

        # Update connection count
        try:
            # Try new API first
            connections = process.net_connections(kind='inet')
        except AttributeError:
            # Fall back to deprecated API
            connections = process.connections(kind='inet')
        active_connections.set(len(connections))

    except Exception as e:
        # Log error but don't fail metrics collection
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update system metrics: {e}")


def initialize_info_metrics(version: str, mode: str):
    """Initialize static info metrics"""
    yori_info.info({
        "version": version,
        "mode": mode,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    })


def generate_metrics() -> bytes:
    """Generate Prometheus metrics output"""
    # Update system metrics before generating output
    update_system_metrics()

    return generate_latest(REGISTRY)


def get_content_type() -> str:
    """Get the content type for Prometheus metrics"""
    return CONTENT_TYPE_LATEST
