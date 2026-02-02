# YORI Policy: Rate Limiting
# @description Limit requests per device per hour to prevent abuse
# @author YORI Team
# @version 1.0.0

package yori.policies.rate_limit

default allow = true
default block = false
default alert = false

# Maximum requests per hour per device
max_requests_per_hour = 100

# Alert threshold (percentage of max)
alert_threshold = 80

# Block if exceeded hourly limit
block if {
    input.daily_request_count > 0
    # Approximate hourly rate from daily
    hourly_rate := input.daily_request_count / 24
    hourly_rate > max_requests_per_hour
}

# Alert if approaching limit
alert if {
    not block
    input.daily_request_count > 0
    hourly_rate := input.daily_request_count / 24
    hourly_rate > (max_requests_per_hour * alert_threshold / 100)
}

# Allow if under limit
allow if {
    not block
}
