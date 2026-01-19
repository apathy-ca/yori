"""
Pydantic models for YORI

Data models for requests, responses, and internal state.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class OperationMode(str, Enum):
    """YORI operation modes"""

    OBSERVE = "observe"  # Log only, no blocking
    ADVISORY = "advisory"  # Log and warn, no blocking
    ENFORCE = "enforce"  # Log and block policy violations


class PolicyDecision(str, Enum):
    """Policy evaluation decisions"""

    ALLOW = "allow"
    ALERT = "alert"
    BLOCK = "block"


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    UNKNOWN = "unknown"


class PolicyResult(BaseModel):
    """Result of policy evaluation"""

    decision: PolicyDecision
    policy_name: str
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    """Audit log event"""

    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    source_ip: str
    destination: str
    endpoint: str
    provider: LLMProvider
    method: str
    request_preview: Optional[str] = None  # Truncated for privacy
    response_preview: Optional[str] = None  # Truncated for privacy
    status_code: Optional[int] = None
    policy_decision: PolicyDecision
    policy_name: Optional[str] = None
    mode: OperationMode
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class ProxyRequest(BaseModel):
    """Parsed proxy request"""

    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[bytes] = None
    provider: LLMProvider
    source_ip: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProxyResponse(BaseModel):
    """Proxy response"""

    status_code: int
    headers: Dict[str, str]
    body: bytes
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(BaseModel):
    """Health check response"""

    status: str
    version: str = "0.1.0"
    mode: Optional[OperationMode] = None
    endpoints: Optional[int] = None
    uptime_seconds: Optional[float] = None


class StatsResponse(BaseModel):
    """Statistics response for dashboard"""

    total_requests: int
    requests_by_provider: Dict[str, int]
    requests_by_decision: Dict[str, int]
    average_latency_ms: float
    period_start: datetime
    period_end: datetime
