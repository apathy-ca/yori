# YORI Policy: Response Auditing
# @description Audit responses for concerning content (post-processing)
# @author YORI Team
# @version 1.0.0

package yori.policies.response_audit

default allow = true
default block = false
default alert = false

# Keywords to audit in responses
audit_keywords = {
    "password",
    "secret",
    "credential",
    "api_key",
    "private_key",
    "ssh_key",
    "token",
}

# This policy runs on responses, not requests
# Alert if response contains sensitive keywords
alert if {
    input.response_body
    response_lower := lower(input.response_body)
    some keyword in audit_keywords
    contains(response_lower, keyword)
}

# Always allow (this is post-processing audit only)
allow = true
