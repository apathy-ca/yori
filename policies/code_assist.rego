# YORI Policy: Code Assistance Tracking
# @description Track and allow code assistance requests
# @author YORI Team
# @version 1.0.0

package yori.policies.code_assist

default allow = true
default block = false
default alert = false

# Code-related keywords
code_keywords = {
    "code",
    "function",
    "class",
    "debug",
    "error",
    "programming",
    "python",
    "javascript",
    "java",
    "rust",
    "golang",
    "typescript",
    "sql",
    "html",
    "css",
    "api",
    "algorithm",
    "data structure",
    "refactor",
    "optimize",
}

# Detect if this is a coding request
is_code_request if {
    prompt_lower := lower(input.prompt)
    some keyword in code_keywords
    contains(prompt_lower, keyword)
}

# Alert on code assistance (for tracking/analytics)
alert if {
    is_code_request
}

# Always allow code assistance
allow = true
