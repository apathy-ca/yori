package yori.home_default

# Default allow-all policy for home use (observe mode)
# This policy logs all requests but allows everything through

import rego.v1

# Default decision: allow all requests
default allow := true

# Default mode: observe (log only, no enforcement)
mode := "observe"

# Reason for the decision
reason := "Default home policy - all requests allowed"

# Metadata for auditing
metadata := {
	"policy_version": "1.0.0",
	"policy_type": "default",
	"timestamp": time.now_ns(),
}
