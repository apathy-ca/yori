# YORI Policy: Family-Friendly Filter
# @description Block inappropriate content for family environments
# @author YORI Team
# @version 1.0.0

package yori.policies.family_filter

default allow = true
default block = false
default alert = false

# Categories to block (add terms as needed)
blocked_categories = {
    # Violence
    "violence",
    "gore",
    "torture",
    # Explicit content
    "explicit",
    "nsfw",
    # Harmful activities
    "illegal",
    "drugs",
    "weapons",
}

# Terms that trigger alerts (less severe)
alert_terms = {
    "mature",
    "adult",
    "controversial",
}

# Block prompts with blocked category terms
block if {
    prompt_lower := lower(input.prompt)
    some term in blocked_categories
    contains(prompt_lower, term)
}

# Alert on potentially concerning prompts
alert if {
    not block
    prompt_lower := lower(input.prompt)
    some term in alert_terms
    contains(prompt_lower, term)
}

# Allow clean prompts
allow if {
    not block
}
