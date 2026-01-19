package yori.bedtime

# Bedtime policy: Alert on LLM usage after 21:00 (9 PM)
# Helps parents monitor late-night AI usage by children

import rego.v1

# Extract hour from input (expects ISO 8601 timestamp or hour field)
request_hour := hour if {
	# Try to get hour from timestamp
	timestamp := input.timestamp
	[date, time_part] := split(timestamp, "T")
	[hour_str, _, _] := split(time_part, ":")
	hour := to_number(hour_str)
}

# Fallback: get hour from input.hour field
request_hour := input.hour if {
	not input.timestamp
	input.hour
}

# Default hour if not provided (assume daytime)
default request_hour := 12

# Check if it's past bedtime (after 9 PM)
is_bedtime if {
	request_hour >= 21
}

# Check if it's late night (before 6 AM)
is_late_night if {
	request_hour < 6
}

# Allow the request (always true - we only alert, not block)
allow := true

# Mode: advisory (alert but allow)
mode := "advisory" if {
	is_bedtime
} else := "advisory" if {
	is_late_night
} else := "observe"

# Reason depends on time
reason := sprintf("LLM usage detected after bedtime (%d:00)", [request_hour]) if {
	is_bedtime
} else := sprintf("Late night LLM usage detected (%d:00)", [request_hour]) if {
	is_late_night
} else := "Within normal hours"

# Metadata for alerts
metadata := {
	"policy_version": "1.0.0",
	"policy_type": "bedtime",
	"hour": request_hour,
	"alert_triggered": is_bedtime or is_late_night,
	"alert_type": "bedtime_violation",
	"user": input.user,
	"device": input.device,
} if {
	is_bedtime or is_late_night
}
