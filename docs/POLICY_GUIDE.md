# YORI Policy Guide

Complete guide to configuring and writing policies for LLM governance.

## Table of Contents

1. [Introduction](#introduction)
2. [Policy Concepts](#policy-concepts)
3. [Pre-built Templates](#pre-built-templates)
4. [Writing Custom Policies](#writing-custom-policies)
5. [Policy Testing](#policy-testing)
6. [Alert Configuration](#alert-configuration)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting](#troubleshooting)

## Introduction

YORI uses [Open Policy Agent (OPA)](https://www.openpolicyagent.org/) to evaluate Rego policies against LLM requests. Policies can observe, alert, or block traffic based on configurable rules.

### Policy Modes

- **Observe:** Log all requests, no alerts (default)
- **Advisory:** Send alerts when rules trigger, but allow requests
- **Enforce:** Block requests that violate policy (opt-in only)

## Policy Concepts

### How Policies Work

```
1. LLM Request → 2. Policy Evaluation → 3. Decision + Alerts → 4. Forward/Block
```

Each policy evaluates request context and returns:
- `allow` (boolean): Whether to allow the request
- `policy` (string): Name of policy that made decision
- `reason` (string): Human-readable explanation
- `mode` (string): observe/advisory/enforce
- `metadata` (optional): Additional data for alerts

### Request Input Schema

Policies receive this context:

```json
{
  "user": "alice",              // Username or client IP
  "device": "iphone-12",         // Device identifier
  "endpoint": "api.openai.com",  // LLM endpoint
  "method": "POST",              // HTTP method
  "path": "/v1/chat/completions",// Request path
  "prompt": "User prompt text",  // User's prompt
  "messages": [                  // Chat messages (if applicable)
    {"role": "user", "content": "Hello"}
  ],
  "timestamp": "2026-01-19T21:30:00Z", // ISO 8601
  "hour": 21,                    // Hour of day (0-23)
  "request_count": 45,           // Daily request count
  "config": {                    // Custom configuration
    "daily_threshold": 50
  }
}
```

## Pre-built Templates

YORI includes 5 ready-to-use policy templates:

### 1. Home Default (Observe Mode)

**File:** `home_default.rego`

Baseline policy that allows all requests. Use this when starting YORI to understand your traffic patterns.

```rego
package yori.home_default

import rego.v1

default allow := true
mode := "observe"
reason := "Default home policy - all requests allowed"
```

**Configuration:** None required

### 2. Bedtime Policy

**File:** `bedtime.rego`

Alert on LLM usage during late hours (after 9 PM or before 6 AM).

**Use Case:** Monitor children's late-night AI usage

**Example Alert:**
```
LLM usage detected after bedtime (22:00)
User: alice
Device: iphone-12
```

**Configuration:** Edit hours in `.rego` file:
```rego
is_bedtime if {
    request_hour >= 21  # Change bedtime hour
}
```

### 3. High Usage Policy

**File:** `high_usage.rego`

Alert when daily request count exceeds thresholds.

**Use Case:** Prevent unexpected API bills

**Thresholds:**
- Warning: 80% of limit (40 requests if limit is 50)
- Critical: 100% of limit (50 requests)

**Configuration:** Set threshold in request:
```python
{
  "request_count": 45,
  "config": {"daily_threshold": 50}  # Custom threshold
}
```

### 4. Privacy Policy

**File:** `privacy.rego`

Detect PII (Personally Identifiable Information) in prompts.

**Use Case:** Prevent accidental data leaks to LLM providers

**Detects:**
- Credit card numbers (`4532-1234-5678-9010`)
- Social Security Numbers (`123-45-6789`)
- Email addresses (`user@example.com`)
- Phone numbers (`(555) 123-4567`)
- IP addresses (`192.168.1.1`)

**Example Alert:**
```
PII detected in prompt: email, phone
User: bob
```

**Configuration:** Add custom patterns in `.rego`:
```rego
contains_api_key if {
    regex.match(`\bsk-[A-Za-z0-9]{48}\b`, prompt)
}
```

### 5. Homework Helper

**File:** `homework_helper.rego`

Detect when children might be using AI for homework.

**Use Case:** Monitor educational AI usage

**Detects Keywords:**
- Homework: assignment, essay, paper, report, study
- Academic: equation, calculus, chemistry, theorem

**Example Alert:**
```
Potential homework-related query detected (keywords: homework, essay)
User: student
Hour: 15
```

## Writing Custom Policies

### Basic Policy Structure

```rego
package yori.my_policy

import rego.v1

# Decision: allow or deny
allow := true if {
    # Your conditions here
}

# Policy mode
mode := "advisory"

# Human-readable reason
reason := "Explanation of decision"

# Optional metadata
metadata := {
    "policy_version": "1.0.0",
    "alert_triggered": true,
}
```

### Example: Time-based Restrictions

Restrict LLM usage during school hours:

```rego
package yori.school_hours

import rego.v1

# Get hour from input
hour := input.hour if {
    input.hour
}

default hour := 12

# Check if during school (8 AM - 3 PM, Mon-Fri)
is_school_hours if {
    hour >= 8
    hour < 15
}

# Allow outside school hours, alert during
allow := true

mode := "advisory" if is_school_hours else := "observe"

reason := sprintf("LLM usage during school hours (%d:00)", [hour]) if {
    is_school_hours
} else := "Outside school hours"

metadata := {
    "policy_type": "school_hours",
    "hour": hour,
    "alert_triggered": is_school_hours,
} if is_school_hours
```

### Example: Content Filtering

Detect specific topics:

```rego
package yori.content_filter

import rego.v1

prompt := lower(input.prompt) if input.prompt else := ""

# Blocked topics
blocked_topics := ["violence", "explicit", "harmful"]

contains_blocked_topic if {
    some topic in blocked_topics
    contains(prompt, topic)
}

# Advisory mode - alert but don't block
allow := true

mode := "advisory" if contains_blocked_topic else := "observe"

reason := "Prompt contains sensitive content" if {
    contains_blocked_topic
} else := "Content OK"
```

### Example: User-specific Policies

Different rules per user:

```rego
package yori.user_specific

import rego.v1

user := input.user if input.user else := "unknown"

# Children have stricter limits
is_child if {
    user in ["alice", "bob", "charlie"]
}

# Allow but alert for children
allow := true

mode := "advisory" if is_child else := "observe"

reason := sprintf("Child account detected: %s", [user]) if {
    is_child
} else := "Adult account"
```

## Policy Testing

Always test policies before deployment using the dry-run feature.

### Command Line Testing

```bash
# Compile policy to WASM
opa build -t wasm -e yori/my_policy/allow my_policy.rego

# Test with Python
python3 << EOF
from yori.policy import PolicyEvaluator

evaluator = PolicyEvaluator("policies")
evaluator.load_policies()

result = evaluator.test_policy("my_policy", {
    "user": "alice",
    "hour": 22,
    "prompt": "test prompt"
})

print(f"Allow: {result.allow}")
print(f"Mode: {result.mode}")
print(f"Reason: {result.reason}")
EOF
```

### Web UI Testing

1. Navigate to **Services → YORI → Policies**
2. Click **Policy Testing** panel
3. Select policy from dropdown
4. Enter test JSON:
```json
{
  "user": "alice",
  "hour": 22,
  "prompt": "Help with homework"
}
```
5. Click **Run Test**

### Unit Testing

Create Rego test files:

```rego
# my_policy_test.rego
package yori.my_policy

import rego.v1

test_allows_daytime if {
    result := allow with input as {"hour": 12}
    result == true
}

test_alerts_nighttime if {
    result := mode with input as {"hour": 22}
    result == "advisory"
}
```

Run with OPA:
```bash
opa test policies/ -v
```

## Alert Configuration

### Email Alerts

Configure SMTP in `/usr/local/etc/yori/yori.conf`:

```ini
[alerts]
email_enabled = true
smtp_host = smtp.gmail.com
smtp_port = 587
smtp_user = alerts@example.com
smtp_password = your-password
smtp_from = yori@home.local
smtp_to = parent@example.com
```

### Webhook Alerts

Send alerts to external services:

```ini
[alerts]
webhook_enabled = true
webhook_url = https://your-server.com/yori-alerts
webhook_headers = {"Authorization": "Bearer token123"}
```

### Push Notifications (Pushover)

```ini
[alerts]
pushover_enabled = true
pushover_api_token = your-app-token
pushover_user_key = your-user-key
```

### Self-hosted (Gotify)

```ini
[alerts]
gotify_enabled = true
gotify_server_url = https://gotify.home.local
gotify_app_token = your-app-token
```

### Web UI Alerts

Always enabled. View at **Services → YORI → Dashboard**

## Performance Considerations

### Target Latency

Policy evaluation should complete in <5ms (p95) to avoid impacting LLM requests.

### Optimization Tips

1. **Keep policies simple:** Complex regex/logic increases latency
2. **Avoid HTTP calls:** All evaluation is synchronous
3. **Limit loaded policies:** Only load policies you need
4. **Use caching:** Repeated evaluations are cached
5. **Compile to WASM:** Always use compiled .wasm files

### Performance Testing

```python
import time
from yori.policy import PolicyEvaluator

evaluator = PolicyEvaluator("policies")
evaluator.load_policies()

# Warmup
for _ in range(10):
    evaluator.evaluate({"user": "test", "hour": 12})

# Measure
latencies = []
for _ in range(1000):
    start = time.perf_counter()
    evaluator.evaluate({"user": "test", "hour": 12, "prompt": "test"})
    latency = (time.perf_counter() - start) * 1000
    latencies.append(latency)

latencies.sort()
print(f"P50: {latencies[500]:.2f}ms")
print(f"P95: {latencies[950]:.2f}ms")
print(f"P99: {latencies[990]:.2f}ms")
```

## Troubleshooting

### Policy Not Loading

**Symptoms:** Policy doesn't appear in `/api/yori/policy/list`

**Solutions:**
1. Check file exists: `ls -la /usr/local/etc/yori/policies/*.wasm`
2. Verify compilation: Re-compile .rego to .wasm
3. Check permissions: `chmod 644 policies/*.wasm`
4. Reload: Click "Reload Policies" in web UI
5. Check logs: `tail -f /var/log/yori/yori.log`

### Policy Not Triggering

**Symptoms:** Expected alerts not sent

**Debug:**
```python
from yori.policy import PolicyEvaluator

evaluator = PolicyEvaluator("policies")
evaluator.load_policies()

result = evaluator.evaluate({
    "user": "alice",
    "hour": 22,
    "prompt": "test"
})

print(f"Policy: {result.policy}")
print(f"Mode: {result.mode}")
print(f"Reason: {result.reason}")
print(f"Metadata: {result.metadata}")
```

**Common Issues:**
- Wrong input field names
- Policy mode is "observe" (no alerts)
- Alert channels not configured
- Conditions not met (check logic)

### Alerts Not Delivered

**Symptoms:** Policy triggers but no email/push received

**Check:**
1. Alert mode: Must be "advisory" or "enforce"
2. Channel enabled: Check `yori.conf`
3. Credentials: Test SMTP/webhook manually
4. Logs: `grep -i alert /var/log/yori/yori.log`
5. Firewall: Allow outbound SMTP (port 587)

### Performance Issues

**Symptoms:** Slow LLM responses, high latency

**Solutions:**
1. Check evaluation time: Run performance test above
2. Simplify policies: Remove complex regex
3. Reduce loaded policies: Disable unused policies
4. Update OPA: Use latest opa-wasm version
5. Hardware: Ensure router has adequate CPU

## Further Reading

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-reference/)
- [OPA Policy Testing](https://www.openpolicyagent.org/docs/latest/policy-testing/)
- [YORI Architecture](ARCHITECTURE.md)
- [YORI User Guide](USER_GUIDE.md)

## Policy Cookbook

See [policies/README.md](../policies/README.md) for 10+ example policies covering:
- Time-based restrictions
- Content filtering
- Usage quotas
- Multi-user policies
- Integration with external systems
