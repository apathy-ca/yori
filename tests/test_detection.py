"""Tests for LLM provider detection"""

import pytest
from yori.detection import (
    detect_provider,
    get_target_url,
    is_llm_endpoint,
    truncate_for_privacy,
    extract_preview,
)
from yori.models import LLMProvider


def test_detect_openai():
    """Test OpenAI provider detection"""
    assert detect_provider("api.openai.com") == LLMProvider.OPENAI
    assert detect_provider("api.openai.com", "/v1/chat/completions") == LLMProvider.OPENAI


def test_detect_anthropic():
    """Test Anthropic provider detection"""
    assert detect_provider("api.anthropic.com") == LLMProvider.ANTHROPIC
    assert detect_provider("api.anthropic.com", "/v1/messages") == LLMProvider.ANTHROPIC


def test_detect_google():
    """Test Google provider detection"""
    assert detect_provider("generativelanguage.googleapis.com") == LLMProvider.GOOGLE
    assert detect_provider("gemini.google.com") == LLMProvider.GOOGLE


def test_detect_mistral():
    """Test Mistral provider detection"""
    assert detect_provider("api.mistral.ai") == LLMProvider.MISTRAL


def test_detect_unknown():
    """Test unknown provider detection"""
    assert detect_provider("example.com") == LLMProvider.UNKNOWN
    assert detect_provider("unknown.ai") == LLMProvider.UNKNOWN


def test_detect_with_port():
    """Test provider detection with port in host"""
    assert detect_provider("api.openai.com:443") == LLMProvider.OPENAI
    assert detect_provider("api.anthropic.com:8443") == LLMProvider.ANTHROPIC


def test_get_target_url():
    """Test target URL construction"""
    url = get_target_url(LLMProvider.OPENAI, "api.openai.com", "/v1/chat/completions")
    assert url == "https://api.openai.com/v1/chat/completions"


def test_is_llm_endpoint():
    """Test LLM endpoint detection"""
    assert is_llm_endpoint("/v1/chat/completions") is True
    assert is_llm_endpoint("/v1/messages") is True
    assert is_llm_endpoint("/v1/completions") is True
    assert is_llm_endpoint("/api/random") is False
    assert is_llm_endpoint("/health") is False


def test_truncate_for_privacy():
    """Test privacy truncation"""
    short_text = "Hello world"
    assert truncate_for_privacy(short_text, max_length=50) == "Hello world"

    long_text = "a" * 300
    truncated = truncate_for_privacy(long_text, max_length=200)
    assert len(truncated) == 203  # 200 + "..."
    assert truncated.endswith("...")


def test_extract_preview():
    """Test preview extraction from body"""
    body = b"Hello world"
    preview = extract_preview(body, max_length=50)
    assert preview == "Hello world"

    long_body = b"a" * 300
    preview = extract_preview(long_body, max_length=200)
    assert len(preview) == 203  # 200 + "..."

    # Test with None
    assert extract_preview(None) is None

    # Test with empty bytes
    assert extract_preview(b"") is None
