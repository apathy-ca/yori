# YORI Policy: Endpoint Restrictions
# @description Restrict which LLM providers can be used
# @author YORI Team
# @version 1.0.0

package yori.policies.endpoint_restrict

default allow = true
default block = false
default alert = false

# Allowed endpoints
allowed_endpoints = {
    "api.openai.com",
    "api.anthropic.com",
}

# Blocked endpoints (competitors, unknown providers)
blocked_endpoints = {
    # Add endpoints to block here
}

# Alert-only endpoints (monitor but allow)
monitored_endpoints = {
    "generativelanguage.googleapis.com",
    "api.mistral.ai",
}

# Block if endpoint is explicitly blocked
block if {
    some blocked in blocked_endpoints
    contains(input.endpoint, blocked)
}

# Block if endpoint is not in allowed list (whitelist mode)
# Uncomment to enable strict whitelist mode:
# block if {
#     endpoint := input.endpoint
#     not endpoint_allowed(endpoint)
# }

# Alert on monitored endpoints
alert if {
    some monitored in monitored_endpoints
    contains(input.endpoint, monitored)
}

# Helper: check if endpoint is allowed
endpoint_allowed(endpoint) if {
    some allowed in allowed_endpoints
    contains(endpoint, allowed)
}
