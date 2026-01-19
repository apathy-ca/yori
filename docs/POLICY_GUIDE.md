# YORI Policy Guide

Learn how to write custom Rego policies for LLM governance, alerts, and enforcement.

> ⚠️ **Development Status:** The policy engine integration is in development. This guide describes the policy system as it will work in v0.1.0+. The Rego syntax and examples are valid OPA/Rego code.

---

## Table of Contents

- [Introduction to Policies](#introduction-to-policies)
- [Policy Basics](#policy-basics)
- [Input Data Structure](#input-data-structure)
- [Policy Examples](#policy-examples)
  - [Example 1: Default Allow-All](#example-1-default-allow-all)
  - [Example 2: Bedtime Alerts](#example-2-bedtime-alerts)
  - [Example 3: High Usage Alerts](#example-3-high-usage-alerts)
  - [Example 4: PII Detection](#example-4-pii-detection)
  - [Example 5: Homework Helper Detection](#example-5-homework-helper-detection)
  - [Example 6: Cost Tracking and Budget Alerts](#example-6-cost-tracking-and-budget-alerts)
  - [Example 7: Device-Specific Policies](#example-7-device-specific-policies)
  - [Example 8: Content Filtering](#example-8-content-filtering)
  - [Example 9: Model Restrictions](#example-9-model-restrictions)
  - [Example 10: Time-Based Usage Limits](#example-10-time-based-usage-limits)
  - [Example 11: Prompt Length Limits](#example-11-prompt-length-limits)
  - [Example 12: Multi-Device Coordination](#example-12-multi-device-coordination)
- [Testing Policies](#testing-policies)
- [Policy Deployment](#policy-deployment)
- [Alert Configuration](#alert-configuration)
- [Troubleshooting Policies](#troubleshooting-policies)

---

## Introduction to Policies

YORI uses **Rego** (the policy language of Open Policy Agent) to define rules for LLM governance.

### What Can Policies Do?

Depending on YORI's operating mode:

- **Observe Mode:** Policies are evaluated but have no effect (learning phase)
- **Advisory Mode:** Policies can trigger alerts (email, push notifications, web UI)
- **Enforce Mode:** Policies can block requests (requires user opt-in)

### Common Policy Use Cases

1. **Parental Controls:**
   - Alert when kids use LLMs after bedtime
   - Detect homework-related prompts
   - Monitor educational vs entertainment use

2. **Privacy Protection:**
   - Alert when personally identifiable information (PII) appears in prompts
   - Detect sensitive data patterns (SSN, credit cards)
   - Monitor for accidental data leaks

3. **Cost Management:**
   - Track daily/monthly API usage
   - Alert when nearing budget limits
   - Identify high-cost models (GPT-4 vs GPT-3.5)

4. **Usage Analytics:**
   - Monitor which family members use which LLMs
   - Track usage patterns by time of day
   - Identify unusual usage spikes

---

## Policy Basics

### Rego Language Overview

Rego is a declarative language for expressing policies. Key concepts:

- **Packages:** Organize policies into namespaces
- **Rules:** Define conditions and decisions
- **Data:** Access input data and external data sources
- **Functions:** Built-in and custom helper functions

### Basic Rego Syntax

```rego
package example

# A simple rule that's always true
allow = true

# A conditional rule
high_usage {
    input.request_count > 100
}

# A rule with output
message = "Too many requests" {
    high_usage
}
```

### YORI Policy Structure

All YORI policies must:

1. Define a `package` (typically `yori.policies.<name>`)
2. Export decision variables: `allow`, `deny`, `alert`, `message`
3. Optionally use `input` data about the current request

**Minimal valid policy:**

```rego
package yori.policies.example

# Allow all requests
allow = true
```

---

## Input Data Structure

YORI provides rich input data to policies about each LLM request.

### Full Input Schema

```json
{
  "request": {
    "id": "req_abc123",
    "timestamp": "2026-01-19T14:30:00Z",
    "method": "POST",
    "path": "/v1/chat/completions",
    "headers": {
      "host": "api.openai.com",
      "authorization": "Bearer sk-...",
      "content-type": "application/json"
    },
    "body": {
      "model": "gpt-4",
      "messages": [
        {"role": "user", "content": "What is the capital of France?"}
      ],
      "temperature": 0.7,
      "max_tokens": 500
    }
  },
  "device": {
    "ip": "192.168.1.100",
    "mac": "aa:bb:cc:dd:ee:ff",
    "hostname": "johns-iphone",
    "user_agent": "ChatGPT/1.2024.226 (iOS 17.1)"
  },
  "endpoint": {
    "domain": "api.openai.com",
    "provider": "openai"
  },
  "context": {
    "hour": 14,
    "day_of_week": "friday",
    "is_weekend": false,
    "request_count_today": 42,
    "request_count_this_hour": 3
  }
}
```

### Accessing Input Data

```rego
# Access request details
model = input.request.body.model
prompt = input.request.body.messages[0].content

# Access device info
device_ip = input.device.ip
device_name = input.device.hostname

# Access context
current_hour = input.context.hour
requests_today = input.context.request_count_today
```

---

## Policy Examples

### Example 1: Default Allow-All

**File:** `home_default.rego`

**Purpose:** Default policy that allows all requests (observe mode baseline).

```rego
package yori.policies.default

# Default policy: allow everything
# This is the baseline policy for observe mode

# Allow all requests by default
allow = true

# No alerts for normal traffic
alert = false

# Optional: log all requests
log_entry = {
    "level": "info",
    "message": "LLM request observed",
    "request_id": input.request.id,
    "endpoint": input.endpoint.domain,
    "device": input.device.hostname,
}
```

**Use Case:** Safe starting point for learning usage patterns without any restrictions.

---

### Example 2: Bedtime Alerts

**File:** `bedtime.rego`

**Purpose:** Alert parents when children use LLMs after bedtime.

```rego
package yori.policies.bedtime

# Bedtime policy: Alert when LLMs are used late at night
# Useful for parental monitoring

# Define bedtime hours (9 PM to 7 AM)
is_bedtime {
    hour := input.context.hour
    hour >= 21  # 9 PM or later
}

is_bedtime {
    hour := input.context.hour
    hour < 7  # Before 7 AM
}

# Define kids' devices (by hostname or IP)
kids_device {
    input.device.hostname == "sarahs-iphone"
}

kids_device {
    input.device.hostname == "jimmys-ipad"
}

kids_device {
    # Or by IP range (192.168.1.100-110)
    startswith(input.device.ip, "192.168.1.10")
}

# Alert if kids use LLMs during bedtime
alert {
    is_bedtime
    kids_device
}

# Friendly message for notification
message = msg {
    alert
    msg := sprintf(
        "🌙 Bedtime LLM usage detected: %s used %s at %d:00",
        [input.device.hostname, input.endpoint.domain, input.context.hour]
    )
}

# In observe/advisory mode, still allow the request
allow = true

# In enforce mode, you could block:
# allow = false { alert }
```

**Alert Example:**
> 🌙 Bedtime LLM usage detected: sarahs-iphone used api.openai.com at 22:00

---

### Example 3: High Usage Alerts

**File:** `high_usage.rego`

**Purpose:** Alert when any device exceeds daily request thresholds.

```rego
package yori.policies.usage

# High usage policy: Alert on unusual request volume
# Helps identify over-usage or potential account compromise

# Define usage thresholds
light_usage_threshold = 50
moderate_usage_threshold = 100
heavy_usage_threshold = 200

# Check usage level
is_light_usage {
    input.context.request_count_today < light_usage_threshold
}

is_moderate_usage {
    count := input.context.request_count_today
    count >= light_usage_threshold
    count < moderate_usage_threshold
}

is_heavy_usage {
    count := input.context.request_count_today
    count >= moderate_usage_threshold
    count < heavy_usage_threshold
}

is_excessive_usage {
    input.context.request_count_today >= heavy_usage_threshold
}

# Alert on heavy or excessive usage
alert {
    is_heavy_usage
}

alert {
    is_excessive_usage
}

# Severity-based messages
message = msg {
    is_heavy_usage
    msg := sprintf(
        "⚠️ Heavy LLM usage: %s has made %d requests today (threshold: %d)",
        [input.device.hostname, input.context.request_count_today, moderate_usage_threshold]
    )
}

message = msg {
    is_excessive_usage
    msg := sprintf(
        "🚨 Excessive LLM usage: %s has made %d requests today (threshold: %d)",
        [input.device.hostname, input.context.request_count_today, heavy_usage_threshold]
    )
}

# Always allow (just monitoring)
allow = true
```

**Alert Examples:**
> ⚠️ Heavy LLM usage: johns-macbook has made 120 requests today (threshold: 100)
> 🚨 Excessive LLM usage: work-laptop has made 250 requests today (threshold: 200)

---

### Example 4: PII Detection

**File:** `privacy.rego`

**Purpose:** Detect personally identifiable information in prompts.

```rego
package yori.policies.privacy

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# PII Detection: Alert when sensitive data appears in prompts
# Helps prevent accidental data leaks to LLM providers

# Get the full prompt text
prompt = input.request.body.messages[_].content

# Social Security Number pattern (XXX-XX-XXXX)
contains_ssn if {
    regex.match(`\d{3}-\d{2}-\d{4}`, prompt)
}

# Credit card number pattern (simplified)
contains_credit_card if {
    regex.match(`\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}`, prompt)
}

# Email address pattern
contains_email if {
    regex.match(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`, prompt)
}

# Phone number patterns
contains_phone if {
    regex.match(`\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}`, prompt)
}

# Address pattern (simplified - ZIP code)
contains_address if {
    regex.match(`\b\d{5}(?:-\d{4})?\b`, prompt)
}

# Check for common PII keywords
pii_keywords = [
    "social security",
    "ssn",
    "credit card",
    "driver's license",
    "driver license",
    "passport number",
    "bank account",
]

contains_pii_keyword if {
    keyword := pii_keywords[_]
    contains(lower(prompt), keyword)
}

# Alert if any PII detected
alert if { contains_ssn }
alert if { contains_credit_card }
alert if { contains_email }
alert if { contains_phone }
alert if { contains_address }
alert if { contains_pii_keyword }

# Detailed message about what was detected
detected_types = types {
    types := {
        "SSN" |
        contains_ssn,
        "Credit Card" |
        contains_credit_card,
        "Email" |
        contains_email,
        "Phone" |
        contains_phone,
        "Address" |
        contains_address,
        "PII Keyword" |
        contains_pii_keyword,
    }
}

message = msg if {
    alert
    types_list := concat(", ", detected_types)
    msg := sprintf(
        "🔒 PII detected in prompt from %s: %s",
        [input.device.hostname, types_list]
    )
}

# In advisory mode: allow but warn
allow = true

# In enforce mode, you could block:
# deny if { contains_ssn }
# deny if { contains_credit_card }
```

**Alert Example:**
> 🔒 PII detected in prompt from marys-laptop: Email, Phone

---

### Example 5: Homework Helper Detection

**File:** `homework_helper.rego`

**Purpose:** Detect when students might be using LLMs for homework.

```rego
package yori.policies.homework

import future.keywords.contains
import future.keywords.if

# Homework detection: Alert when educational keywords appear
# Helps parents monitor academic integrity

# Get prompt text
prompt = lower(input.request.body.messages[_].content)

# Educational keywords
homework_keywords = [
    "homework",
    "assignment",
    "essay",
    "write a paper",
    "solve this problem",
    "answer key",
    "test answers",
    "exam",
    "quiz",
]

math_keywords = [
    "solve for x",
    "derivative",
    "integral",
    "prove that",
    "equation",
    "math problem",
]

writing_keywords = [
    "write an essay",
    "thesis statement",
    "5 paragraph essay",
    "introduction and conclusion",
    "literary analysis",
]

# Check for homework-related content
is_homework_related if {
    keyword := homework_keywords[_]
    contains(prompt, keyword)
}

is_math_homework if {
    keyword := math_keywords[_]
    contains(prompt, keyword)
}

is_writing_homework if {
    keyword := writing_keywords[_]
    contains(prompt, keyword)
}

# Only monitor kids' devices during school hours
is_school_hours if {
    hour := input.context.hour
    day := input.context.day_of_week

    # Monday-Friday
    day != "saturday"
    day != "sunday"

    # 8 AM to 6 PM
    hour >= 8
    hour < 18
}

kids_device if {
    input.device.hostname == "sarahs-iphone"
}

kids_device if {
    input.device.hostname == "jimmys-ipad"
}

# Alert if homework detected on kids' devices
alert if {
    kids_device
    is_homework_related
}

alert if {
    kids_device
    is_school_hours
    is_math_homework
}

alert if {
    kids_device
    is_school_hours
    is_writing_homework
}

# Categorized messages
message = msg if {
    alert
    is_homework_related
    not is_math_homework
    not is_writing_homework
    msg := sprintf(
        "📚 Possible homework help: %s at %d:00 - general homework keywords",
        [input.device.hostname, input.context.hour]
    )
}

message = msg if {
    alert
    is_math_homework
    msg := sprintf(
        "🔢 Possible math homework: %s at %d:00",
        [input.device.hostname, input.context.hour]
    )
}

message = msg if {
    alert
    is_writing_homework
    msg := sprintf(
        "✍️ Possible writing assignment: %s at %d:00",
        [input.device.hostname, input.context.hour]
    )
}

# Advisory mode: allow but notify
allow = true
```

**Alert Examples:**
> 📚 Possible homework help: sarahs-iphone at 16:00 - general homework keywords
> 🔢 Possible math homework: jimmys-ipad at 14:00

---

### Example 6: Cost Tracking and Budget Alerts

**File:** `budget.rego`

**Purpose:** Track estimated API costs and alert when approaching limits.

```rego
package yori.policies.budget

# Cost tracking: Estimate API costs and alert on budget
# Pricing as of Jan 2026 (verify current pricing)

# Token estimation (rough approximation)
estimate_tokens(text) = tokens {
    # Rough estimate: 1 token ≈ 4 characters
    tokens := ceil(count(text) / 4)
}

# OpenAI pricing (per 1K tokens)
openai_pricing = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}

# Anthropic pricing
anthropic_pricing = {
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}

# Get model being used
model = input.request.body.model

# Estimate input tokens
input_tokens = estimate_tokens(input.request.body.messages[_].content)

# Estimate output tokens (from max_tokens param or default)
output_tokens = tokens {
    tokens := input.request.body.max_tokens
} else = 150  # Default assumption

# Calculate cost for OpenAI
openai_cost = cost {
    input.endpoint.domain == "api.openai.com"
    pricing := openai_pricing[model]
    input_cost := (input_tokens / 1000) * pricing.input
    output_cost := (output_tokens / 1000) * pricing.output
    cost := input_cost + output_cost
}

# Calculate cost for Anthropic
anthropic_cost = cost {
    input.endpoint.domain == "api.anthropic.com"
    pricing := anthropic_pricing[model]
    input_cost := (input_tokens / 1000) * pricing.input
    output_cost := (output_tokens / 1000) * pricing.output
    cost := input_cost + output_cost
}

# Monthly budget (in dollars)
monthly_budget = 50

# Estimated cost today (would need external data for real implementation)
# This is a placeholder - actual implementation would query audit DB
estimated_cost_today = 12.50

# Alert thresholds
alert_threshold_80 = monthly_budget * 0.8
alert_threshold_95 = monthly_budget * 0.95

alert if {
    estimated_cost_today > alert_threshold_80
    estimated_cost_today < alert_threshold_95
}

alert if {
    estimated_cost_today >= alert_threshold_95
}

message = msg if {
    alert
    estimated_cost_today < alert_threshold_95
    percent := (estimated_cost_today / monthly_budget) * 100
    msg := sprintf(
        "💰 Budget alert: %.0f%% of monthly budget used ($%.2f / $%.0f)",
        [percent, estimated_cost_today, monthly_budget]
    )
}

message = msg if {
    alert
    estimated_cost_today >= alert_threshold_95
    msg := sprintf(
        "🚨 Budget critical: Approaching limit! ($%.2f / $%.0f)",
        [estimated_cost_today, monthly_budget]
    )
}

# Allow requests (even when over budget in advisory mode)
allow = true

# Could block when over budget in enforce mode:
# deny if { estimated_cost_today >= monthly_budget }
```

**Alert Examples:**
> 💰 Budget alert: 85% of monthly budget used ($42.50 / $50)
> 🚨 Budget critical: Approaching limit! ($48.75 / $50)

---

### Example 7: Device-Specific Policies

**File:** `device_rules.rego`

**Purpose:** Apply different rules to different devices.

```rego
package yori.policies.devices

# Device-specific policies: Different rules for different family members

# Identify devices
parent_device if { input.device.hostname == "dads-laptop" }
parent_device if { input.device.hostname == "moms-iphone" }

kid_device if { input.device.hostname == "sarahs-iphone" }
kid_device if { input.device.hostname == "jimmys-ipad" }

guest_device if {
    # Guest network range
    startswith(input.device.ip, "192.168.2.")
}

# Kids: Only allowed to use GPT-3.5 (cheaper models)
kids_using_expensive_model if {
    kid_device
    model := input.request.body.model
    contains(model, "gpt-4")
}

# Guests: No LLM access at all
guest_accessing_llm if {
    guest_device
}

# Alert conditions
alert if { kids_using_expensive_model }
alert if { guest_accessing_llm }

message = msg if {
    kids_using_expensive_model
    msg := sprintf(
        "💸 %s is using expensive model: %s (allowed: gpt-3.5-turbo only)",
        [input.device.hostname, input.request.body.model]
    )
}

message = msg if {
    guest_accessing_llm
    msg := sprintf(
        "🚫 Guest device %s attempted to access %s",
        [input.device.ip, input.endpoint.domain]
    )
}

# Advisory mode: allow but alert
allow = true

# Enforce mode could block:
# deny if { kids_using_expensive_model }
# deny if { guest_accessing_llm }
```

---

### Example 8: Content Filtering

**File:** `content_filter.rego`

**Purpose:** Detect potentially inappropriate content requests.

```rego
package yori.policies.content

import future.keywords.contains
import future.keywords.if

# Content filtering: Detect inappropriate prompts

prompt = lower(input.request.body.messages[_].content)

# Inappropriate content keywords
violence_keywords = ["kill", "murder", "weapon", "bomb", "harm"]
adult_keywords = ["explicit", "nsfw", "adult content"]
illegal_keywords = ["illegal", "hack into", "break into", "steal"]

contains_violence if {
    keyword := violence_keywords[_]
    contains(prompt, keyword)
}

contains_adult_content if {
    keyword := adult_keywords[_]
    contains(prompt, keyword)
}

contains_illegal_content if {
    keyword := illegal_keywords[_]
    contains(prompt, keyword)
}

# Only monitor kids' devices
kid_device if { input.device.hostname == "sarahs-iphone" }
kid_device if { input.device.hostname == "jimmys-ipad" }

# Alert if kids access inappropriate content
alert if {
    kid_device
    contains_violence
}

alert if {
    kid_device
    contains_adult_content
}

alert if {
    kid_device
    contains_illegal_content
}

message = msg if {
    alert
    contains_violence
    msg := sprintf(
        "⚠️ Violent content detected in prompt from %s",
        [input.device.hostname]
    )
}

message = msg if {
    alert
    contains_adult_content
    msg := sprintf(
        "🔞 Adult content detected in prompt from %s",
        [input.device.hostname]
    )
}

message = msg if {
    alert
    contains_illegal_content
    msg := sprintf(
        "🚨 Illegal activity keywords detected from %s",
        [input.device.hostname]
    )
}

# Advisory: allow but warn parents
allow = true

# Enforce mode: could block specific content types
# deny if { kid_device; contains_adult_content }
```

---

### Example 9: Model Restrictions

**File:** `model_policy.rego`

**Purpose:** Restrict which AI models can be used.

```rego
package yori.policies.models

import future.keywords.contains
import future.keywords.in

# Model restrictions: Control which AI models are accessible

# Allowed models (whitelist approach)
allowed_models = [
    "gpt-3.5-turbo",
    "gpt-4-turbo",
    "claude-3-haiku",
    "claude-3-sonnet",
]

# Blocked models (blacklist approach)
blocked_models = [
    "gpt-4",  # Too expensive
    "claude-3-opus",  # Too expensive
]

model = input.request.body.model

# Check if model is in whitelist
model_allowed if {
    allowed := allowed_models[_]
    model == allowed
}

# Check if model is blocked
model_blocked if {
    blocked := blocked_models[_]
    model == blocked
}

# Alert on blocked model usage
alert if {
    model_blocked
}

message = msg if {
    alert
    msg := sprintf(
        "🚫 Blocked model usage: %s attempted to use %s (not allowed)",
        [input.device.hostname, model]
    )
}

# Advisory: allow but warn
allow = true

# Enforce mode: actually block
# deny if { model_blocked }
# allow if { model_allowed }
```

---

### Example 10: Time-Based Usage Limits

**File:** `time_limits.rego`

**Purpose:** Limit LLM usage to specific hours per day.

```rego
package yori.policies.time_limits

# Time-based limits: Hourly request quotas

# Get current hour and request count
current_hour = input.context.hour
requests_this_hour = input.context.request_count_this_hour

# Define hourly limits
hourly_limit_normal = 10
hourly_limit_peak = 20

# Peak hours (after school/work: 5 PM - 9 PM)
is_peak_hours if {
    current_hour >= 17
    current_hour < 21
}

# Determine applicable limit
applicable_limit = limit {
    is_peak_hours
    limit := hourly_limit_peak
} else = hourly_limit_normal

# Check if over limit
over_hourly_limit if {
    requests_this_hour >= applicable_limit
}

# Alert when approaching or exceeding limit
approaching_limit if {
    requests_this_hour >= (applicable_limit * 0.8)
    requests_this_hour < applicable_limit
}

alert if { approaching_limit }
alert if { over_hourly_limit }

message = msg if {
    approaching_limit
    msg := sprintf(
        "⏱️ Approaching hourly limit: %d/%d requests this hour",
        [requests_this_hour, applicable_limit]
    )
}

message = msg if {
    over_hourly_limit
    msg := sprintf(
        "🛑 Hourly limit exceeded: %d/%d requests this hour",
        [requests_this_hour, applicable_limit]
    )
}

# Advisory: allow but warn
allow = true

# Enforce mode: block when over limit
# deny if { over_hourly_limit }
```

---

### Example 11: Prompt Length Limits

**File:** `prompt_limits.rego`

**Purpose:** Alert on unusually long prompts (potential data exfiltration).

```rego
package yori.policies.prompt_size

# Prompt length limits: Detect unusually large prompts
# Could indicate copy-pasting large documents (privacy concern)

# Get all message contents
messages = input.request.body.messages

# Calculate total prompt length
total_length = sum([count(msg.content) | msg := messages[_]])

# Define thresholds (characters)
warning_length = 5000    # ~1,250 tokens
critical_length = 20000  # ~5,000 tokens

# Check thresholds
is_long_prompt if {
    total_length > warning_length
    total_length < critical_length
}

is_very_long_prompt if {
    total_length >= critical_length
}

# Alert on long prompts
alert if { is_long_prompt }
alert if { is_very_long_prompt }

message = msg if {
    is_long_prompt
    msg := sprintf(
        "⚠️ Long prompt detected from %s: %d characters (~%d tokens)",
        [input.device.hostname, total_length, total_length / 4]
    )
}

message = msg if {
    is_very_long_prompt
    msg := sprintf(
        "🚨 Very long prompt from %s: %d characters (~%d tokens) - possible document paste",
        [input.device.hostname, total_length, total_length / 4]
    )
}

# Allow in advisory mode (just monitoring)
allow = true

# Enforce mode could block extremely long prompts:
# deny if { is_very_long_prompt }
```

---

### Example 12: Multi-Device Coordination

**File:** `multi_device.rego`

**Purpose:** Detect when same account used from multiple devices simultaneously.

```rego
package yori.policies.multi_device

# Multi-device detection: Alert on simultaneous usage
# This example shows the concept - actual implementation would
# require external data about recent requests

# This would query recent requests from audit database
# For now, this is a placeholder showing the policy structure

# Hypothetical: devices that accessed LLMs in last 5 minutes
recent_devices = {
    "192.168.1.100",  # johns-laptop
    "192.168.1.101",  # johns-iphone
}

# Current device
current_device = input.device.ip

# Check if multiple devices active
multiple_devices_active if {
    count(recent_devices) > 1
    current_device in recent_devices
}

# This could indicate:
# 1. Account sharing (kids using parent's API key)
# 2. Compromised credentials
# 3. Normal behavior (person switching devices)

alert if {
    multiple_devices_active
}

message = msg if {
    alert
    msg := sprintf(
        "👥 Multi-device usage: %s and %d other device(s) active",
        [input.device.hostname, count(recent_devices) - 1]
    )
}

# Allow (this is informational)
allow = true
```

---

## Testing Policies

### Testing with Sample Data

YORI provides a policy testing mode:

```bash
# Test a policy with sample input
yori policy test bedtime.rego --input sample_request.json

# Sample input file
cat > sample_request.json <<EOF
{
  "request": {
    "body": {
      "model": "gpt-4",
      "messages": [{"role": "user", "content": "Help with homework"}]
    }
  },
  "device": {
    "hostname": "sarahs-iphone",
    "ip": "192.168.1.105"
  },
  "context": {
    "hour": 22,
    "day_of_week": "friday",
    "request_count_today": 15
  }
}
EOF

# Test the policy
yori policy test homework_helper.rego --input sample_request.json
```

### Expected Output

```json
{
  "allow": true,
  "alert": true,
  "message": "📚 Possible homework help: sarahs-iphone at 22:00 - general homework keywords",
  "policy": "yori.policies.homework"
}
```

### Dry-Run Mode

Test policies against real traffic without triggering alerts:

```bash
# Enable dry-run mode
yori policy dry-run enable

# Policies are evaluated but alerts not sent
# Results logged to /var/log/yori/policy-dry-run.log

# Disable dry-run
yori policy dry-run disable
```

---

## Policy Deployment

### Adding a New Policy

```bash
# 1. Create policy file
cat > /usr/local/etc/yori/policies/my_policy.rego <<EOF
package yori.policies.my_policy

alert {
    input.context.hour > 20
}

message = "After hours usage detected"
allow = true
EOF

# 2. Test the policy
yori policy test my_policy.rego --input test_data.json

# 3. Reload policies (no restart needed)
yori policy reload

# 4. Verify policy loaded
yori policy list
# Should show: my_policy.rego (loaded)
```

### Updating an Existing Policy

```bash
# 1. Edit policy file
ee /usr/local/etc/yori/policies/bedtime.rego

# 2. Validate syntax
yori policy validate bedtime.rego

# 3. Test with sample data
yori policy test bedtime.rego --input test_bedtime.json

# 4. Reload policies
yori policy reload
```

### Removing a Policy

```bash
# 1. Delete policy file
rm /usr/local/etc/yori/policies/old_policy.rego

# 2. Reload policies
yori policy reload

# Policy is immediately inactive
```

---

## Alert Configuration

### Email Alerts

Configure email notifications in `/usr/local/etc/yori/yori.conf`:

```yaml
alerts:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    smtp_user: your-email@gmail.com
    smtp_password: your-app-password
    from: yori@home.local
    to: parents@example.com
    subject_prefix: "[YORI Alert]"
```

### Push Notifications (Pushover)

```yaml
alerts:
  pushover:
    enabled: true
    user_key: your-pushover-user-key
    api_token: your-pushover-api-token
    priority: 0  # -2 to 2
```

### Web UI Alerts

Alerts automatically appear in the YORI dashboard:

1. Navigate to **Services → YORI → Alerts**
2. See real-time alerts as policies trigger
3. Acknowledge or dismiss alerts

---

## Troubleshooting Policies

### Policy Not Triggering

**Check policy is loaded:**
```bash
yori policy list
# Verify your policy appears
```

**Test with explicit input:**
```bash
# Create test input that should trigger alert
yori policy test your_policy.rego --input should_alert.json
# Verify "alert": true in output
```

**Check logs:**
```bash
tail -f /var/log/yori/policy.log
# Look for evaluation errors
```

### Policy Syntax Errors

```bash
# Validate Rego syntax
yori policy validate broken_policy.rego

# Common errors:
# - Missing package declaration
# - Undefined variables
# - Invalid regex syntax
# - Type mismatches
```

### Alerts Not Sending

```bash
# Test email configuration
yori alerts test email

# Test push notification
yori alerts test pushover

# Check alert logs
tail -f /var/log/yori/alerts.log
```

---

## Best Practices

1. **Start Simple:** Begin with observe mode and simple policies
2. **Test Thoroughly:** Use dry-run mode before enabling alerts
3. **Avoid False Positives:** Tune thresholds to match your usage patterns
4. **Document Policies:** Add comments explaining policy intent
5. **Version Control:** Keep policy files in git for change tracking
6. **Regular Review:** Review alerts weekly, adjust policies as needed

---

## Additional Resources

- **Open Policy Agent (OPA) Documentation:** https://www.openpolicyagent.org/docs/latest/
- **Rego Language Reference:** https://www.openpolicyagent.org/docs/latest/policy-language/
- **Rego Playground:** https://play.openpolicyagent.org/ (test policies interactively)
- **YORI Policy Examples Repository:** https://github.com/apathy-ca/yori-policies

---

**Policy guide version:** v0.1.0 (2026-01-19)

**Policy count:** 12 comprehensive examples covering parental controls, privacy, cost management, and enforcement scenarios.
