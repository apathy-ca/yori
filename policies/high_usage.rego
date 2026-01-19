package yori.high_usage

# High usage policy: Alert when daily request count exceeds threshold
# Helps monitor API usage and prevent unexpected bills

import rego.v1

# Default threshold: 50 requests per day
default daily_threshold := 50

# Get threshold from configuration if provided
daily_threshold := input.config.daily_threshold if {
	input.config.daily_threshold
}

# Get current request count for user/device
current_count := input.request_count if {
	input.request_count
} else := 0

# Check if usage is high (>80% of threshold)
is_high_usage if {
	current_count > (daily_threshold * 0.8)
}

# Check if usage exceeds threshold
exceeds_threshold if {
	current_count >= daily_threshold
}

# Allow the request (advisory mode - alert but don't block)
allow := true

# Mode: advisory if high usage detected
mode := "advisory" if {
	exceeds_threshold
} else := "advisory" if {
	is_high_usage
} else := "observe"

# Reason based on usage level
reason := sprintf("Daily request limit exceeded: %d/%d requests", [current_count, daily_threshold]) if {
	exceeds_threshold
} else := sprintf("High usage detected: %d/%d requests (%.0f%%)", [current_count, daily_threshold, (current_count / daily_threshold) * 100]) if {
	is_high_usage
} else := sprintf("Normal usage: %d/%d requests", [current_count, daily_threshold])

# Metadata for alerts and dashboards
metadata := {
	"policy_version": "1.0.0",
	"policy_type": "usage_threshold",
	"current_count": current_count,
	"daily_threshold": daily_threshold,
	"percentage": (current_count / daily_threshold) * 100,
	"alert_triggered": is_high_usage or exceeds_threshold,
	"alert_level": "critical" if exceeds_threshold else "warning",
	"user": input.user,
	"device": input.device,
} if {
	is_high_usage or exceeds_threshold
}
