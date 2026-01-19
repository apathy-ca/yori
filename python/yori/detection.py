"""
LLM Provider Detection

Detects which LLM provider is being targeted based on request details.
"""

from typing import Optional
from yori.models import LLMProvider


# Provider detection mappings
PROVIDER_DOMAINS = {
    "api.openai.com": LLMProvider.OPENAI,
    "openai.com": LLMProvider.OPENAI,
    "api.anthropic.com": LLMProvider.ANTHROPIC,
    "anthropic.com": LLMProvider.ANTHROPIC,
    "generativelanguage.googleapis.com": LLMProvider.GOOGLE,
    "gemini.google.com": LLMProvider.GOOGLE,
    "api.mistral.ai": LLMProvider.MISTRAL,
    "mistral.ai": LLMProvider.MISTRAL,
}

# Common LLM API endpoints
PROVIDER_ENDPOINTS = {
    LLMProvider.OPENAI: [
        "/v1/chat/completions",
        "/v1/completions",
        "/v1/embeddings",
        "/v1/models",
    ],
    LLMProvider.ANTHROPIC: [
        "/v1/messages",
        "/v1/complete",
    ],
    LLMProvider.GOOGLE: [
        "/v1/models",
        "/v1beta/models",
    ],
    LLMProvider.MISTRAL: [
        "/v1/chat/completions",
        "/v1/embeddings",
    ],
}


def detect_provider(host: str, path: str = "") -> LLMProvider:
    """
    Detect LLM provider from request host and path.

    Args:
        host: Request host (e.g., "api.openai.com")
        path: Request path (e.g., "/v1/chat/completions")

    Returns:
        Detected LLMProvider enum value
    """
    # Remove port if present
    host_clean = host.split(":")[0].lower()

    # Check exact domain match
    if host_clean in PROVIDER_DOMAINS:
        return PROVIDER_DOMAINS[host_clean]

    # Check if domain ends with known provider domain
    for domain, provider in PROVIDER_DOMAINS.items():
        if host_clean.endswith(f".{domain}") or host_clean == domain:
            return provider

    # If path is provided, check endpoint patterns
    if path:
        path_lower = path.lower()
        for provider, endpoints in PROVIDER_ENDPOINTS.items():
            if any(path_lower.startswith(ep) for ep in endpoints):
                return provider

    return LLMProvider.UNKNOWN


def get_target_url(provider: LLMProvider, host: str, path: str) -> str:
    """
    Construct target URL for forwarding request.

    Args:
        provider: Detected provider
        host: Original request host
        path: Request path

    Returns:
        Full URL to forward request to
    """
    # Use HTTPS by default for all LLM providers
    return f"https://{host}{path}"


def is_llm_endpoint(path: str) -> bool:
    """
    Check if path looks like an LLM API endpoint.

    Args:
        path: Request path

    Returns:
        True if path appears to be an LLM endpoint
    """
    path_lower = path.lower()

    # Check against known endpoints
    for endpoints in PROVIDER_ENDPOINTS.values():
        if any(path_lower.startswith(ep) for ep in endpoints):
            return True

    # Check for common patterns
    llm_patterns = [
        "/v1/chat",
        "/v1/complete",
        "/v1/message",
        "/v1/embed",
        "/chat/completions",
        "/completions",
        "/messages",
    ]

    return any(pattern in path_lower for pattern in llm_patterns)


def truncate_for_privacy(content: str, max_length: int = 200) -> str:
    """
    Truncate content for privacy-safe logging.

    Args:
        content: Content to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated content with ellipsis if needed
    """
    if len(content) <= max_length:
        return content

    return content[:max_length] + "..."


def extract_preview(body: bytes, max_length: int = 200) -> Optional[str]:
    """
    Extract a safe preview from request/response body.

    Args:
        body: Request or response body
        max_length: Maximum preview length

    Returns:
        Safe preview string or None if extraction fails
    """
    if not body:
        return None

    try:
        # Try to decode as UTF-8
        text = body.decode("utf-8", errors="ignore")

        # Truncate for privacy
        return truncate_for_privacy(text, max_length)
    except Exception:
        # If decode fails, return None
        return None
