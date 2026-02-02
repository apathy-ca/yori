# YORI Policy: Content Filter
# @description Block prompts containing inappropriate keywords
# @author YORI Team
# @version 1.0.0

package yori.policies.content_filter

default allow = true
default block = false
default alert = false

# Add inappropriate keywords to block
blocked_keywords = {
    # Add keywords here
    # "example_bad_word",
}

# Alert keywords (less severe)
alert_keywords = {
    # "example_concerning_word",
}

# Block if blocked keyword found
block if {
    some keyword in blocked_keywords
    contains(lower(input.prompt), keyword)
}

# Alert if concerning keyword found
alert if {
    some keyword in alert_keywords
    contains(lower(input.prompt), keyword)
}

# Allow if no blocked keywords
allow if {
    not block
}
