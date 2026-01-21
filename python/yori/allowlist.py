"""
Allowlist management and checking

Handles device allowlisting to bypass enforcement for trusted devices.
"""

from datetime import datetime
from typing import Optional, List, Tuple
from ipaddress import ip_address, IPv4Address, IPv6Address
import logging

from yori.models import AllowlistDevice, AllowlistGroup, AllowlistConfig, RecentDevice
from yori.config import YoriConfig

logger = logging.getLogger(__name__)


def normalize_ip(ip: str) -> str:
    """
    Normalize IP address to standard format

    Args:
        ip: IP address string (IPv4 or IPv6)

    Returns:
        Normalized IP address string
    """
    try:
        addr = ip_address(ip)
        return str(addr)
    except ValueError:
        logger.warning(f"Invalid IP address format: {ip}")
        return ip


def normalize_mac(mac: Optional[str]) -> Optional[str]:
    """
    Normalize MAC address to standard format (lowercase, colon-separated)

    Args:
        mac: MAC address string (various formats accepted)

    Returns:
        Normalized MAC address (aa:bb:cc:dd:ee:ff) or None
    """
    if not mac:
        return None

    # Remove common separators
    mac_clean = mac.replace(":", "").replace("-", "").replace(".", "").lower()

    # Validate length
    if len(mac_clean) != 12:
        logger.warning(f"Invalid MAC address format: {mac}")
        return None

    # Format as colon-separated
    return ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))


def is_device_enabled(device: AllowlistDevice) -> bool:
    """
    Check if an allowlist device is currently active

    Args:
        device: Allowlist device configuration

    Returns:
        True if device is enabled and not expired
    """
    # Permanent devices are always enabled
    if device.permanent:
        return True

    # Check if device is explicitly disabled
    if not device.enabled:
        return False

    # Check if temporary allowlist has expired
    if device.expires_at and datetime.now() >= device.expires_at:
        logger.info(f"Temporary allowlist expired for device: {device.name} ({device.ip})")
        return False

    return True


def get_device_by_ip(config: AllowlistConfig, ip: str) -> Optional[AllowlistDevice]:
    """
    Find an allowlist device by IP address

    Args:
        config: Allowlist configuration
        ip: IP address to search for

    Returns:
        AllowlistDevice if found and enabled, None otherwise
    """
    normalized_ip = normalize_ip(ip)

    for device in config.devices:
        if normalize_ip(device.ip) == normalized_ip and is_device_enabled(device):
            return device

    return None


def get_device_by_mac(config: AllowlistConfig, mac: str) -> Optional[AllowlistDevice]:
    """
    Find an allowlist device by MAC address

    Args:
        config: Allowlist configuration
        mac: MAC address to search for

    Returns:
        AllowlistDevice if found and enabled, None otherwise
    """
    normalized_mac = normalize_mac(mac)
    if not normalized_mac:
        return None

    for device in config.devices:
        if device.mac and normalize_mac(device.mac) == normalized_mac and is_device_enabled(device):
            return device

    return None


def is_in_group(config: AllowlistConfig, ip: str, group_name: str) -> bool:
    """
    Check if an IP address is in a specific allowlist group

    Args:
        config: Allowlist configuration
        ip: IP address to check
        group_name: Name of the group to check

    Returns:
        True if IP is in the group and group is enabled
    """
    normalized_ip = normalize_ip(ip)

    for group in config.groups:
        if group.name == group_name and group.enabled:
            if normalized_ip in [normalize_ip(g_ip) for g_ip in group.device_ips]:
                return True

    return False


def get_device_groups(config: AllowlistConfig, ip: str) -> List[str]:
    """
    Get all groups that a device belongs to

    Args:
        config: Allowlist configuration
        ip: IP address to check

    Returns:
        List of group names
    """
    normalized_ip = normalize_ip(ip)
    groups = []

    for group in config.groups:
        if group.enabled and normalized_ip in [normalize_ip(g_ip) for g_ip in group.device_ips]:
            groups.append(group.name)

    return groups


def is_allowlisted(client_ip: str, config: YoriConfig, client_mac: Optional[str] = None) -> Tuple[bool, Optional[AllowlistDevice]]:
    """
    Check if a client IP/MAC is on the allowlist

    This is the main entry point for allowlist checking. Checks both IP and MAC address
    if available.

    Args:
        client_ip: Client IP address
        config: Full YORI configuration
        client_mac: Client MAC address (optional)

    Returns:
        Tuple of (is_allowlisted, device_config)
        - is_allowlisted: True if device should bypass enforcement
        - device_config: AllowlistDevice if found, None otherwise
    """
    if not config.enforcement or not config.enforcement.allowlist:
        return False, None

    allowlist_config = config.enforcement.allowlist

    # Check by IP address first
    device = get_device_by_ip(allowlist_config, client_ip)
    if device:
        logger.info(f"Device allowlisted by IP: {device.name} ({client_ip})")
        return True, device

    # Check by MAC address if provided
    if client_mac:
        device = get_device_by_mac(allowlist_config, client_mac)
        if device:
            logger.info(f"Device allowlisted by MAC: {device.name} ({client_mac})")
            return True, device

    return False, None


def add_device(config: YoriConfig, ip: str, name: str, mac: Optional[str] = None,
               permanent: bool = False, group: Optional[str] = None,
               expires_at: Optional[datetime] = None, notes: Optional[str] = None) -> AllowlistDevice:
    """
    Add a device to the allowlist

    Args:
        config: Full YORI configuration
        ip: Device IP address
        name: Human-readable device name
        mac: MAC address (optional)
        permanent: Whether this is a permanent allowlist entry
        group: Group membership (optional)
        expires_at: Expiration time for temporary entries (optional)
        notes: Admin notes (optional)

    Returns:
        Newly created AllowlistDevice
    """
    device = AllowlistDevice(
        ip=normalize_ip(ip),
        name=name,
        mac=normalize_mac(mac) if mac else None,
        permanent=permanent,
        group=group,
        expires_at=expires_at,
        notes=notes
    )

    if not config.enforcement:
        from yori.models import EnforcementConfig
        config.enforcement = EnforcementConfig()

    config.enforcement.allowlist.devices.append(device)
    logger.info(f"Added device to allowlist: {name} ({ip})")

    return device


def remove_device(config: YoriConfig, ip: str) -> bool:
    """
    Remove a device from the allowlist

    Args:
        config: Full YORI configuration
        ip: Device IP address to remove

    Returns:
        True if device was removed, False if not found
    """
    if not config.enforcement or not config.enforcement.allowlist:
        return False

    normalized_ip = normalize_ip(ip)
    devices = config.enforcement.allowlist.devices

    for i, device in enumerate(devices):
        if normalize_ip(device.ip) == normalized_ip:
            removed_device = devices.pop(i)
            logger.info(f"Removed device from allowlist: {removed_device.name} ({ip})")
            return True

    return False


def list_recent_devices(config: YoriConfig, limit: int = 50) -> List[RecentDevice]:
    """
    List recently seen devices for discovery

    This would typically pull from audit logs to show devices that have made requests.
    For now, returns an empty list (to be implemented with audit integration).

    Args:
        config: Full YORI configuration
        limit: Maximum number of devices to return

    Returns:
        List of recently seen devices
    """
    # TODO: Integrate with audit database to get recent devices
    # This will be implemented when Worker 12 (enhanced-audit) is complete
    return []
