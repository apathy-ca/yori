"""
Unit tests for allowlist functionality
"""

import pytest
from datetime import datetime, timedelta

from yori.models import AllowlistDevice, AllowlistConfig, EnforcementConfig
from yori.config import YoriConfig
from yori.allowlist import (
    normalize_ip,
    normalize_mac,
    is_device_enabled,
    get_device_by_ip,
    get_device_by_mac,
    is_in_group,
    get_device_groups,
    is_allowlisted,
    add_device,
    remove_device,
)


class TestNormalization:
    """Test IP and MAC address normalization"""

    def test_normalize_ipv4(self):
        assert normalize_ip("192.168.1.1") == "192.168.1.1"
        assert normalize_ip("10.0.0.1") == "10.0.0.1"

    def test_normalize_ipv6(self):
        # IPv6 addresses are normalized to compressed form
        assert normalize_ip("::1") == "::1"
        assert normalize_ip("2001:0db8::1") == "2001:db8::1"

    def test_normalize_mac_various_formats(self):
        # Colon-separated
        assert normalize_mac("AA:BB:CC:DD:EE:FF") == "aa:bb:cc:dd:ee:ff"
        # Dash-separated
        assert normalize_mac("AA-BB-CC-DD-EE-FF") == "aa:bb:cc:dd:ee:ff"
        # Dot-separated (Cisco format)
        assert normalize_mac("AABB.CCDD.EEFF") == "aa:bb:cc:dd:ee:ff"
        # No separators
        assert normalize_mac("AABBCCDDEEFF") == "aa:bb:cc:dd:ee:ff"

    def test_normalize_mac_invalid(self):
        assert normalize_mac("invalid") is None
        assert normalize_mac("AA:BB:CC") is None
        assert normalize_mac(None) is None


class TestDeviceEnabled:
    """Test device enabled status checking"""

    def test_permanent_device_always_enabled(self):
        device = AllowlistDevice(
            ip="192.168.1.1",
            name="Test",
            permanent=True,
            enabled=False,  # Even if disabled
        )
        assert is_device_enabled(device) is True

    def test_disabled_device(self):
        device = AllowlistDevice(
            ip="192.168.1.1",
            name="Test",
            enabled=False,
        )
        assert is_device_enabled(device) is False

    def test_enabled_device(self):
        device = AllowlistDevice(
            ip="192.168.1.1",
            name="Test",
            enabled=True,
        )
        assert is_device_enabled(device) is True

    def test_expired_temporary_allowlist(self):
        device = AllowlistDevice(
            ip="192.168.1.1",
            name="Test",
            enabled=True,
            expires_at=datetime.now() - timedelta(hours=1),  # Expired 1 hour ago
        )
        assert is_device_enabled(device) is False

    def test_valid_temporary_allowlist(self):
        device = AllowlistDevice(
            ip="192.168.1.1",
            name="Test",
            enabled=True,
            expires_at=datetime.now() + timedelta(hours=1),  # Expires in 1 hour
        )
        assert is_device_enabled(device) is True


class TestDeviceLookup:
    """Test device lookup by IP and MAC"""

    def test_get_device_by_ip(self):
        config = AllowlistConfig(
            devices=[
                AllowlistDevice(ip="192.168.1.100", name="Device1", enabled=True),
                AllowlistDevice(ip="192.168.1.101", name="Device2", enabled=True),
            ]
        )

        device = get_device_by_ip(config, "192.168.1.100")
        assert device is not None
        assert device.name == "Device1"

    def test_get_device_by_ip_not_found(self):
        config = AllowlistConfig(
            devices=[
                AllowlistDevice(ip="192.168.1.100", name="Device1", enabled=True),
            ]
        )

        device = get_device_by_ip(config, "192.168.1.200")
        assert device is None

    def test_get_device_by_ip_disabled(self):
        config = AllowlistConfig(
            devices=[
                AllowlistDevice(ip="192.168.1.100", name="Device1", enabled=False),
            ]
        )

        device = get_device_by_ip(config, "192.168.1.100")
        assert device is None

    def test_get_device_by_mac(self):
        config = AllowlistConfig(
            devices=[
                AllowlistDevice(
                    ip="192.168.1.100",
                    name="Device1",
                    mac="aa:bb:cc:dd:ee:ff",
                    enabled=True,
                ),
            ]
        )

        device = get_device_by_mac(config, "AA:BB:CC:DD:EE:FF")
        assert device is not None
        assert device.name == "Device1"

    def test_get_device_by_mac_different_format(self):
        config = AllowlistConfig(
            devices=[
                AllowlistDevice(
                    ip="192.168.1.100",
                    name="Device1",
                    mac="aa:bb:cc:dd:ee:ff",
                    enabled=True,
                ),
            ]
        )

        # Test different MAC formats
        device = get_device_by_mac(config, "AA-BB-CC-DD-EE-FF")
        assert device is not None
        assert device.name == "Device1"


class TestGroups:
    """Test device group functionality"""

    def test_is_in_group(self):
        config = AllowlistConfig(
            groups=[
                {
                    "name": "family",
                    "device_ips": ["192.168.1.100", "192.168.1.101"],
                    "enabled": True,
                }
            ]
        )

        assert is_in_group(config, "192.168.1.100", "family") is True
        assert is_in_group(config, "192.168.1.101", "family") is True
        assert is_in_group(config, "192.168.1.200", "family") is False

    def test_is_in_group_disabled(self):
        config = AllowlistConfig(
            groups=[
                {
                    "name": "family",
                    "device_ips": ["192.168.1.100"],
                    "enabled": False,
                }
            ]
        )

        assert is_in_group(config, "192.168.1.100", "family") is False

    def test_get_device_groups(self):
        config = AllowlistConfig(
            groups=[
                {
                    "name": "family",
                    "device_ips": ["192.168.1.100", "192.168.1.101"],
                    "enabled": True,
                },
                {
                    "name": "work",
                    "device_ips": ["192.168.1.100", "192.168.1.200"],
                    "enabled": True,
                },
            ]
        )

        groups = get_device_groups(config, "192.168.1.100")
        assert "family" in groups
        assert "work" in groups
        assert len(groups) == 2


class TestAllowlistChecking:
    """Test main allowlist checking function"""

    def test_is_allowlisted_by_ip(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(ip="192.168.1.100", name="Test Device", enabled=True)
                    ]
                )
            )
        )

        is_allowed, device = is_allowlisted("192.168.1.100", config)
        assert is_allowed is True
        assert device is not None
        assert device.name == "Test Device"

    def test_is_allowlisted_by_mac(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(
                            ip="192.168.1.100",
                            name="Test Device",
                            mac="aa:bb:cc:dd:ee:ff",
                            enabled=True,
                        )
                    ]
                )
            )
        )

        is_allowed, device = is_allowlisted(
            "192.168.1.200", config, client_mac="AA:BB:CC:DD:EE:FF"
        )
        assert is_allowed is True
        assert device is not None
        assert device.name == "Test Device"

    def test_not_allowlisted(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(ip="192.168.1.100", name="Test Device", enabled=True)
                    ]
                )
            )
        )

        is_allowed, device = is_allowlisted("192.168.1.200", config)
        assert is_allowed is False
        assert device is None

    def test_no_enforcement_config(self):
        config = YoriConfig()

        is_allowed, device = is_allowlisted("192.168.1.100", config)
        assert is_allowed is False
        assert device is None


class TestDeviceManagement:
    """Test adding and removing devices"""

    def test_add_device(self):
        config = YoriConfig()

        device = add_device(config, "192.168.1.100", "Test Device", mac="AA:BB:CC:DD:EE:FF")

        assert device.ip == "192.168.1.100"
        assert device.name == "Test Device"
        assert device.mac == "aa:bb:cc:dd:ee:ff"
        assert len(config.enforcement.allowlist.devices) == 1

    def test_add_device_with_group(self):
        config = YoriConfig()

        device = add_device(config, "192.168.1.100", "Test Device", group="family")

        assert device.group == "family"

    def test_add_temporary_device(self):
        config = YoriConfig()
        expires = datetime.now() + timedelta(hours=1)

        device = add_device(config, "192.168.1.100", "Guest", expires_at=expires)

        assert device.expires_at == expires

    def test_remove_device(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    devices=[
                        AllowlistDevice(ip="192.168.1.100", name="Test Device", enabled=True)
                    ]
                )
            )
        )

        result = remove_device(config, "192.168.1.100")
        assert result is True
        assert len(config.enforcement.allowlist.devices) == 0

    def test_remove_device_not_found(self):
        config = YoriConfig()

        result = remove_device(config, "192.168.1.200")
        assert result is False
