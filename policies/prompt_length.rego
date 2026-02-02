# YORI Policy: Prompt Length Limits
# @description Limit prompt length to control costs and prevent abuse
# @author YORI Team
# @version 1.0.0

package yori.policies.prompt_length

default allow = true
default block = false
default alert = false

# Maximum prompt length in characters
max_prompt_length = 10000

# Alert threshold (characters)
alert_threshold = 5000

# Block very long prompts
block if {
    count(input.prompt) > max_prompt_length
}

# Alert on moderately long prompts
alert if {
    not block
    count(input.prompt) > alert_threshold
}

# Allow normal length prompts
allow if {
    not block
}
