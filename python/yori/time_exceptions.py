"""
Time-based exception management

Handles time-based exceptions that allow access during specific hours/days.
"""

from datetime import datetime, time as datetime_time
from typing import Optional, List
import logging

from yori.models import TimeException, AllowlistConfig
from yori.config import YoriConfig

logger = logging.getLogger(__name__)

# Map day names to weekday numbers (Monday=0, Sunday=6)
DAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_time(time_str: str) -> datetime_time:
    """
    Parse time string in HH:MM format to datetime.time

    Args:
        time_str: Time in HH:MM format (24-hour)

    Returns:
        datetime.time object

    Raises:
        ValueError: If time format is invalid
    """
    try:
        hour, minute = time_str.split(":")
        return datetime_time(int(hour), int(minute))
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM (24-hour)")


def is_time_in_range(current_time: datetime_time, start_time: datetime_time, end_time: datetime_time) -> bool:
    """
    Check if current time falls within start and end time range

    Handles overnight ranges (e.g., 22:00 - 02:00)

    Args:
        current_time: Time to check
        start_time: Range start time
        end_time: Range end time

    Returns:
        True if current_time is within range
    """
    if start_time <= end_time:
        # Normal range (e.g., 09:00 - 17:00)
        return start_time <= current_time <= end_time
    else:
        # Overnight range (e.g., 22:00 - 02:00)
        return current_time >= start_time or current_time <= end_time


def is_day_in_range(current_day: int, allowed_days: List[str]) -> bool:
    """
    Check if current day of week is in allowed days

    Args:
        current_day: Day of week (0=Monday, 6=Sunday)
        allowed_days: List of allowed day names (lowercase)

    Returns:
        True if current day is in allowed days
    """
    allowed_day_numbers = [DAY_MAP.get(day.lower(), -1) for day in allowed_days]
    return current_day in allowed_day_numbers


def get_exception_by_name(config: AllowlistConfig, name: str) -> Optional[TimeException]:
    """
    Find a time exception by name

    Args:
        config: Allowlist configuration
        name: Exception name to search for

    Returns:
        TimeException if found and enabled, None otherwise
    """
    for exception in config.time_exceptions:
        if exception.name == name and exception.enabled:
            return exception

    return None


def is_exception_active(exception_name: str, client_ip: str, config: YoriConfig,
                        check_time: Optional[datetime] = None) -> bool:
    """
    Check if a specific time exception is currently active for a client

    Args:
        exception_name: Name of the time exception to check
        client_ip: Client IP address
        config: Full YORI configuration
        check_time: Time to check (defaults to now)

    Returns:
        True if exception is active for this client at this time
    """
    if not config.enforcement or not config.enforcement.allowlist:
        return False

    exception = get_exception_by_name(config.enforcement.allowlist, exception_name)
    if not exception:
        return False

    # Check if client IP is in exception's device list
    if client_ip not in exception.device_ips:
        return False

    # Check time and day
    now = check_time or datetime.now()
    current_day = now.weekday()  # 0=Monday, 6=Sunday
    current_time = now.time()

    try:
        start_time = parse_time(exception.start_time)
        end_time = parse_time(exception.end_time)
    except ValueError as e:
        logger.error(f"Invalid time format in exception '{exception_name}': {e}")
        return False

    # Check if current day is in allowed days
    if not is_day_in_range(current_day, exception.days):
        return False

    # Check if current time is in allowed time range
    if not is_time_in_range(current_time, start_time, end_time):
        return False

    logger.info(f"Time exception '{exception_name}' active for {client_ip}")
    return True


def check_any_exception_active(client_ip: str, config: YoriConfig,
                                check_time: Optional[datetime] = None) -> tuple[bool, Optional[TimeException]]:
    """
    Check if ANY time exception is currently active for a client

    This is the main entry point for time exception checking.

    Args:
        client_ip: Client IP address
        config: Full YORI configuration
        check_time: Time to check (defaults to now)

    Returns:
        Tuple of (is_active, exception)
        - is_active: True if any exception is active
        - exception: The active TimeException if found, None otherwise
    """
    if not config.enforcement or not config.enforcement.allowlist:
        return False, None

    now = check_time or datetime.now()
    current_day = now.weekday()
    current_time = now.time()

    for exception in config.enforcement.allowlist.time_exceptions:
        if not exception.enabled:
            continue

        # Check if client IP is in exception's device list
        if client_ip not in exception.device_ips:
            continue

        try:
            start_time = parse_time(exception.start_time)
            end_time = parse_time(exception.end_time)
        except ValueError as e:
            logger.error(f"Invalid time format in exception '{exception.name}': {e}")
            continue

        # Check day and time
        if is_day_in_range(current_day, exception.days) and \
           is_time_in_range(current_time, start_time, end_time):
            logger.info(f"Time exception '{exception.name}' active for {client_ip}")
            return True, exception

    return False, None


def add_exception(config: YoriConfig, name: str, description: Optional[str],
                  days: List[str], start_time: str, end_time: str,
                  device_ips: List[str]) -> TimeException:
    """
    Add a time-based exception

    Args:
        config: Full YORI configuration
        name: Exception name
        description: Human-readable description
        days: List of day names (e.g., ["monday", "tuesday"])
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        device_ips: List of device IPs this exception applies to

    Returns:
        Newly created TimeException

    Raises:
        ValueError: If time format is invalid
    """
    # Validate time formats
    parse_time(start_time)
    parse_time(end_time)

    exception = TimeException(
        name=name,
        description=description,
        days=days,
        start_time=start_time,
        end_time=end_time,
        device_ips=device_ips
    )

    if not config.enforcement:
        from yori.models import EnforcementConfig
        config.enforcement = EnforcementConfig()

    config.enforcement.allowlist.time_exceptions.append(exception)
    logger.info(f"Added time exception: {name}")

    return exception


def remove_exception(config: YoriConfig, name: str) -> bool:
    """
    Remove a time-based exception

    Args:
        config: Full YORI configuration
        name: Exception name to remove

    Returns:
        True if exception was removed, False if not found
    """
    if not config.enforcement or not config.enforcement.allowlist:
        return False

    exceptions = config.enforcement.allowlist.time_exceptions

    for i, exception in enumerate(exceptions):
        if exception.name == name:
            exceptions.pop(i)
            logger.info(f"Removed time exception: {name}")
            return True

    return False


def list_active_exceptions(config: YoriConfig, check_time: Optional[datetime] = None) -> List[TimeException]:
    """
    List all time exceptions that are currently active

    Args:
        config: Full YORI configuration
        check_time: Time to check (defaults to now)

    Returns:
        List of currently active TimeExceptions
    """
    if not config.enforcement or not config.enforcement.allowlist:
        return []

    now = check_time or datetime.now()
    current_day = now.weekday()
    current_time = now.time()

    active_exceptions = []

    for exception in config.enforcement.allowlist.time_exceptions:
        if not exception.enabled:
            continue

        try:
            start_time = parse_time(exception.start_time)
            end_time = parse_time(exception.end_time)
        except ValueError:
            continue

        if is_day_in_range(current_day, exception.days) and \
           is_time_in_range(current_time, start_time, end_time):
            active_exceptions.append(exception)

    return active_exceptions
