# YORI Policy: High Usage Alert
# @description Alert when device exceeds 50 requests per day
# @author YORI Team
# @version 1.0.0

package yori.policies.high_usage

default allow = true
default alert = false
default block = false

# Alert if daily request count exceeds threshold
alert if {
    input.daily_request_count > 50
}

# Additional alert for very high usage
alert if {
    input.daily_request_count > 100
}
