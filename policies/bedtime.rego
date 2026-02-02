# YORI Policy: Bedtime Restrictions
# @description Block LLM access after 9 PM and before 7 AM
# @author YORI Team
# @version 1.0.0

package yori.policies.bedtime

import future.keywords.if

default allow = true
default block = false

# Block requests between 9 PM (21:00) and 7 AM (07:00)
block if {
    hour := time.clock([time.now_ns(), "Local"])[0]
    hour >= 21
}

block if {
    hour := time.clock([time.now_ns(), "Local"])[0]
    hour < 7
}

# Allow during normal hours
allow if {
    not block
}
