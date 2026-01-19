# YORI User Guide

Complete guide to using YORI for monitoring and managing LLM usage in your home network.

> ⚠️ **Development Status:** This guide describes the user experience for YORI v0.1.0. The OPNsense plugin UI is currently in development. This documentation serves as a specification for the intended user interface.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Dashboard Overview](#dashboard-overview)
- [Viewing Audit Logs](#viewing-audit-logs)
- [Managing Policies](#managing-policies)
- [Alerts and Notifications](#alerts-and-notifications)
- [Understanding Operating Modes](#understanding-operating-modes)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing YORI

After installation:

1. Log in to your OPNsense web UI (typically https://192.168.1.1)
2. Navigate to **Services → YORI** in the left sidebar
3. You'll see three main sections:
   - **Dashboard** - Usage overview and statistics
   - **Audit Logs** - Detailed request/response logs
   - **Settings** - Configuration and policies

### First-Time Setup Checklist

Before using YORI effectively:

- ✅ Install YORI plugin (see [Installation Guide](INSTALLATION.md))
- ✅ Configure operating mode (start with "Observe")
- ✅ Install CA certificate on all devices
- ✅ Set up NAT redirection rules
- ✅ Wait 24 hours to collect baseline data

---

## Dashboard Overview

The YORI dashboard provides at-a-glance visibility into your family's LLM usage.

### Main Dashboard Page

**Path:** Services → YORI → Dashboard

#### Usage Charts

**1. Requests Over Time (24 Hours)**

```
Bar chart showing LLM requests per hour

Example:
┌─────────────────────────────────────────┐
│ Requests (Last 24 Hours)                │
├─────────────────────────────────────────┤
│ 60│                                      │
│ 50│                                      │
│ 40│          ██                          │
│ 30│       ██ ██ ██                       │
│ 20│    ██ ██ ██ ██ ██                    │
│ 10│ ██ ██ ██ ██ ██ ██ ██                 │
│  0└─────────────────────────────────────┤
│    00 04 08 12 16 20 24 Hour            │
└─────────────────────────────────────────┘
```

**Insights:**
- Peak usage hours (typically after school/work)
- Overnight usage (potential bedtime violation)
- Unusual spikes (account sharing or automated tools)

**2. Top Endpoints (Pie Chart)**

```
Distribution of requests across LLM providers

Example:
         ┌───────────────┐
         │ OpenAI  45%   │ (Blue)
         │ Anthropic 30% │ (Green)
         │ Google   20%  │ (Yellow)
         │ Mistral   5%  │ (Red)
         └───────────────┘
```

**Insights:**
- Which LLM provider your family prefers
- Cost estimation (OpenAI GPT-4 more expensive than GPT-3.5)
- Migration opportunities (consolidate to one provider)

**3. Top Devices (Bar Chart)**

```
Which devices are making the most requests

Example:
┌─────────────────────────────────────────┐
│ Top Devices (Last 7 Days)               │
├─────────────────────────────────────────┤
│ johns-laptop     ████████████████ 45    │
│ sarahs-iphone    ██████████       28    │
│ moms-macbook     ██████           18    │
│ jimmys-ipad      ████             12    │
│ guest-device     ██                6    │
└─────────────────────────────────────────┘
```

**Insights:**
- Who is using LLMs the most
- Unexpected device activity (guest network usage)
- Individual usage patterns

**4. Recent Alerts**

```
Table of recent policy violations or noteworthy events

┌──────────────┬─────────────────┬──────────────────────────────┐
│ Time         │ Device          │ Alert Message                │
├──────────────┼─────────────────┼──────────────────────────────┤
│ 10:34 PM     │ sarahs-iphone   │ 🌙 Bedtime usage detected   │
│  6:15 PM     │ johns-laptop    │ 💰 High usage (120 req/day) │
│  3:20 PM     │ jimmys-ipad     │ 📚 Homework keywords found  │
│  1:45 PM     │ moms-macbook    │ 🔒 PII detected in prompt   │
└──────────────┴─────────────────┴──────────────────────────────┘
```

**Actions:**
- Click alert to view full request details
- Acknowledge to mark as reviewed
- Adjust policy if false positive

#### Statistics Cards

At the top of dashboard:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Total Requests  │  │ Average Tokens  │  │ Active Devices  │  │ Alerts (24h)    │
│                 │  │                 │  │                 │  │                 │
│      1,234      │  │      ~2,500     │  │        5        │  │       12        │
│                 │  │                 │  │                 │  │                 │
│  ↑ 15% vs prev  │  │  ↓ 8% vs prev   │  │  → no change    │  │  ↑ 3 vs prev    │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Metrics Explained:**
- **Total Requests:** Cumulative LLM API calls (all time)
- **Average Tokens:** Mean tokens per request (prompt + completion)
- **Active Devices:** Unique devices that made requests in last 24h
- **Alerts (24h):** Policy violations or noteworthy events today

### Filtering Dashboard Data

Use the filter controls at top of dashboard:

**Time Range:**
- Last 24 hours (default)
- Last 7 days
- Last 30 days
- Custom date range

**Device Filter:**
- All devices (default)
- Select specific device from dropdown

**Endpoint Filter:**
- All endpoints (default)
- OpenAI only
- Anthropic only
- Google only
- Mistral only

**Example:** View only Sarah's iPhone usage for last 7 days

```
[Time Range: Last 7 days ▼] [Device: sarahs-iphone ▼] [Endpoint: All ▼] [Apply]
```

---

## Viewing Audit Logs

Detailed request/response logs for forensic analysis and troubleshooting.

### Audit Log Page

**Path:** Services → YORI → Audit Logs

#### Log Table View

```
┌──────────┬───────────────┬──────────────┬─────────┬────────────────────────────────────┐
│ Time     │ Device        │ Endpoint     │ Model   │ Prompt Preview                     │
├──────────┼───────────────┼──────────────┼─────────┼────────────────────────────────────┤
│ 14:35:22 │ johns-laptop  │ OpenAI       │ gpt-4   │ "Write a Python function to..."    │
│ 14:32:18 │ sarahs-iphone │ Anthropic    │ claude  │ "Help me with my homework..."      │
│ 14:30:05 │ moms-macbook  │ Google       │ gemini  │ "Plan a vacation to..."            │
│ 14:25:41 │ jimmys-ipad   │ OpenAI       │ gpt-3.5 │ "Explain photosynthesis..."        │
└──────────┴───────────────┴──────────────┴─────────┴────────────────────────────────────┘
```

**Click any row to expand full details.**

#### Detailed Log Entry

```
┌─────────────────────────────────────────────────────────────────┐
│ Request Details                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Request ID:    req_20260119_143522_abc123                       │
│ Timestamp:     2026-01-19 14:35:22                              │
│ Device:        johns-laptop (192.168.1.105)                     │
│ Endpoint:      api.openai.com                                   │
│ Model:         gpt-4                                            │
│ Latency:       247ms                                            │
│ Policy:        Allowed (observe mode)                           │
├─────────────────────────────────────────────────────────────────┤
│ Request Body (JSON)                                             │
├─────────────────────────────────────────────────────────────────┤
│ {                                                               │
│   "model": "gpt-4",                                             │
│   "messages": [                                                 │
│     {                                                           │
│       "role": "user",                                           │
│       "content": "Write a Python function to calculate..."      │
│     }                                                           │
│   ],                                                            │
│   "temperature": 0.7,                                           │
│   "max_tokens": 500                                             │
│ }                                                               │
├─────────────────────────────────────────────────────────────────┤
│ Response Body (JSON) - Abbreviated                              │
├─────────────────────────────────────────────────────────────────┤
│ {                                                               │
│   "id": "chatcmpl-abc123",                                      │
│   "model": "gpt-4-0613",                                        │
│   "choices": [                                                  │
│     {                                                           │
│       "message": {                                              │
│         "role": "assistant",                                    │
│         "content": "Here's a Python function..."                │
│       }                                                         │
│     }                                                           │
│   ],                                                            │
│   "usage": {                                                    │
│     "prompt_tokens": 18,                                        │
│     "completion_tokens": 145,                                   │
│     "total_tokens": 163                                         │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘

[Export to CSV] [Copy JSON] [Delete Entry]
```

### Searching and Filtering Logs

**Search Bar:**

```
[🔍 Search prompts, devices, or models...]
```

**Example searches:**
- `homework` - Find all prompts mentioning homework
- `sarahs-iphone` - All requests from specific device
- `gpt-4` - All requests using GPT-4 model
- `api.anthropic.com` - All Claude requests

**Advanced Filters:**

```
[Date Range: Last 7 days ▼]
[Device: All devices ▼]
[Endpoint: All endpoints ▼]
[Model: All models ▼]
[Policy Decision: All ▼]  (allow, deny, alert)

[Apply Filters]
```

### Exporting Audit Logs

**Export Options:**

1. **CSV Export** - For Excel/Google Sheets analysis

   ```
   [Export to CSV]

   Downloads: yori_audit_20260119.csv

   Columns: timestamp, device_ip, device_hostname, endpoint,
            model, prompt, response, tokens, latency_ms
   ```

2. **JSON Export** - For programmatic analysis

   ```
   [Export to JSON]

   Downloads: yori_audit_20260119.json

   Array of full request/response objects
   ```

**Use Cases for Export:**
- Import into Excel for pivot tables and charts
- Analyze with Python/R for usage patterns
- Backup before retention cleanup
- Share anonymized data for research

---

## Managing Policies

Control LLM usage with declarative Rego policies.

### Policy Management Page

**Path:** Services → YORI → Policies

#### Installed Policies List

```
┌─────────────────┬─────────┬────────────┬────────────────────────┐
│ Policy Name     │ Status  │ Alerts (7d)│ Description            │
├─────────────────┼─────────┼────────────┼────────────────────────┤
│ home_default    │ Active  │      0     │ Default allow-all      │
│ bedtime         │ Active  │     12     │ After-hours alerts     │
│ high_usage      │ Active  │      5     │ Usage threshold alerts │
│ privacy         │ Active  │      2     │ PII detection          │
│ homework_helper │ Enabled │      8     │ Educational keywords   │
└─────────────────┴─────────┴────────────┴────────────────────────┘

[+ Add Policy] [Upload Policy File]
```

**Policy Status:**
- **Active:** Currently evaluating and triggering alerts
- **Enabled:** Loaded but not triggering (dry-run mode)
- **Disabled:** Not loaded
- **Error:** Syntax error or failed validation

#### Enabling/Disabling Policies

Click policy row → Toggle switch:

```
┌─────────────────────────────────────────────┐
│ bedtime.rego                                │
├─────────────────────────────────────────────┤
│ Status: [●───────] Active                  │
│                                             │
│ Description: Alert when kids use LLMs      │
│ after 9 PM bedtime.                        │
│                                             │
│ Alerts triggered (last 7 days): 12         │
│ - 8 from sarahs-iphone                     │
│ - 4 from jimmys-ipad                       │
│                                             │
│ [Disable Policy] [Edit Policy] [Test]      │
└─────────────────────────────────────────────┘
```

### Installing Pre-Built Policy Templates

YORI provides templates for common use cases:

```
[📦 Policy Templates]

┌─────────────────────────────────────────────┐
│ Bedtime Monitoring                          │
│ Alert when devices use LLMs after 9 PM     │
│ [Install Template]                          │
├─────────────────────────────────────────────┤
│ High Usage Alert                            │
│ Alert when >50 requests per day            │
│ [Install Template]                          │
├─────────────────────────────────────────────┤
│ PII Detection                               │
│ Alert when SSN, credit cards in prompts   │
│ [Install Template]                          │
└─────────────────────────────────────────────┘
```

**Installation Process:**
1. Click **[Install Template]**
2. Review policy code (Rego)
3. Customize thresholds (optional)
4. Click **[Install]**
5. Policy is immediately active

### Writing Custom Policies

See [Policy Guide](POLICY_GUIDE.md) for detailed examples.

**Quick Start:**

1. Click **[+ Add Policy]**
2. Give it a name: `my_custom_policy`
3. Write Rego code:

   ```rego
   package yori.policies.my_custom_policy

   alert {
       input.context.hour > 22
   }

   message = "Late night LLM usage detected"
   allow = true
   ```

4. Click **[Test Policy]** with sample data
5. If valid, click **[Save and Activate]**

---

## Alerts and Notifications

Stay informed about policy violations and unusual activity.

### Alert Inbox

**Path:** Services → YORI → Alerts

```
┌──────────────┬──────────────┬────────────────────────────────┬─────────┐
│ Time         │ Severity     │ Message                        │ Status  │
├──────────────┼──────────────┼────────────────────────────────┼─────────┤
│ 10:34 PM     │ 🌙 Info      │ Bedtime usage: sarahs-iphone  │ New     │
│  6:15 PM     │ ⚠️ Warning   │ High usage: johns-laptop      │ Ack     │
│  3:20 PM     │ 📚 Info      │ Homework keywords detected     │ Ack     │
│  1:45 PM     │ 🔒 Critical  │ PII detected in prompt         │ New     │
└──────────────┴──────────────┴────────────────────────────────┴─────────┘

[Acknowledge All] [Mark as Read] [Delete]
```

**Alert Actions:**
- **View Details** - See full request that triggered alert
- **Acknowledge** - Mark as reviewed
- **Snooze** - Suppress similar alerts for 24 hours
- **Delete** - Remove from inbox

### Configuring Email Notifications

**Path:** Services → YORI → Settings → Alerts

```
┌─────────────────────────────────────────────┐
│ Email Notifications                         │
├─────────────────────────────────────────────┤
│ Enabled: [✓]                                │
│                                             │
│ SMTP Server:   smtp.gmail.com              │
│ SMTP Port:     587                          │
│ SMTP User:     your-email@gmail.com        │
│ SMTP Password: ****************            │
│                                             │
│ From Address:  yori@home.local             │
│ To Address:    parents@example.com         │
│                                             │
│ Subject Prefix: [YORI Alert]               │
│                                             │
│ [Test Email] [Save Settings]                │
└─────────────────────────────────────────────┘
```

**Email Alert Example:**

```
Subject: [YORI Alert] Bedtime usage detected

From: yori@home.local
To: parents@example.com
Date: 2026-01-19 22:34:17

Alert Details:
- Device: sarahs-iphone (192.168.1.105)
- Endpoint: api.openai.com
- Model: gpt-4
- Time: 10:34 PM

Message:
🌙 Bedtime LLM usage detected: sarahs-iphone used api.openai.com at 22:00

View full details:
https://192.168.1.1/ui/yori/alerts/20260119_223417

--
YORI Home LLM Gateway
```

### Configuring Push Notifications (Pushover)

```
┌─────────────────────────────────────────────┐
│ Push Notifications (Pushover)               │
├─────────────────────────────────────────────┤
│ Enabled: [✓]                                │
│                                             │
│ User Key:   ******************************  │
│ API Token:  ******************************  │
│                                             │
│ Priority:   [Normal ▼]                      │
│  - Lowest (-2)                              │
│  - Low (-1)                                 │
│  - Normal (0) ✓                             │
│  - High (1)                                 │
│  - Emergency (2)                            │
│                                             │
│ [Test Push] [Save Settings]                 │
└─────────────────────────────────────────────┘
```

---

## Understanding Operating Modes

YORI has three operating modes that control how policies are enforced.

### Mode Comparison

| Mode | Logs Traffic | Sends Alerts | Can Block | Use Case |
|------|-------------|--------------|-----------|----------|
| **Observe** | ✅ | ❌ | ❌ | Learning baseline usage |
| **Advisory** | ✅ | ✅ | ❌ | Awareness without control |
| **Enforce** | ✅ | ✅ | ✅ | Active governance |

### Changing Operating Mode

**Path:** Services → YORI → Settings → General

```
┌─────────────────────────────────────────────┐
│ Operating Mode                              │
├─────────────────────────────────────────────┤
│ Current Mode: [Advisory ▼]                  │
│                                             │
│ ○ Observe                                   │
│   Log all traffic, no alerts                │
│   Best for: First 1-2 weeks                 │
│                                             │
│ ● Advisory                                  │
│   Log traffic + send alerts                 │
│   Best for: Most families                   │
│                                             │
│ ○ Enforce (Advanced)                        │
│   Can block traffic based on policies       │
│   Best for: Strict parental controls        │
│   ⚠️ Requires testing policies first        │
│                                             │
│ [Save and Restart Service]                  │
└─────────────────────────────────────────────┘
```

**Recommendation:** Observe → Advisory → Enforce progression

---

## Common Use Cases

### Use Case 1: Monitor Family AI Usage

**Goal:** Understand who uses which LLMs and when.

**Steps:**
1. Set mode to **Observe** for 1 week
2. View **Dashboard → Top Devices** chart
3. Export audit logs to CSV
4. Analyze in Excel:
   - Create pivot table: Rows=Device, Columns=Hour, Values=Count of requests
   - Identify peak usage times per family member

**Sample Insight:**
> "Sarah uses ChatGPT heavily on weekday afternoons (homework time), while John prefers Claude on weekends (hobby projects)."

### Use Case 2: Set Up Bedtime Policy

**Goal:** Get alerts when kids use LLMs after 9 PM.

**Steps:**
1. Install **Bedtime Monitoring** policy template
2. Edit policy to set bedtime hour (default 21:00)
3. Add kids' device hostnames to policy
4. Enable **Email Notifications**
5. Switch to **Advisory** mode
6. Test by making LLM request at 9:30 PM from kid's device

**Expected Result:**
- Email alert received within 1 minute
- Alert appears in dashboard
- Request still allowed (advisory mode)

### Use Case 3: Track Monthly LLM Costs

**Goal:** Estimate API costs to decide between free tier and paid plans.

**Steps:**
1. Export audit logs (last 30 days) to CSV
2. Add column: `estimated_cost`
3. Formula: `=IF(model="gpt-4", total_tokens/1000 * 0.06, total_tokens/1000 * 0.002)`
4. Sum `estimated_cost` column
5. Compare to ChatGPT Plus subscription ($20/month)

**Decision Framework:**
- If estimated cost < $20/month: Stay on API, use YORI for free-tier management
- If estimated cost > $20/month: Consider ChatGPT Plus for unlimited use

### Use Case 4: Detect Account Sharing

**Goal:** Find out if kids are using parents' API keys.

**Steps:**
1. View **Dashboard → Top Devices** (last 7 days)
2. Look for unexpected devices
3. Click device to see all requests
4. Correlate with family schedules
   - Example: Parent's laptop shows activity during school hours → kid borrowing laptop

**Policy to Add:**
```rego
# Alert when parent device used during school hours
alert {
    input.device.hostname == "dads-laptop"
    hour := input.context.hour
    day := input.context.day_of_week

    day != "saturday"
    day != "sunday"
    hour >= 9
    hour < 15  # 9 AM - 3 PM school hours
}
```

---

## Troubleshooting

### Dashboard Shows "No Data"

**Symptoms:**
- Dashboard charts empty
- "0 requests" in statistics cards

**Causes & Solutions:**

1. **YORI service not running**
   ```bash
   service yori status
   # If not running: service yori start
   ```

2. **No traffic intercepted (NAT rules not working)**
   - Check Firewall → NAT → Port Forward
   - Verify LLM_Endpoints alias exists
   - Test: `tcpdump -i lo0 -n tcp port 8443`

3. **Devices not trusting CA certificate**
   - Verify CA installed on devices
   - Test: Visit https://api.openai.com in browser
   - Should show YORI certificate, not OpenAI's

4. **Waiting for data collection**
   - Dashboard requires at least 1 request
   - Generate test request from device
   - Refresh dashboard after 5 minutes

### Audit Logs Missing Requests

**Symptoms:**
- Some requests appear in dashboard but not audit logs
- Gaps in audit log timeline

**Cause:** SQLite write errors or database corruption

**Solution:**
```bash
# Check database integrity
sqlite3 /var/db/yori/audit.db "PRAGMA integrity_check;"

# If corrupted, rebuild from backup
cp /var/db/yori/audit.db.backup /var/db/yori/audit.db

# If no backup, start fresh (data loss)
rm /var/db/yori/audit.db
service yori restart
```

### Alerts Not Sending

**Symptoms:**
- Policies triggering (visible in logs)
- No email/push notifications received

**Diagnosis:**
```bash
# Check alert logs
tail -f /var/log/yori/alerts.log

# Test email manually
yori alerts test email

# Test push manually
yori alerts test pushover
```

**Common Issues:**
1. SMTP credentials invalid → Re-enter password
2. Gmail blocking "less secure apps" → Use app-specific password
3. Pushover API token wrong → Regenerate in Pushover dashboard

### Policy Not Triggering

**Symptoms:**
- Policy shows "Active" but no alerts
- Manually tested policy works

**Diagnosis:**
```bash
# Check policy syntax
yori policy validate /usr/local/etc/yori/policies/my_policy.rego

# Check policy is loaded
yori policy list
# Should show your policy

# Enable debug logging
yori --log-level debug

# Watch policy evaluation
tail -f /var/log/yori/policy.log
```

**Common Issues:**
1. Policy conditions too strict (never match)
2. Device hostname mismatch (check actual hostname in audit logs)
3. Time zone issues (policy checks UTC but expects local time)

---

## Best Practices

1. **Start with Observe Mode**
   - Run for 1-2 weeks before enabling alerts
   - Understand normal usage patterns
   - Avoid false positive alerts

2. **Regularly Review Dashboard**
   - Weekly review of usage trends
   - Monthly cost estimation
   - Adjust policies based on findings

3. **Test Policies Before Enabling**
   - Use dry-run mode first
   - Test with known-good and known-bad inputs
   - Confirm alert notifications work

4. **Export Audit Logs Monthly**
   - Backup before retention cleanup
   - Archive for long-term trends
   - Use for annual reviews

5. **Discuss with Family**
   - Transparency about monitoring
   - Explain privacy protections (data stays local)
   - Adjust policies based on feedback

---

## Next Steps

- **[Configuration Reference](CONFIGURATION.md)** - Detailed config options
- **[Policy Guide](POLICY_GUIDE.md)** - Writing custom policies
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[FAQ](FAQ.md)** - Frequently asked questions

---

**User guide version:** v0.1.0 (2026-01-19)
