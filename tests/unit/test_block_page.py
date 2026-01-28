"""
Unit tests for block page rendering
"""

import pytest
from datetime import datetime
from yori.models import BlockDecision
from yori.block_page import (
    render_block_page,
    get_custom_message,
    add_custom_message,
    remove_custom_message,
)


def test_render_block_page_basic():
    """Test basic block page rendering"""
    decision = BlockDecision(
        should_block=True,
        policy_name="test.rego",
        reason="Test block reason",
        timestamp=datetime(2026, 1, 20, 12, 0, 0),
        allow_override=False,
        request_id="test-request-123",
    )

    html = render_block_page(decision)

    # Verify HTML contains key elements
    assert "Request Blocked by YORI" in html
    assert "test.rego" in html
    assert "Test block reason" in html
    assert "2026-01-20 12:00:00" in html
    assert "test-request-123" in html


def test_render_block_page_with_override():
    """Test block page rendering with override option"""
    decision = BlockDecision(
        should_block=True,
        policy_name="bedtime.rego",
        reason="LLM access not allowed after 21:00",
        timestamp=datetime.now(),
        allow_override=True,
        request_id="override-test-123",
    )

    html = render_block_page(decision)

    # Verify override form is present
    assert "Override This Block" in html
    assert 'name="password"' in html
    assert 'type="password"' in html
    assert 'action="/yori/override"' in html


def test_render_block_page_without_override():
    """Test block page rendering without override option"""
    decision = BlockDecision(
        should_block=True,
        policy_name="strict.rego",
        reason="Strict policy - no overrides",
        timestamp=datetime.now(),
        allow_override=False,
    )

    html = render_block_page(decision)

    # Verify override form is NOT present
    assert "Override This Block" not in html
    assert 'name="password"' not in html


def test_render_block_page_custom_message():
    """Test block page with custom message"""
    decision = BlockDecision(
        should_block=True,
        policy_name="bedtime.rego",
        reason="LLM access not allowed after 21:00",
        timestamp=datetime.now(),
        allow_override=True,
    )

    html = render_block_page(decision)

    # Should include default custom message for bedtime.rego
    assert "after bedtime" in html.lower() or "tomorrow morning" in html.lower()


def test_render_block_page_invalid_decision():
    """Test that rendering fails for non-blocking decision"""
    decision = BlockDecision(
        should_block=False,
        policy_name="allow.rego",
        reason="Request allowed",
        timestamp=datetime.now(),
        allow_override=False,
    )

    with pytest.raises(ValueError, match="Cannot render block page for allowed request"):
        render_block_page(decision)


def test_get_custom_message():
    """Test getting custom messages"""
    # Test existing message
    message = get_custom_message("bedtime.rego")
    assert message is not None
    assert "bedtime" in message.lower() or "tomorrow" in message.lower()

    # Test non-existent message
    message = get_custom_message("nonexistent.rego")
    assert message is None


def test_add_custom_message():
    """Test adding custom messages"""
    add_custom_message("test_policy.rego", "This is a test message")

    message = get_custom_message("test_policy.rego")
    assert message == "This is a test message"

    # Cleanup
    remove_custom_message("test_policy.rego")


def test_remove_custom_message():
    """Test removing custom messages"""
    add_custom_message("temp_policy.rego", "Temporary message")
    assert get_custom_message("temp_policy.rego") is not None

    remove_custom_message("temp_policy.rego")
    assert get_custom_message("temp_policy.rego") is None


def test_render_block_page_html_escaping():
    """Test that user input is properly escaped in HTML"""
    decision = BlockDecision(
        should_block=True,
        policy_name="<script>alert('xss')</script>",
        reason="<img src=x onerror=alert('xss')>",
        timestamp=datetime.now(),
        allow_override=False,
        request_id="<script>alert('xss')</script>",
    )

    html = render_block_page(decision)

    # Verify HTML is escaped (jinja2 autoescaping)
    # The XSS attempts should be properly escaped
    assert "&lt;script&gt;" in html
    assert "&lt;img" in html or "onerror" not in html
