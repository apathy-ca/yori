#!/usr/bin/env python3
"""
YORI Command Line Interface

Utility for managing allowlist, time exceptions, and emergency override from the command line.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import yaml

from yori.config import YoriConfig
from yori.allowlist import (
    add_device,
    remove_device,
    is_allowlisted,
    get_device_groups,
)
from yori.time_exceptions import (
    add_exception,
    remove_exception,
    check_any_exception_active,
    list_active_exceptions,
)
from yori.emergency import (
    activate_override,
    deactivate_override,
    set_override_password,
    get_override_status,
    is_emergency_override_active,
)


def load_config(config_path: Optional[str] = None) -> YoriConfig:
    """Load YORI configuration"""
    if config_path:
        return YoriConfig.from_yaml(Path(config_path))
    return YoriConfig.from_default_locations()


def save_config(config: YoriConfig, config_path: Optional[str] = None):
    """Save YORI configuration"""
    path = Path(config_path) if config_path else Path("yori.conf")

    # Convert config to dict
    config_dict = config.model_dump(exclude_none=True)

    with open(path, 'w') as f:
        yaml.safe_dump(config_dict, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Configuration saved to {path}")


def cmd_allowlist_add(args):
    """Add device to allowlist"""
    config = load_config(args.config)

    # Parse expiration time if provided
    expires_at = None
    if args.expires:
        if args.expires.endswith('h'):
            hours = int(args.expires[:-1])
            expires_at = datetime.now() + timedelta(hours=hours)
        elif args.expires.endswith('d'):
            days = int(args.expires[:-1])
            expires_at = datetime.now() + timedelta(days=days)
        else:
            print(f"✗ Invalid expiration format: {args.expires}")
            print("  Use format like '1h' for 1 hour or '1d' for 1 day")
            return 1

    device = add_device(
        config,
        ip=args.ip,
        name=args.name,
        mac=args.mac,
        permanent=args.permanent,
        group=args.group,
        expires_at=expires_at,
        notes=args.notes,
    )

    save_config(config, args.config)

    print(f"✓ Added device to allowlist:")
    print(f"  Name: {device.name}")
    print(f"  IP: {device.ip}")
    if device.mac:
        print(f"  MAC: {device.mac}")
    if device.permanent:
        print(f"  Status: PERMANENT (never blocked)")
    elif device.expires_at:
        print(f"  Expires: {device.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if device.group:
        print(f"  Group: {device.group}")

    return 0


def cmd_allowlist_remove(args):
    """Remove device from allowlist"""
    config = load_config(args.config)

    success = remove_device(config, args.ip)

    if success:
        save_config(config, args.config)
        print(f"✓ Removed device {args.ip} from allowlist")
        return 0
    else:
        print(f"✗ Device {args.ip} not found in allowlist")
        return 1


def cmd_allowlist_list(args):
    """List allowlisted devices"""
    config = load_config(args.config)

    if not config.enforcement or not config.enforcement.allowlist.devices:
        print("No devices in allowlist")
        return 0

    print("Allowlisted Devices:")
    print("-" * 80)

    for device in config.enforcement.allowlist.devices:
        status = "ENABLED" if device.enabled else "DISABLED"
        if device.permanent:
            status = "PERMANENT"
        elif device.expires_at and device.expires_at < datetime.now():
            status = "EXPIRED"

        print(f"• {device.name}")
        print(f"  IP: {device.ip:20} MAC: {device.mac or 'N/A'}")
        print(f"  Status: {status:15} Group: {device.group or 'N/A'}")
        if device.expires_at:
            print(f"  Expires: {device.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if device.notes:
            print(f"  Notes: {device.notes}")
        print()

    return 0


def cmd_allowlist_check(args):
    """Check if IP is allowlisted"""
    config = load_config(args.config)

    is_allowed, device = is_allowlisted(args.ip, config, args.mac)

    if is_allowed and device:
        print(f"✓ {args.ip} is ALLOWLISTED")
        print(f"  Device: {device.name}")
        if device.mac:
            print(f"  MAC: {device.mac}")
        if device.group:
            print(f"  Group: {device.group}")
        return 0
    else:
        print(f"✗ {args.ip} is NOT allowlisted")
        return 1


def cmd_time_add(args):
    """Add time-based exception"""
    config = load_config(args.config)

    # Parse days
    days = [d.strip().lower() for d in args.days.split(',')]

    # Parse device IPs
    device_ips = [ip.strip() for ip in args.devices.split(',')]

    exception = add_exception(
        config,
        name=args.name,
        description=args.description,
        days=days,
        start_time=args.start,
        end_time=args.end,
        device_ips=device_ips,
    )

    save_config(config, args.config)

    print(f"✓ Added time exception:")
    print(f"  Name: {exception.name}")
    print(f"  Days: {', '.join(exception.days)}")
    print(f"  Time: {exception.start_time} - {exception.end_time}")
    print(f"  Devices: {', '.join(exception.device_ips)}")

    return 0


def cmd_time_remove(args):
    """Remove time-based exception"""
    config = load_config(args.config)

    success = remove_exception(config, args.name)

    if success:
        save_config(config, args.config)
        print(f"✓ Removed time exception: {args.name}")
        return 0
    else:
        print(f"✗ Time exception not found: {args.name}")
        return 1


def cmd_time_list(args):
    """List time-based exceptions"""
    config = load_config(args.config)

    if not config.enforcement or not config.enforcement.allowlist.time_exceptions:
        print("No time exceptions configured")
        return 0

    print("Time-Based Exceptions:")
    print("-" * 80)

    now = datetime.now()
    active_exceptions = list_active_exceptions(config, now)
    active_names = {e.name for e in active_exceptions}

    for exception in config.enforcement.allowlist.time_exceptions:
        status = "ACTIVE NOW" if exception.name in active_names else ("ENABLED" if exception.enabled else "DISABLED")

        print(f"• {exception.name} [{status}]")
        if exception.description:
            print(f"  {exception.description}")
        print(f"  Days: {', '.join(exception.days)}")
        print(f"  Time: {exception.start_time} - {exception.end_time}")
        print(f"  Devices: {', '.join(exception.device_ips) if exception.device_ips else 'All devices'}")
        print()

    return 0


def cmd_emergency_activate(args):
    """Activate emergency override"""
    config = load_config(args.config)

    if is_emergency_override_active(config):
        print("⚠ Emergency override is already active!")
        return 1

    success, message = activate_override(
        config,
        password=args.password,
        activated_by=args.activated_by or "CLI",
    )

    if success:
        save_config(config, args.config)
        print(f"✓ {message}")
        print("⚠ WARNING: All enforcement is now DISABLED")
        return 0
    else:
        print(f"✗ {message}")
        return 1


def cmd_emergency_deactivate(args):
    """Deactivate emergency override"""
    config = load_config(args.config)

    if not is_emergency_override_active(config):
        print("Emergency override is not active")
        return 1

    success, message = deactivate_override(config, password=args.password)

    if success:
        save_config(config, args.config)
        print(f"✓ {message}")
        print("✓ Enforcement is now re-enabled")
        return 0
    else:
        print(f"✗ {message}")
        return 1


def cmd_emergency_status(args):
    """Show emergency override status"""
    config = load_config(args.config)

    status = get_override_status(config)

    print("Emergency Override Status:")
    print("-" * 80)

    if status['enabled']:
        print("Status: ⚠ ACTIVE - All enforcement DISABLED")
        if status.get('activated_at'):
            print(f"Activated: {status['activated_at']}")
        if status.get('activated_by'):
            print(f"Activated by: {status['activated_by']}")
    else:
        print("Status: Inactive - Enforcement is active")

    print(f"Password required: {'Yes' if status['require_password'] else 'No'}")
    print(f"Password configured: {'Yes' if status.get('has_password') else 'No'}")

    return 0


def cmd_emergency_setpassword(args):
    """Set emergency override password"""
    config = load_config(args.config)

    set_override_password(config, args.password)
    save_config(config, args.config)

    print("✓ Emergency override password updated")
    print("  Password is stored as SHA-256 hash")

    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="YORI Allowlist Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--config',
        help='Path to yori.conf (default: auto-detect)',
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Allowlist commands
    allowlist = subparsers.add_parser('allowlist', help='Manage device allowlist')
    allowlist_cmds = allowlist.add_subparsers(dest='action')

    # allowlist add
    add_parser = allowlist_cmds.add_parser('add', help='Add device to allowlist')
    add_parser.add_argument('ip', help='Device IP address')
    add_parser.add_argument('name', help='Device name')
    add_parser.add_argument('--mac', help='MAC address (optional)')
    add_parser.add_argument('--permanent', action='store_true', help='Permanent allowlist (never block)')
    add_parser.add_argument('--group', help='Device group (e.g., family, work)')
    add_parser.add_argument('--expires', help='Expiration (e.g., 1h, 1d, 7d)')
    add_parser.add_argument('--notes', help='Admin notes')

    # allowlist remove
    remove_parser = allowlist_cmds.add_parser('remove', help='Remove device from allowlist')
    remove_parser.add_argument('ip', help='Device IP address')

    # allowlist list
    allowlist_cmds.add_parser('list', help='List allowlisted devices')

    # allowlist check
    check_parser = allowlist_cmds.add_parser('check', help='Check if IP is allowlisted')
    check_parser.add_argument('ip', help='IP address to check')
    check_parser.add_argument('--mac', help='MAC address (optional)')

    # Time exception commands
    time = subparsers.add_parser('time', help='Manage time-based exceptions')
    time_cmds = time.add_subparsers(dest='action')

    # time add
    time_add = time_cmds.add_parser('add', help='Add time-based exception')
    time_add.add_argument('name', help='Exception name')
    time_add.add_argument('--description', help='Description')
    time_add.add_argument('--days', required=True, help='Days (comma-separated, e.g., monday,tuesday)')
    time_add.add_argument('--start', required=True, help='Start time (HH:MM)')
    time_add.add_argument('--end', required=True, help='End time (HH:MM)')
    time_add.add_argument('--devices', required=True, help='Device IPs (comma-separated)')

    # time remove
    time_remove = time_cmds.add_parser('remove', help='Remove time-based exception')
    time_remove.add_argument('name', help='Exception name')

    # time list
    time_cmds.add_parser('list', help='List time-based exceptions')

    # Emergency override commands
    emergency = subparsers.add_parser('emergency', help='Manage emergency override')
    emergency_cmds = emergency.add_subparsers(dest='action')

    # emergency activate
    emergency_activate = emergency_cmds.add_parser('activate', help='Activate emergency override')
    emergency_activate.add_argument('--password', required=True, help='Admin password')
    emergency_activate.add_argument('--activated-by', help='Who is activating (default: CLI)')

    # emergency deactivate
    emergency_deactivate = emergency_cmds.add_parser('deactivate', help='Deactivate emergency override')
    emergency_deactivate.add_argument('--password', required=True, help='Admin password')

    # emergency status
    emergency_cmds.add_parser('status', help='Show emergency override status')

    # emergency setpassword
    emergency_setpw = emergency_cmds.add_parser('setpassword', help='Set emergency override password')
    emergency_setpw.add_argument('password', help='New password')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to appropriate handler
    if args.command == 'allowlist':
        if args.action == 'add':
            return cmd_allowlist_add(args)
        elif args.action == 'remove':
            return cmd_allowlist_remove(args)
        elif args.action == 'list':
            return cmd_allowlist_list(args)
        elif args.action == 'check':
            return cmd_allowlist_check(args)
        else:
            allowlist.print_help()
            return 1

    elif args.command == 'time':
        if args.action == 'add':
            return cmd_time_add(args)
        elif args.action == 'remove':
            return cmd_time_remove(args)
        elif args.action == 'list':
            return cmd_time_list(args)
        else:
            time.print_help()
            return 1

    elif args.command == 'emergency':
        if args.action == 'activate':
            return cmd_emergency_activate(args)
        elif args.action == 'deactivate':
            return cmd_emergency_deactivate(args)
        elif args.action == 'status':
            return cmd_emergency_status(args)
        elif args.action == 'setpassword':
            return cmd_emergency_setpassword(args)
        else:
            emergency.print_help()
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
