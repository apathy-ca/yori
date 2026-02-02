# YORI Policy: School Hours Blocking
# @description Block LLM usage during school hours (prevent homework cheating)
# @author YORI Team
# @version 1.0.0

package yori.policies.school_hours

default allow = true
default block = false
default alert = false

# School hours: 8:00 AM - 3:00 PM weekdays
school_start = 8
school_end = 15

# Days that are school days (1=Monday, 5=Friday)
school_days = {1, 2, 3, 4, 5}

# Block during school hours on school days
block if {
    input.hour >= school_start
    input.hour < school_end
    input.day_of_week >= 1
    input.day_of_week <= 5
}

# Alert for usage just before/after school
alert if {
    not block
    input.day_of_week >= 1
    input.day_of_week <= 5
    # 1 hour before or after school
    input.hour >= (school_start - 1)
    input.hour <= (school_end + 1)
}

# Allow outside school hours
allow if {
    not block
}
