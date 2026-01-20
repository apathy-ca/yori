"""
Comprehensive async tests for YORI audit logging
Tests with real aiosqlite database operations
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from yori.audit import AuditLogger
from yori.models import AuditEvent, PolicyDecision, OperationMode, LLMProvider


@pytest.mark.asyncio
class TestAuditLoggerAsync:
    """Async tests for AuditLogger"""

    async def test_initialize_creates_schema(self, temp_db):
        """Test that initialize creates database schema"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Verify database file exists and has content
        assert temp_db.exists()
        assert temp_db.stat().st_size > 0

    async def test_log_single_event(self, temp_db):
        """Test logging a single event"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        event = AuditEvent(
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            request_preview="Test request",
            response_preview="Test response",
            status_code=200,
            policy_decision=PolicyDecision.ALLOW,
            policy_name="default",
            mode=OperationMode.OBSERVE,
            latency_ms=12.5,
        )

        event_id = await logger.log_event(event)
        assert event_id is not None
        assert event_id > 0

    async def test_log_multiple_events(self, temp_db):
        """Test logging multiple events"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Log 10 events
        event_ids = []
        for i in range(10):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip=f"192.168.1.{100+i}",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
            )
            event_id = await logger.log_event(event)
            event_ids.append(event_id)

        # All events should have unique IDs
        assert len(event_ids) == 10
        assert len(set(event_ids)) == 10

    async def test_get_events_no_filters(self, temp_db):
        """Test getting events without filters"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Log some events
        for i in range(5):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip="192.168.1.100",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
            )
            await logger.log_event(event)

        # Get events
        events = await logger.get_events(limit=10)
        assert len(events) == 5
        assert all(isinstance(e, AuditEvent) for e in events)

    async def test_get_events_with_provider_filter(self, temp_db):
        """Test filtering events by provider"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Log OpenAI events
        for i in range(3):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip="192.168.1.100",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
            )
            await logger.log_event(event)

        # Log Anthropic events
        for i in range(2):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip="192.168.1.100",
                destination="api.anthropic.com",
                endpoint="/v1/messages",
                provider=LLMProvider.ANTHROPIC,
                method="POST",
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
            )
            await logger.log_event(event)

        # Filter by OpenAI
        openai_events = await logger.get_events(provider="openai")
        assert len(openai_events) == 3

    async def test_get_events_with_decision_filter(self, temp_db):
        """Test filtering events by policy decision"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Log allowed events
        for i in range(4):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip="192.168.1.100",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
            )
            await logger.log_event(event)

        # Log blocked events
        for i in range(2):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip="192.168.1.100",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                policy_decision=PolicyDecision.BLOCK,
                mode=OperationMode.ENFORCE,
            )
            await logger.log_event(event)

        # Filter by blocked
        blocked_events = await logger.get_events(decision="block")
        assert len(blocked_events) == 2

    async def test_get_events_pagination(self, temp_db):
        """Test event pagination"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Log 20 events
        for i in range(20):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip="192.168.1.100",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
            )
            await logger.log_event(event)

        # Get first page
        page1 = await logger.get_events(limit=10, offset=0)
        assert len(page1) == 10

        # Get second page
        page2 = await logger.get_events(limit=10, offset=10)
        assert len(page2) == 10

        # No overlap
        page1_ids = [e.id for e in page1]
        page2_ids = [e.id for e in page2]
        assert len(set(page1_ids) & set(page2_ids)) == 0

    async def test_get_stats(self, temp_db):
        """Test getting statistics"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Log mixed events
        for i in range(5):
            event = AuditEvent(
                timestamp=datetime.now(),
                source_ip="192.168.1.100",
                destination="api.openai.com",
                endpoint="/v1/chat/completions",
                provider=LLMProvider.OPENAI,
                method="POST",
                policy_decision=PolicyDecision.ALLOW,
                mode=OperationMode.OBSERVE,
                latency_ms=10.0 + i,
            )
            await logger.log_event(event)

        stats = await logger.get_stats()
        assert stats.total_requests == 5
        assert stats.average_latency_ms > 0

    async def test_cleanup_old_events(self, temp_db):
        """Test cleaning up old events"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        # Log old event (400 days ago)
        old_event = AuditEvent(
            timestamp=datetime.now() - timedelta(days=400),
            source_ip="192.168.1.100",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            policy_decision=PolicyDecision.ALLOW,
            mode=OperationMode.OBSERVE,
        )
        await logger.log_event(old_event)

        # Log recent event
        recent_event = AuditEvent(
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            policy_decision=PolicyDecision.ALLOW,
            mode=OperationMode.OBSERVE,
        )
        await logger.log_event(recent_event)

        # Cleanup with 365 day retention
        deleted = await logger.cleanup_old_events(retention_days=365)
        assert deleted == 1

        # Verify only recent event remains
        events = await logger.get_events(limit=100)
        assert len(events) == 1

    async def test_event_with_metadata(self, temp_db):
        """Test event with metadata"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        event = AuditEvent(
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            policy_decision=PolicyDecision.ALLOW,
            mode=OperationMode.OBSERVE,
            metadata={"model": "gpt-4", "tokens": 150},
        )

        await logger.log_event(event)

        events = await logger.get_events(limit=1)
        assert len(events) == 1
        assert events[0].metadata == {"model": "gpt-4", "tokens": 150}

    async def test_event_with_error(self, temp_db):
        """Test logging event with error"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        event = AuditEvent(
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            policy_decision=PolicyDecision.ALLOW,
            mode=OperationMode.OBSERVE,
            error="Connection timeout",
        )

        await logger.log_event(event)

        events = await logger.get_events(limit=1)
        assert len(events) == 1
        assert events[0].error == "Connection timeout"

    async def test_memory_database(self, temp_db):
        """Test using temporary database like memory"""
        logger = AuditLogger(temp_db)
        await logger.initialize()

        event = AuditEvent(
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination="api.openai.com",
            endpoint="/v1/chat/completions",
            provider=LLMProvider.OPENAI,
            method="POST",
            policy_decision=PolicyDecision.ALLOW,
            mode=OperationMode.OBSERVE,
        )

        await logger.log_event(event)

        events = await logger.get_events()
        assert len(events) == 1
