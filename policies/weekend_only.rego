# YORI Policy: Weekend Only
# @description Only allow LLM access on weekends
# @author YORI Team
# @version 1.0.0

package yori.policies.weekend_only

import future.keywords.if

default allow = false
default block = false
default alert = false

# Get day of week (0 = Sunday, 6 = Saturday)
is_weekend if {
    day := time.weekday(time.now_ns())
    day == "Saturday"
}

is_weekend if {
    day := time.weekday(time.now_ns())
    day == "Sunday"
}

# Allow on weekends
allow if {
    is_weekend
}

# Block on weekdays
block if {
    not is_weekend
}
