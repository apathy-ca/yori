# YORI Quick Start Guide

**Goal:** Get YORI monitoring your LLM traffic in 15 minutes

> ⚠️ **Development Status:** YORI is in early development. This guide describes the intended user experience for v0.1.0. Not all features are currently functional. See [Project Status](#development-status) below.

---

## Prerequisites

Before starting, ensure you have:

- ✅ OPNsense 24.1+ router installed
- ✅ Admin access to OPNsense web UI
- ✅ At least 512MB free RAM
- ✅ 1GB free disk space
- ✅ Basic familiarity with SSL/TLS certificates

**Estimated Time:** 15 minutes

---

## Step 1: Install YORI Plugin (3 minutes)

### Option A: From OPNsense Plugin Repository (Recommended)

1. Log in to your OPNsense web UI
2. Navigate to **System → Firmware → Plugins**
3. Search for "yori"
4. Click **+** to install `os-yori`
5. Wait for installation to complete

### Option B: Manual Installation

```bash
# SSH into your OPNsense router
ssh root@192.168.1.1

# Install the package
pkg install os-yori

# Enable the service
service yori enable
```

**Verify Installation:**
```bash
pkg info os-yori
# Should show version 0.1.0 or later
```

---

## Step 2: Initial Configuration (5 minutes)

### Access YORI Dashboard

1. In OPNsense web UI, navigate to **Services → YORI → Dashboard**
2. You'll see the YORI configuration page

### Configure Operating Mode

1. Select **Mode: Observe** (recommended for first week)
   - **Observe:** Logs all traffic, no blocking
   - **Advisory:** Sends alerts but allows traffic
   - **Enforce:** Can block traffic based on policies

2. Leave default listen address: `0.0.0.0:8443`

### Enable LLM Endpoints

Check the endpoints you want to monitor:

- ✅ **api.openai.com** (ChatGPT, GPT-4)
- ✅ **api.anthropic.com** (Claude)
- ✅ **gemini.google.com** (Gemini)
- ✅ **api.mistral.ai** (Mistral)

Leave all enabled for comprehensive monitoring.

### Configure Audit Logging

Default settings are fine for most users:

- Database: `/var/db/yori/audit.db`
- Retention: 365 days
- SQLite auto-vacuum: Enabled

**Click "Save and Start Service"**

---

## Step 3: Install CA Certificate (5 minutes)

For YORI to intercept HTTPS traffic to LLM providers, devices must trust YORI's Certificate Authority.

### Generate YORI CA Certificate

In OPNsense web UI:

1. Navigate to **Services → YORI → Certificate Management**
2. Click **Generate YORI CA**
3. Fill in details:
   - Common Name: `YORI Home LLM Gateway`
   - Valid for: 3650 days (10 years)
4. Click **Generate**
5. Click **Download CA Certificate** → Save as `yori-ca.crt`

### Install on Your Devices

#### macOS

1. Double-click `yori-ca.crt`
2. Keychain Access opens → Select "System" keychain
3. Find "YORI Home LLM Gateway" certificate
4. Right-click → Get Info → Trust → Always Trust

#### Windows 10/11

1. Right-click `yori-ca.crt` → Install Certificate
2. Store Location: Local Machine (requires admin)
3. Place in: Trusted Root Certification Authorities
4. Click Finish

#### iOS/iPadOS

1. AirDrop `yori-ca.crt` to device
2. Settings → Profile Downloaded → Install
3. Enter passcode
4. Settings → General → About → Certificate Trust Settings
5. Enable full trust for "YORI Home LLM Gateway"

#### Android

1. Settings → Security → Encryption & credentials
2. Install from storage → Select `yori-ca.crt`
3. Name: "YORI CA"
4. Credential use: VPN and apps

**Verify Installation:** Browse to https://www.howsmyssl.com/ and check that TLS works normally.

---

## Step 4: Configure Transparent Proxy (2 minutes)

### Set Up Transparent Proxying

YORI needs to intercept traffic destined for LLM APIs.

1. Navigate to **Firewall → NAT → Port Forward**
2. Click **Add** to create a new rule:
   - Interface: LAN
   - Protocol: TCP
   - Destination: Any
   - Destination port range: 443 (HTTPS)
   - Redirect target IP: 127.0.0.1
   - Redirect target port: 8443 (YORI)
3. Add destination conditions:
   - Click **Advanced** → **Destination Address**
   - Add alias for LLM endpoints (create alias with all enabled endpoints)
4. Save and Apply Changes

### Create LLM Endpoint Alias

1. Navigate to **Firewall → Aliases**
2. Click **Add**
   - Name: `LLM_Endpoints`
   - Type: Host(s)
   - Content:
     ```
     api.openai.com
     api.anthropic.com
     gemini.google.com
     api.mistral.ai
     ```
3. Save and Apply

Update your NAT rule to use this alias for destination filtering.

---

## Step 5: Verify It's Working (2 minutes)

### Test LLM Traffic Capture

1. On a device with the CA certificate installed, visit https://chat.openai.com
2. Send a test message to ChatGPT
3. In OPNsense, navigate to **Services → YORI → Audit Logs**

You should see:
- Timestamp of request
- Device IP address
- Destination: api.openai.com
- Request method: POST
- Endpoint: /v1/chat/completions

### Check Dashboard Statistics

1. Navigate to **Services → YORI → Dashboard**
2. You should see:
   - **Requests (Last 24 Hours):** Chart with at least 1 request
   - **Top Endpoints:** Pie chart showing OpenAI
   - **Top Devices:** Your device IP listed

---

## What's Next?

### Week 1: Observe Mode

Keep YORI in **Observe mode** for at least a week to:
- Understand your family's AI usage patterns
- Identify all devices making LLM requests
- Establish baseline activity

### Week 2+: Set Up Policies

Once you understand your usage, create policies:

1. Navigate to **Services → YORI → Policies**
2. Try pre-built templates:
   - **Bedtime:** Alert when kids use ChatGPT after 9 PM
   - **High Usage:** Alert when any device exceeds 50 requests/day
   - **Homework Helper:** Detect potential homework cheating

See [Policy Guide](POLICY_GUIDE.md) for custom policy creation.

### Export and Analysis

Export your audit logs for deeper analysis:

1. **Services → YORI → Audit Logs** → **Export to CSV**
2. Open in Excel/Google Sheets
3. Create pivot tables to analyze:
   - Usage by time of day
   - Cost estimation (requests × model pricing)
   - Popular topics (requires prompt analysis)

---

## Troubleshooting

### Common Issues

**❌ "Certificate not trusted" errors on devices**
- Verify CA certificate is installed in system trust store (not user)
- iOS: Check Certificate Trust Settings is enabled
- Try restarting browser/device after installation

**❌ No traffic showing in audit logs**
- Check NAT rule is active: Firewall → NAT → Port Forward
- Verify LLM_Endpoints alias includes correct domains
- Test: `curl -v https://api.openai.com` should connect through YORI
- Check service is running: `service yori status`

**❌ LLM requests failing (503/504 errors)**
- Check YORI service logs: `tail -f /var/log/yori/yori.log`
- Verify proxy mode allows traffic (Observe mode should never block)
- Test direct connectivity: `nc -zv api.openai.com 443` from OPNsense

**❌ Dashboard shows "No data available"**
- Wait 5 minutes for initial data collection
- Check SQLite database exists: `ls -lh /var/db/yori/audit.db`
- Verify retention settings haven't expired logs

See [Troubleshooting Guide](TROUBLESHOOTING.md) for more solutions.

---

## Performance Expectations

On typical home router hardware:

- **Latency Impact:** <10ms added to LLM requests
- **Memory Usage:** ~50MB RAM
- **Disk Usage:** ~1MB per 1,000 requests (with 365-day retention)
- **CPU Impact:** <5% during normal usage

YORI uses efficient Rust core components (from SARK) for minimal overhead.

---

## Security Considerations

**What YORI Can See:**
- Full request and response bodies to/from LLM APIs
- Device IP addresses and user agents
- Timestamps and request metadata

**What YORI Cannot See:**
- Traffic to other HTTPS sites (only LLM endpoints are intercepted)
- Encrypted messaging (Signal, WhatsApp, etc.)
- Banking or sensitive non-LLM traffic

**Data Storage:**
- All audit logs stored locally on OPNsense router
- No data sent to external servers
- SQLite database encrypted at rest (if OPNsense disk encryption enabled)

See [Security Policy](../SECURITY.md) for more details.

---

## Development Status

> ⚠️ **Current Implementation Status (as of v0.0.1-alpha):**
>
> This quick start guide describes the **intended user experience** for YORI v0.1.0.
>
> **Currently Implemented:**
> - Configuration system (YAML loading)
> - Basic FastAPI server structure
> - PyO3 bindings skeleton
>
> **Not Yet Implemented:**
> - OPNsense plugin UI (Services → YORI menu)
> - Transparent proxy interception
> - SQLite audit logging
> - Dashboard charts and visualizations
> - Certificate management UI
>
> **For Developers:** This guide serves as a specification for the target UX. If you're interested in contributing to make this guide accurate, see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Getting Help

- **Documentation:** [docs/](../docs/)
- **User Guide:** [USER_GUIDE.md](USER_GUIDE.md) - Detailed feature documentation
- **Installation Issues:** [INSTALLATION.md](INSTALLATION.md) - Troubleshooting installation
- **Policy Help:** [POLICY_GUIDE.md](POLICY_GUIDE.md) - Writing custom policies
- **FAQ:** [FAQ.md](FAQ.md) - Common questions answered

**Community Support:**
- GitHub Issues: Report bugs and request features
- GitHub Discussions: Ask questions and share tips
- Security Issues: Use GitHub Security Advisories (private reporting)

---

**Congratulations! YORI is now monitoring your family's LLM usage. Welcome to transparent AI governance at home.**
