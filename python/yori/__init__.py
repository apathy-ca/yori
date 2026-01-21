"""
YORI - Zero-trust LLM governance for home networks

This package provides a lightweight LLM governance gateway for OPNsense routers,
bringing enterprise-grade security to home networks.

Example:
    >>> import yori
    >>> # Initialize policy engine
    >>> engine = yori.PolicyEngine("/usr/local/etc/yori/policies")
    >>> # Evaluate a request
    >>> result = engine.evaluate({
    ...     "user": "alice",
    ...     "endpoint": "api.openai.com",
    ...     "time": "20:00"
    ... })
"""

__version__ = "0.2.0"
__author__ = "James Henry <jamesrahenry@henrynet.ca>"

# Import Rust core components (will be available after maturin build)
try:
    from yori._core import PolicyEngine, Cache
except ImportError:
    # Rust module not built yet - provide stubs for development
    PolicyEngine = None  # type: ignore
    Cache = None  # type: ignore

# Import Python components
from yori.config import YoriConfig
from yori.proxy import ProxyServer
from yori.models import EnforcementDecision, PolicyResult
from yori.enforcement import should_enforce_policy
from yori.consent import ConsentValidator, validate_enforcement_consent

__all__ = [
    "PolicyEngine",
    "Cache",
    "YoriConfig",
    "ProxyServer",
    "EnforcementDecision",
    "PolicyResult",
    "should_enforce_policy",
    "ConsentValidator",
    "validate_enforcement_consent",
    "__version__",
    "__author__",
]
