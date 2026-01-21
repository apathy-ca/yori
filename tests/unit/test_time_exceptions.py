"""
Unit tests for time-based exception functionality
"""

import pytest
from datetime import datetime, time as datetime_time

from yori.models import TimeException, AllowlistConfig, EnforcementConfig
from yori.config import YoriConfig
from yori.time_exceptions import (
    parse_time,
    is_time_in_range,
    is_day_in_range,
    get_exception_by_name,
    is_exception_active,
    check_any_exception_active,
    add_exception,
    remove_exception,
    list_active_exceptions,
)


class TestTimeParser:
    """Test time string parsing"""

    def test_parse_time_valid(self):
        t = parse_time("09:30")
        assert t.hour == 9
        assert t.minute == 30

    def test_parse_time_midnight(self):
        t = parse_time("00:00")
        assert t.hour == 0
        assert t.minute == 0

    def test_parse_time_evening(self):
        t = parse_time("23:59")
        assert t.hour == 23
        assert t.minute == 59

    def test_parse_time_invalid(self):
        with pytest.raises(ValueError):
            parse_time("invalid")

        with pytest.raises(ValueError):
            parse_time("25:00")


class TestTimeRangeChecking:
    """Test time range validation"""

    def test_normal_range(self):
        # 09:00 - 17:00 (9 AM - 5 PM)
        start = datetime_time(9, 0)
        end = datetime_time(17, 0)

        assert is_time_in_range(datetime_time(9, 0), start, end) is True
        assert is_time_in_range(datetime_time(12, 0), start, end) is True
        assert is_time_in_range(datetime_time(17, 0), start, end) is True
        assert is_time_in_range(datetime_time(8, 59), start, end) is False
        assert is_time_in_range(datetime_time(17, 1), start, end) is False

    def test_overnight_range(self):
        # 22:00 - 02:00 (10 PM - 2 AM)
        start = datetime_time(22, 0)
        end = datetime_time(2, 0)

        assert is_time_in_range(datetime_time(22, 0), start, end) is True
        assert is_time_in_range(datetime_time(23, 30), start, end) is True
        assert is_time_in_range(datetime_time(0, 0), start, end) is True
        assert is_time_in_range(datetime_time(1, 0), start, end) is True
        assert is_time_in_range(datetime_time(2, 0), start, end) is True
        assert is_time_in_range(datetime_time(3, 0), start, end) is False
        assert is_time_in_range(datetime_time(12, 0), start, end) is False


class TestDayRangeChecking:
    """Test day of week validation"""

    def test_weekday_check(self):
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]

        assert is_day_in_range(0, weekdays) is True  # Monday
        assert is_day_in_range(4, weekdays) is True  # Friday
        assert is_day_in_range(5, weekdays) is False  # Saturday
        assert is_day_in_range(6, weekdays) is False  # Sunday

    def test_weekend_check(self):
        weekend = ["saturday", "sunday"]

        assert is_day_in_range(5, weekend) is True  # Saturday
        assert is_day_in_range(6, weekend) is True  # Sunday
        assert is_day_in_range(0, weekend) is False  # Monday

    def test_single_day(self):
        friday = ["friday"]

        assert is_day_in_range(4, friday) is True
        assert is_day_in_range(0, friday) is False


class TestExceptionLookup:
    """Test exception lookup by name"""

    def test_get_exception_by_name(self):
        config = AllowlistConfig(
            time_exceptions=[
                TimeException(
                    name="homework_hours",
                    days=["monday"],
                    start_time="15:00",
                    end_time="18:00",
                    enabled=True,
                )
            ]
        )

        exception = get_exception_by_name(config, "homework_hours")
        assert exception is not None
        assert exception.name == "homework_hours"

    def test_get_exception_not_found(self):
        config = AllowlistConfig(time_exceptions=[])

        exception = get_exception_by_name(config, "nonexistent")
        assert exception is None

    def test_get_exception_disabled(self):
        config = AllowlistConfig(
            time_exceptions=[
                TimeException(
                    name="homework_hours",
                    days=["monday"],
                    start_time="15:00",
                    end_time="18:00",
                    enabled=False,
                )
            ]
        )

        exception = get_exception_by_name(config, "homework_hours")
        assert exception is None


class TestExceptionActive:
    """Test if exception is currently active"""

    def test_exception_active_weekday_afternoon(self):
        # Monday 4:00 PM - should be active for homework_hours (3-6 PM Mon-Fri)
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="homework_hours",
                            days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.102"],
                            enabled=True,
                        )
                    ]
                )
            )
        )

        check_time = datetime(2026, 1, 19, 16, 0)  # Monday 4:00 PM
        result = is_exception_active("homework_hours", "192.168.1.102", config, check_time)
        assert result is True

    def test_exception_inactive_wrong_time(self):
        # Monday 2:00 PM - should NOT be active (exception is 3-6 PM)
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="homework_hours",
                            days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.102"],
                            enabled=True,
                        )
                    ]
                )
            )
        )

        check_time = datetime(2026, 1, 19, 14, 0)  # Monday 2:00 PM
        result = is_exception_active("homework_hours", "192.168.1.102", config, check_time)
        assert result is False

    def test_exception_inactive_wrong_day(self):
        # Saturday 4:00 PM - should NOT be active (exception is Mon-Fri)
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="homework_hours",
                            days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.102"],
                            enabled=True,
                        )
                    ]
                )
            )
        )

        check_time = datetime(2026, 1, 18, 16, 0)  # Saturday 4:00 PM
        result = is_exception_active("homework_hours", "192.168.1.102", config, check_time)
        assert result is False

    def test_exception_inactive_wrong_device(self):
        # Monday 4:00 PM, but different device
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="homework_hours",
                            days=["monday", "tuesday", "wednesday", "thursday", "friday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.102"],
                            enabled=True,
                        )
                    ]
                )
            )
        )

        check_time = datetime(2026, 1, 19, 16, 0)  # Monday 4:00 PM
        result = is_exception_active("homework_hours", "192.168.1.200", config, check_time)
        assert result is False


class TestCheckAnyExceptionActive:
    """Test checking if any exception is active for a client"""

    def test_multiple_exceptions_one_active(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="morning_exception",
                            days=["monday"],
                            start_time="09:00",
                            end_time="12:00",
                            device_ips=["192.168.1.100"],
                            enabled=True,
                        ),
                        TimeException(
                            name="afternoon_exception",
                            days=["monday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.100"],
                            enabled=True,
                        ),
                    ]
                )
            )
        )

        # Monday 4:00 PM - afternoon exception should be active
        check_time = datetime(2026, 1, 19, 16, 0)  # Monday
        is_active, exception = check_any_exception_active("192.168.1.100", config, check_time)

        assert is_active is True
        assert exception is not None
        assert exception.name == "afternoon_exception"

    def test_no_exception_active(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="homework_hours",
                            days=["monday"],
                            start_time="15:00",
                            end_time="18:00",
                            device_ips=["192.168.1.102"],
                            enabled=True,
                        )
                    ]
                )
            )
        )

        # Monday 2:00 PM - no exception active
        check_time = datetime(2026, 1, 19, 14, 0)  # Monday
        is_active, exception = check_any_exception_active("192.168.1.102", config, check_time)

        assert is_active is False
        assert exception is None


class TestExceptionManagement:
    """Test adding and removing exceptions"""

    def test_add_exception(self):
        config = YoriConfig()

        exception = add_exception(
            config,
            name="test_exception",
            description="Test",
            days=["monday", "tuesday"],
            start_time="09:00",
            end_time="17:00",
            device_ips=["192.168.1.100"],
        )

        assert exception.name == "test_exception"
        assert len(config.enforcement.allowlist.time_exceptions) == 1

    def test_add_exception_invalid_time(self):
        config = YoriConfig()

        with pytest.raises(ValueError):
            add_exception(
                config,
                name="test_exception",
                description="Test",
                days=["monday"],
                start_time="invalid",
                end_time="17:00",
                device_ips=["192.168.1.100"],
            )

    def test_remove_exception(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="test_exception",
                            days=["monday"],
                            start_time="15:00",
                            end_time="18:00",
                            enabled=True,
                        )
                    ]
                )
            )
        )

        result = remove_exception(config, "test_exception")
        assert result is True
        assert len(config.enforcement.allowlist.time_exceptions) == 0

    def test_remove_exception_not_found(self):
        config = YoriConfig()

        result = remove_exception(config, "nonexistent")
        assert result is False


class TestListActiveExceptions:
    """Test listing active exceptions"""

    def test_list_active_exceptions(self):
        config = YoriConfig(
            enforcement=EnforcementConfig(
                allowlist=AllowlistConfig(
                    time_exceptions=[
                        TimeException(
                            name="exception1",
                            days=["monday"],
                            start_time="09:00",
                            end_time="17:00",
                            enabled=True,
                        ),
                        TimeException(
                            name="exception2",
                            days=["monday"],
                            start_time="15:00",
                            end_time="18:00",
                            enabled=True,
                        ),
                        TimeException(
                            name="exception3",
                            days=["tuesday"],
                            start_time="09:00",
                            end_time="17:00",
                            enabled=True,
                        ),
                    ]
                )
            )
        )

        # Monday 4:00 PM - both exception1 and exception2 should be active
        check_time = datetime(2026, 1, 19, 16, 0)  # Monday
        active = list_active_exceptions(config, check_time)

        assert len(active) == 2
        names = [e.name for e in active]
        assert "exception1" in names
        assert "exception2" in names
