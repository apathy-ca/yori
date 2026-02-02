# YORI Policy: Token Budget
# @description Enforce token-based daily budgets per device
# @author YORI Team
# @version 1.0.0

package yori.policies.token_budget

default allow = true
default block = false
default alert = false

# Daily token limit per device
daily_token_limit = 100000

# Alert at this percentage of limit
alert_threshold_percent = 80

# Block if daily token budget exceeded
block if {
    input.daily_tokens > daily_token_limit
}

# Alert if approaching limit
alert if {
    not block
    input.daily_tokens > (daily_token_limit * alert_threshold_percent / 100)
}

# Allow if under budget
allow if {
    not block
}
