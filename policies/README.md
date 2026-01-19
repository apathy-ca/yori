# YORI Policy Templates

This directory contains pre-built Rego policy templates for common home LLM governance scenarios.

## Available Policies

### 1. `home_default.rego` - Default Allow Policy

**Purpose:** Baseline policy that allows all requests in observe mode.

**Use Case:** Start here when first deploying YORI to understand traffic patterns.

**Mode:** Observe (log only, no enforcement)

**Decision:** Always allows requests

### 2. `bedtime.rego` - Bedtime Monitoring

**Purpose:** Alert on LLM usage after bedtime hours (9 PM - 6 AM).

**Use Case:** Monitor late-night AI usage by children.

**Mode:** Advisory (alert but allow)

**Triggers:**
- After 9 PM (21:00)
- Before 6 AM (06:00)

**Input Requirements:**
- `timestamp` (ISO 8601) or `hour` (0-23)
- `user` (for alerts)
- `device` (for alerts)

**Example Alert:**
```
LLM usage detected after bedtime (22:00)
```

### 3. `high_usage.rego` - Usage Threshold Monitoring

**Purpose:** Alert when daily request count exceeds thresholds.

**Use Case:** Monitor API usage to prevent unexpected bills.

**Mode:** Advisory (alert but allow)

**Triggers:**
- Warning at 80% of daily threshold (default: 40 requests)
- Critical at 100% of daily threshold (default: 50 requests)

**Input Requirements:**
- `request_count` (current daily count)
- `config.daily_threshold` (optional, defaults to 50)

**Example Alert:**
```
High usage detected: 45/50 requests (90%)
```

### 4. `privacy.rego` - PII Detection

**Purpose:** Detect personally identifiable information in prompts.

**Use Case:** Prevent accidental sharing of sensitive data with LLM providers.

**Mode:** Advisory (alert but allow)

**Detects:**
- Credit card numbers (16 digits)
- Social Security Numbers (XXX-XX-XXXX)
- Email addresses
- Phone numbers
- IP addresses

**Input Requirements:**
- `prompt` or `messages` array

**Example Alert:**
```
PII detected in prompt: email, phone
```

### 5. `homework_helper.rego` - Educational Usage Detection

**Purpose:** Detect homework-related queries.

**Use Case:** Monitor when children might be using AI for homework assignments.

**Mode:** Advisory (alert but allow)

**Detects Keywords:**
- Homework: assignment, essay, paper, homework, etc.
- Academic: equation, theorem, calculus, chemistry, etc.

**Input Requirements:**
- `prompt` or `messages` array
- `hour` (optional, for context)

**Example Alert:**
```
Potential homework-related query detected (keywords: homework, essay, solve)
```

## Using Policies

### Compilation

Policies must be compiled to WebAssembly before use:

```bash
# Install OPA CLI
brew install opa  # macOS
# or
curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x /usr/local/bin/opa

# Compile a single policy
opa build -t wasm -e yori/bedtime/allow bedtime.rego

# Or use the Python helper
python3 -c "from yori.policy_loader import compile_policies; compile_policies('policies')"
```

### Loading Policies

Policies are automatically loaded at startup:

```python
from yori.policy import PolicyEvaluator

# Initialize with policy directory
evaluator = PolicyEvaluator("/usr/local/etc/yori/policies")

# Load compiled .wasm files
count = evaluator.load_policies()
print(f"Loaded {count} policies")
```

### Testing Policies

Test policies before deployment:

```python
from yori.policy import PolicyEvaluator

evaluator = PolicyEvaluator("policies")
evaluator.load_policies()

# Test bedtime policy
result = evaluator.test_policy("bedtime", {
    "hour": 22,  # 10 PM
    "user": "alice",
    "device": "iphone-12"
})

print(f"Decision: {result.allow}")
print(f"Mode: {result.mode}")
print(f"Reason: {result.reason}")
# Output:
# Decision: True
# Mode: test
# Reason: LLM usage detected after bedtime (22:00)
```

## Writing Custom Policies

### Policy Structure

```rego
package yori.my_policy

import rego.v1

# Decision: allow or deny
allow := true

# Mode: observe, advisory, or enforce
mode := "advisory"

# Human-readable reason
reason := "My policy reason"

# Optional metadata for alerts
metadata := {
    "policy_version": "1.0.0",
    "policy_type": "custom",
    "alert_triggered": true,
}
```

### Input Schema

Policies receive this input structure:

```json
{
  "user": "alice",
  "device": "iphone-12",
  "endpoint": "api.openai.com",
  "method": "POST",
  "path": "/v1/chat/completions",
  "prompt": "User's prompt text",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "timestamp": "2026-01-19T21:30:00Z",
  "hour": 21,
  "request_count": 45,
  "config": {
    "daily_threshold": 50
  }
}
```

### Best Practices

1. **Always default to allow:** Fail open for safety
2. **Use advisory mode first:** Test policies before enforcement
3. **Provide clear reasons:** Help users understand decisions
4. **Include metadata:** Enable rich alerts and dashboards
5. **Test thoroughly:** Use `test_policy()` before production

## Policy Modes

### Observe Mode
- **Behavior:** Log all requests, no alerts
- **Use:** Initial deployment, traffic analysis
- **Decision:** Always allow

### Advisory Mode
- **Behavior:** Log requests, send alerts on violations
- **Use:** Monitoring without blocking (recommended)
- **Decision:** Always allow (with alerts)

### Enforce Mode
- **Behavior:** Block requests that violate policy
- **Use:** After thorough testing in advisory mode
- **Decision:** Can deny requests

## Troubleshooting

### Policy Not Loading

Check:
1. Policy compiled to .wasm format
2. .wasm file in correct directory
3. File permissions readable
4. Check logs: `journalctl -u yori -f`

### Policy Not Triggering

Debug:
```python
result = evaluator.evaluate({
    "user": "test",
    "hour": 22,
    "prompt": "test prompt"
})
print(f"Policy: {result.policy}")
print(f"Mode: {result.mode}")
print(f"Metadata: {result.metadata}")
```

### Alert Not Sent

Check:
1. Mode is "advisory" or "enforce"
2. Alert channels configured in `yori.conf`
3. SMTP/webhook credentials correct
4. Check logs for delivery errors

## Further Reading

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Rego Language Guide](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [YORI Policy Guide](../docs/POLICY_GUIDE.md)
