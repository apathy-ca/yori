package yori.privacy

# Privacy policy: Detect PII (Personally Identifiable Information) in prompts
# Helps prevent accidental sharing of sensitive information with LLM providers

import rego.v1

# Get the prompt text from input
prompt := input.prompt if {
	input.prompt
} else := input.messages[_].content if {
	input.messages
} else := ""

# Simple PII patterns (regex-like matching)
# Credit card pattern: 16 digits with optional spaces/dashes
contains_credit_card if {
	regex.match(`\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b`, prompt)
}

# Social Security Number pattern (SSN): XXX-XX-XXXX
contains_ssn if {
	regex.match(`\b\d{3}-\d{2}-\d{4}\b`, prompt)
}

# Email address pattern
contains_email if {
	regex.match(`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`, prompt)
}

# Phone number pattern (various formats)
contains_phone if {
	regex.match(`\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b`, prompt)
}

# IP address pattern
contains_ip_address if {
	regex.match(`\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b`, prompt)
}

# Check if any PII detected
pii_detected if {
	contains_credit_card
} else if {
	contains_ssn
} else if {
	contains_email
} else if {
	contains_phone
} else if {
	contains_ip_address
}

# Collect detected PII types
pii_types := types if {
	types_set := {type |
		contains_credit_card
		type := "credit_card"
	} | {type |
		contains_ssn
		type := "ssn"
	} | {type |
		contains_email
		type := "email"
	} | {type |
		contains_phone
		type := "phone"
	} | {type |
		contains_ip_address
		type := "ip_address"
	}
	types := [t | t := types_set[_]]
}

# Allow the request (advisory mode - warn but don't block)
allow := true

# Mode: advisory if PII detected
mode := "advisory" if {
	pii_detected
} else := "observe"

# Reason with details
reason := sprintf("PII detected in prompt: %s", [concat(", ", pii_types)]) if {
	pii_detected
} else := "No PII detected"

# Metadata for alerts
metadata := {
	"policy_version": "1.0.0",
	"policy_type": "privacy",
	"pii_detected": pii_detected,
	"pii_types": pii_types,
	"alert_triggered": pii_detected,
	"user": input.user,
	"device": input.device,
	"prompt_length": count(prompt),
} if {
	pii_detected
}
