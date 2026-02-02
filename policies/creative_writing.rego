# YORI Policy: Creative Writing Detection
# @description Track creative writing requests for monitoring
# @author YORI Team
# @version 1.0.0

package yori.policies.creative_writing

default allow = true
default block = false
default alert = false

# Creative writing keywords
creative_keywords = {
    "story",
    "poem",
    "write me",
    "creative",
    "fiction",
    "narrative",
    "character",
    "plot",
    "dialogue",
    "essay",
    "blog post",
    "article",
    "script",
    "screenplay",
}

# Detect creative writing request
is_creative_request if {
    prompt_lower := lower(input.prompt)
    some keyword in creative_keywords
    contains(prompt_lower, keyword)
}

# Alert on creative writing (for parental monitoring)
alert if {
    is_creative_request
}

# Allow all creative writing
allow = true
