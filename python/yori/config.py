"""
Configuration management for YORI

Loads configuration from YAML files and provides type-safe access.
"""

from pathlib import Path
from typing import List, Literal, Dict
from pydantic import BaseModel, Field
import yaml


class EndpointConfig(BaseModel):
    """Configuration for an LLM endpoint"""

    domain: str = Field(..., description="Domain name (e.g., api.openai.com)")
    enabled: bool = Field(True, description="Whether to intercept this endpoint")


class AuditConfig(BaseModel):
    """Audit logging configuration"""

    database: Path = Field(
        default=Path("/var/db/yori/audit.db"), description="SQLite database path"
    )
    retention_days: int = Field(default=365, description="How long to keep audit logs")


class EnforcementConfig(BaseModel):
    """Enforcement mode configuration"""

    enabled: bool = Field(
        default=False, description="Whether enforcement mode is enabled (requires consent)"
    )
    consent_accepted: bool = Field(
        default=False,
        description="Whether user has accepted enforcement mode risks (required to enable)",
    )


class PolicyFileConfig(BaseModel):
    """Configuration for an individual policy file"""

    enabled: bool = Field(default=True, description="Whether this policy is enabled")
    action: Literal["allow", "alert", "block"] = Field(
        default="alert",
        description="Action to take when policy triggers (allow=pass through, alert=log only, block=deny request)",
    )


class PolicyConfig(BaseModel):
    """Policy engine configuration"""

    directory: Path = Field(
        default=Path("/usr/local/etc/yori/policies"), description="Directory containing .rego files"
    )
    default: str = Field(default="home_default.rego", description="Default policy file")
    files: Dict[str, PolicyFileConfig] = Field(
        default_factory=dict,
        description="Per-policy configuration (key is policy filename without .rego)",
    )


class EnforcementConfig(BaseModel):
    """Enforcement and override configuration"""

    override_enabled: bool = Field(
        default=True, description="Enable password-based override for blocked requests"
    )
    override_password_hash: str = Field(
        default="", description="SHA-256 hash of override password (format: sha256:hexdigest)"
    )
    override_rate_limit: int = Field(
        default=3, description="Maximum override attempts per minute per IP"
    )
    admin_token_hash: str = Field(
        default="", description="SHA-256 hash of emergency admin override token"
    )
    custom_messages: dict = Field(
        default_factory=dict, description="Custom block messages per policy name"
    )


class YoriConfig(BaseModel):
    """Main YORI configuration"""

    mode: Literal["observe", "advisory", "enforce"] = Field(
        default="observe", description="Operation mode"
    )
    listen: str = Field(default="0.0.0.0:8443", description="Listen address")

    endpoints: List[EndpointConfig] = Field(
        default_factory=lambda: [
            EndpointConfig(domain="api.openai.com", enabled=True),
            EndpointConfig(domain="api.anthropic.com", enabled=True),
            EndpointConfig(domain="gemini.google.com", enabled=True),
            EndpointConfig(domain="api.mistral.ai", enabled=True),
        ]
    )

    audit: AuditConfig = Field(default_factory=AuditConfig)
    policies: PolicyConfig = Field(default_factory=PolicyConfig)
    enforcement: EnforcementConfig = Field(default_factory=EnforcementConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "YoriConfig":
        """Load configuration from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def from_default_locations(cls) -> "YoriConfig":
        """Load configuration from default locations"""
        default_paths = [
            Path("/usr/local/etc/yori/yori.conf"),
            Path("/etc/yori/yori.conf"),
            Path("yori.conf"),
        ]

        for path in default_paths:
            if path.exists():
                return cls.from_yaml(path)

        # No config found, use defaults
        return cls()
