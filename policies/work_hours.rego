# YORI Policy: Work Hours
# @description Only allow LLM access during business hours (9 AM - 5 PM)
# @author YORI Team
# @version 1.0.0

package yori.policies.work_hours

import future.keywords.if

default allow = false
default block = false

# Check if within work hours (9 AM to 5 PM)
is_work_hours if {
    hour := time.clock([time.now_ns(), "Local"])[0]
    hour >= 9
    hour < 17
}

# Allow during work hours
allow if {
    is_work_hours
}

# Block outside work hours
block if {
    not is_work_hours
}
