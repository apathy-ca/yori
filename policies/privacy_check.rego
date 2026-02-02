# YORI Policy: Privacy Check
# @description Alert on potential PII in prompts (emails, phones, SSN)
# @author YORI Team
# @version 1.0.0

package yori.policies.privacy_check

default allow = true
default alert = false

# Check for email patterns
alert if {
    regex.match(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`, input.prompt)
}

# Check for phone number patterns
alert if {
    regex.match(`\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`, input.prompt)
}

# Check for SSN patterns
alert if {
    regex.match(`\b\d{3}-\d{2}-\d{4}\b`, input.prompt)
}

# Check for credit card patterns
alert if {
    regex.match(`\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b`, input.prompt)
}
