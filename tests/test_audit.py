"""Tests for SQLite audit logging"""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

from yori.audit import AuditLogger
from yori.models import AuditEvent, LLMProvider, PolicyDecision, OperationMode


@pytest.fixture
async def audit_logger():
    """Create a temporary audit logger for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_audit.db"
        logger = AuditLogger(db_path)
        await logger.initialize()
        yield logger


@pytest.mark.asyncio
async def test_initialize_database(audit_logger):
    """Test database initialization creates schema"""
    # Database should be created by fixture
    assert audit_logger.db_path.exists()


@pytest.mark.asyncio
async def test_log_event(audit_logger):
    """Test logging an audit event"""
    event = AuditEvent(
        source_ip="192.168.1.100",
        destination="api.openai.com",
        endpoint="/v1/chat/completions",
        provider=LLMProvider.OPENAI,
        method="POST",
        request_preview="test request",
        status_code=200,
        policy_decision=PolicyDecision.ALLOW,
        mode=OperationMode.OBSERVE,
        latency_ms=125.5,
    )

    event_id = await audit_logger.log_event(event)
    assert event_id > 0


@pytest.mark.asyncio
async def test_get_events(audit_logger):
    """Test retrieving audit events"""
    # Log some test events
    for i in range(5):
        event = AuditEvent(
            source_ip=f"192.168.1.{100 + i}",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            status_code=200,
            policy_decision=PolicyDecision.ALLOW,
            mode=OperationMode.OBSERVE,
        )
        await audit_logger.log_event(event)

    # Retrieve events
    events = await audit_logger.get_events(limit=10)
    assert len(events) == 5


@pytest.mark.asyncio
async def test_get_events_with_filters(audit_logger):
    """Test retrieving events with filters"""
    # Log events with different providers
    await audit_logger.log_event(
        AuditEvent(
            source_ip="192.168.1.100",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            status_code=200,
            policy_decision=PolicyDecision.ALLOW,
            mode=OperationMode.OBSERVE,
        )
    )

    await audit_logger.log_event(
        AuditEvent(
            source_ip="192.168.1.101",
            destination="api.anthropic.com",
            endpoint="/v1/messages",
            provider=LLMProvider.ANTHROPIC,
            method="POST",
            status_code=200,
            policy_decision=PolicyDecision.BLOCK,
            mode=OperationMode.ENFORCE,
        )
    )

    # Filter by provider
    openai_events = await audit_logger.get_events(provider="openai")
    assert len(openai_events) == 1
    assert openai_events[0].provider == LLMProvider.OPENAI

    # Filter by decision
    blocked_events = await audit_logger.get_events(decision="block")
    assert len(blocked_events) == 1
    assert blocked_events[0].policy_decision == PolicyDecision.BLOCK


@pytest.mark.asyncio
async def test_get_stats(audit_logger):
    """Test retrieving statistics"""
    # Log some test events
    for i in range(3):
        await audit_logger.log_event(
            AuditEvent(
                source_ip="192.168.1.100",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                status_code=200,
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
                latency_ms=100.0 + i * 10,
            )
        )

    stats = await audit_logger.get_stats()
    assert stats.total_requests == 3
    assert stats.requests_by_provider.get("openai") == 3
    assert stats.average_latency_ms > 0


@pytest.mark.asyncio
async def test_cleanup_old_events(audit_logger):
    """Test cleaning up old events"""
    # Log an old event
    old_event = AuditEvent(
        timestamp=datetime.utcnow() - timedelta(days=400),
        source_ip="192.168.1.100",
        destination="api.openai.com",
        endpoint="/v1/chat/completions",
        provider=LLMProvider.OPENAI,
        method="POST",
        status_code=200,
        policy_decision=PolicyDecision.ALLOW,
        mode=OperationMode.OBSERVE,
    )
    await audit_logger.log_event(old_event)

    # Log a recent event
    recent_event = AuditEvent(
        source_ip="192.168.1.101",
        destination="api.openai.com",
        endpoint="/v1/chat/completions",
        provider=LLMProvider.OPENAI,
        method="POST",
        status_code=200,
        policy_decision=PolicyDecision.ALLOW,
        mode=OperationMode.OBSERVE,
    )
    await audit_logger.log_event(recent_event)

    # Clean up events older than 365 days
    deleted = await audit_logger.cleanup_old_events(retention_days=365)
    assert deleted == 1

    # Verify only recent event remains
    events = await audit_logger.get_events()
    assert len(events) == 1
