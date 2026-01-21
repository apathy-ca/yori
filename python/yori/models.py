"""
Data models for YORI allowlist, time exceptions, and emergency override

Defines Pydantic models for configuration and runtime data structures.
"""

from datetime import datetime, time
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from ipaddress import IPv4Address, IPv6Address


class AllowlistDevice(BaseModel):
    """A device on the allowlist that bypasses enforcement"""

    ip: str = Field(..., description="Device IP address")
    name: str = Field(..., description="Human-readable device name")
    mac: Optional[str] = Field(None, description="MAC address (aa:bb:cc:dd:ee:ff)")
    enabled: bool = Field(True, description="Whether this allowlist entry is active")
    permanent: bool = Field(False, description="Never block this device, even if disabled")
    group: Optional[str] = Field(None, description="Group membership (e.g., 'family', 'work')")
    expires_at: Optional[datetime] = Field(None, description="Temporary allowlist expiration")
    added_at: datetime = Field(default_factory=datetime.now, description="When device was added")
    notes: Optional[str] = Field(None, description="Admin notes about this device")


class AllowlistGroup(BaseModel):
    """A group of devices for easier management"""

    name: str = Field(..., description="Group name (e.g., 'family', 'work_devices')")
    description: Optional[str] = Field(None, description="Group description")
    device_ips: List[str] = Field(default_factory=list, description="IP addresses in this group")
    enabled: bool = Field(True, description="Whether this group is active")


class TimeException(BaseModel):
    """Time-based exception that allows access during specific hours"""

    name: str = Field(..., description="Exception name (e.g., 'homework_hours')")
    description: Optional[str] = Field(None, description="Human-readable description")
    days: List[Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]] = Field(
        ..., description="Days of week when this exception applies"
    )
    start_time: str = Field(..., description="Start time in HH:MM format (24-hour)")
    end_time: str = Field(..., description="End time in HH:MM format (24-hour)")
    device_ips: List[str] = Field(default_factory=list, description="Devices this exception applies to")
    enabled: bool = Field(True, description="Whether this exception is active")


class EmergencyOverride(BaseModel):
    """Emergency override configuration to disable all enforcement"""

    enabled: bool = Field(False, description="Whether emergency override is currently active")
    password_hash: Optional[str] = Field(None, description="SHA-256 hash of admin password")
    activated_at: Optional[datetime] = Field(None, description="When override was activated")
    activated_by: Optional[str] = Field(None, description="IP address that activated override")
    require_password: bool = Field(True, description="Whether password is required to activate")


class AllowlistConfig(BaseModel):
    """Complete allowlist configuration"""

    devices: List[AllowlistDevice] = Field(default_factory=list, description="Allowlisted devices")
    groups: List[AllowlistGroup] = Field(default_factory=list, description="Device groups")
    time_exceptions: List[TimeException] = Field(default_factory=list, description="Time-based exceptions")


class EnforcementConfig(BaseModel):
    """Enforcement mode configuration"""

    enabled: bool = Field(False, description="Whether enforcement mode is active")
    consent_accepted: bool = Field(False, description="Whether user has accepted consent warning")
    allowlist: AllowlistConfig = Field(default_factory=AllowlistConfig, description="Allowlist configuration")
    emergency_override: EmergencyOverride = Field(
        default_factory=EmergencyOverride, description="Emergency override settings"
    )


class PolicyResult(BaseModel):
    """Result from policy evaluation"""

    allowed: bool = Field(..., description="Whether the request is allowed by policy")
    policy_name: str = Field(..., description="Name of the policy that was evaluated")
    reason: Optional[str] = Field(None, description="Reason for the decision")
    violations: List[str] = Field(default_factory=list, description="List of policy violations")


class EnforcementDecision(BaseModel):
    """Decision about whether to enforce a policy result"""

    enforce: bool = Field(..., description="Whether to actually block the request")
    reason: str = Field(..., description="Reason for the enforcement decision")
    bypass_type: Optional[Literal["allowlist", "time_exception", "emergency_override"]] = Field(
        None, description="Type of bypass if enforcement was skipped"
    )
    device_name: Optional[str] = Field(None, description="Name of device that bypassed enforcement")


class RecentDevice(BaseModel):
    """A recently seen device for discovery"""

    ip: str = Field(..., description="Device IP address")
    mac: Optional[str] = Field(None, description="MAC address if available")
    hostname: Optional[str] = Field(None, description="Hostname if available")
    last_seen: datetime = Field(default_factory=datetime.now, description="When device was last seen")
    request_count: int = Field(0, description="Number of requests from this device")
    on_allowlist: bool = Field(False, description="Whether device is already allowlisted")
