# YORI Policy: Cost Limit
# @description Alert when estimated daily cost exceeds threshold
# @author YORI Team
# @version 1.0.0

package yori.policies.cost_limit

default allow = true
default alert = false
default block = false

# Cost threshold in cents (default $5 = 500 cents)
cost_threshold = 500

# Alert if daily cost exceeds threshold
alert if {
    input.daily_cost_cents > cost_threshold
}

# Block if cost exceeds 2x threshold
block if {
    input.daily_cost_cents > (cost_threshold * 2)
}
