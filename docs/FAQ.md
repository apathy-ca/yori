# YORI Frequently Asked Questions

Common questions about YORI, its capabilities, and how to use it effectively.

---

## General Questions

### What is YORI?

YORI (yet to be backronym-ed!) is a lightweight LLM gateway that runs on your home router (OPNsense) to provide visibility and optional control over AI assistant usage. Think of it as "parental controls for ChatGPT" - it helps families understand and manage how LLMs are being used in their home network.

**Key features:**
- **Transparent monitoring** of LLM API traffic (ChatGPT, Claude, Gemini, etc.)
- **Audit logging** to SQLite database (1 year retention by default)
- **Policy-based alerts** for bedtime violations, high usage, PII detection, etc.
- **Optional enforcement** mode to block specific requests (parental controls)
- **Privacy-first** design - all data stays on your local network

---

### How does YORI differ from ChatGPT parental controls?

ChatGPT (and other LLM providers) offer limited parental controls:

| Feature | ChatGPT Controls | YORI |
|---------|-----------------|------|
| Cross-provider | ❌ OpenAI only | ✅ All LLMs (OpenAI, Anthropic, Google, Mistral) |
| Visibility | ❌ Limited usage stats | ✅ Full request/response logs |
| Custom policies | ❌ No | ✅ Write Rego policies |
| Data location | ☁️ Cloud (OpenAI servers) | 🏠 On-premise (your router) |
| Cost | 💰 Requires ChatGPT Plus ($20/mo) | 🆓 Free (DIY) |
| Multi-device | ✅ Per account | ✅ Network-wide (all devices) |

**YORI's advantage:** Works across all LLM providers and gives you complete control over data.

---

### Is YORI safe to use? Will it break my internet?

Yes, YORI is designed with safety in mind:

**Fail-open design:** If YORI crashes or stops working, your internet continues to function normally. LLM traffic will bypass YORI and flow directly to providers.

**Limited scope:** YORI only intercepts traffic to specific LLM endpoints (api.openai.com, api.anthropic.com, etc.). All other internet traffic (web browsing, streaming, gaming) is completely unaffected.

**Observe mode default:** YORI starts in "observe" mode which only logs traffic without blocking anything.

**Tested on home routers:** YORI is designed for commodity hardware (Protectli, PC Engines APU, Netgate) running OPNsense.

---

### Do I need technical skills to use YORI?

**For basic usage:** Moderate technical skills required.

You need to be comfortable with:
- Installing packages on OPNsense (web UI, not command line)
- Creating firewall NAT rules (guided in documentation)
- Installing CA certificates on devices (documented step-by-step)

**For advanced usage:** Higher technical skills recommended.

Writing custom Rego policies, debugging issues, or building from source requires:
- Understanding of YAML configuration files
- Basic programming concepts (for policy writing)
- Familiarity with command line and SSH (for troubleshooting)

**Getting help:** Extensive documentation, example policies, and community support available.

---

### Can YORI see my LLM conversations?

**Yes, by design.** YORI performs TLS interception to analyze LLM traffic, which means it can see the full plaintext of your prompts and the AI's responses.

**Privacy protections:**
- All data stays on your local router (never sent to cloud)
- Audit logs are encrypted at rest (if you enable OPNsense disk encryption)
- You control retention period (default 365 days, can reduce to 30 days)
- Audit logs can be deleted at any time
- No telemetry or phone-home to YORI developers

**Trust model:** You must trust your home router (which you should already, since it sees all your internet traffic).

**Alternative:** If you're uncomfortable with this, YORI may not be the right tool. Consider provider-level controls instead (e.g., OpenAI's parental controls).

---

## Installation and Setup

### What hardware do I need to run YORI?

**Minimum requirements:**
- OPNsense 24.1+ router
- 512MB RAM available (after OPNsense overhead)
- 1GB disk space (more for extended audit log retention)
- x86_64 (amd64) CPU architecture

**Tested hardware:**
- **Protectli Vault** (FW4B, FW6) - ✅ Recommended
- **PC Engines** APU2/APU3/APU4 - ✅ Recommended
- **Netgate** SG-1100, SG-2100, SG-3100 - ✅ Works well
- **Dell OptiPlex Micro** (repurposed as router) - ✅ Budget option
- **Raspberry Pi 4** - ⚠️ ARM64 support experimental

**Not recommended:**
- Routers with <512MB RAM (will cause OOM crashes)
- Non-OPNsense platforms (pfSense support planned for future)

---

### How long does installation take?

**Quick installation:** 15 minutes (if you already have OPNsense running)

Breakdown:
- Install YORI plugin: 3 minutes
- Configure settings: 5 minutes
- Set up NAT rules: 5 minutes
- Install CA cert on first device: 2 minutes

**Full setup:** 1-2 hours (including CA installation on all devices)

If installing CA certificates on 10+ devices (phones, tablets, laptops), budget extra time.

---

### Can I use YORI with pfSense instead of OPNsense?

**Not currently.** YORI v0.1.0 is designed specifically for OPNsense (PHP/MVC plugin structure, Volt templates).

**Future plans:** pfSense port is on the roadmap for v0.3.0, but requires significant rework of the plugin layer.

**Workaround:** Advanced users can run YORI as a standalone service on pfSense (without the web UI), but this is unsupported and requires manual configuration.

---

## Features and Capabilities

### What LLM providers does YORI support?

**Default supported endpoints (v0.1.0):**
- **OpenAI** - api.openai.com (ChatGPT, GPT-4, DALL-E)
- **Anthropic** - api.anthropic.com (Claude 3.5, Claude 3)
- **Google** - gemini.google.com (Gemini Pro, Gemini Ultra)
- **Mistral AI** - api.mistral.ai (Mistral Large, Medium, Small)

**Adding custom endpoints:**
Edit `/usr/local/etc/yori/yori.conf`:
```yaml
endpoints:
  - domain: api.cohere.ai
    enabled: true
  - domain: api.together.xyz
    enabled: true
```

**Limitations:**
- Only HTTPS endpoints supported (no HTTP)
- Must be domain-based (IP addresses not supported)
- Wildcard domains planned for v0.2.0

---

### Can YORI block specific prompts or content?

**Yes, in "Enforce" mode.**

YORI policies (written in Rego) can:
- Detect keywords in prompts
- Block requests based on device, time, or content
- Allow/deny specific AI models (e.g., only allow GPT-3.5, block GPT-4)

**Example policy:**
```rego
# Block adult content keywords on kids' devices
deny {
    kid_device
    contains(lower(prompt), "inappropriate keyword")
}
```

**Important:** Blocking requires switching from "Observe" or "Advisory" mode to "Enforce" mode. Always test policies thoroughly before enabling enforcement.

---

### Can I export my audit logs for analysis?

**Yes, multiple formats:**

1. **CSV export** (via web UI)
   - Services → YORI → Audit Logs → Export to CSV
   - Opens in Excel/Google Sheets
   - Columns: timestamp, device, endpoint, model, prompt, response, tokens

2. **JSON export** (via command line)
   ```bash
   yori audit export --format json --start 2026-01-01 --end 2026-01-31 > jan2026.json
   ```

3. **Direct SQLite access**
   ```bash
   sqlite3 /var/db/yori/audit.db
   SELECT * FROM audit_events WHERE device_ip = '192.168.1.105';
   ```

**Use cases:**
- Cost analysis (estimate API spend)
- Usage patterns (pivot tables in Excel)
- Long-term archival (before retention cleanup)
- Academic research (anonymize first!)

---

### Does YORI slow down my LLM requests?

**Minimal impact:** YORI adds <50ms p95 latency.

**Breakdown:**
| Stage | Latency |
|-------|---------|
| NAT redirect | <1ms |
| TLS termination | <10ms |
| Policy evaluation | <5ms |
| SQLite write | <5ms |
| Proxy overhead | <5ms |
| **Total YORI overhead** | **<25ms** |

For context:
- Typical LLM API call: 200-500ms
- Network latency to LLM provider: 50-150ms
- YORI overhead: ~25ms (5-10% of total)

**Performance tips:**
- Use "Observe" mode if you don't need policies (skips evaluation)
- Reduce retention days to improve SQLite write speed
- Ensure router has adequate RAM (512MB minimum)

---

## Privacy and Security

### Is my data sent to YORI developers or third parties?

**No. Absolutely not.**

YORI is a fully on-premise solution:
- ✅ All audit logs stored locally on your router
- ✅ No telemetry or analytics sent to developers
- ✅ No cloud dependencies
- ✅ Open source (audit the code yourself)

**The only external connections YORI makes:**
- To LLM providers (OpenAI, Anthropic, etc.) on behalf of your devices
- Package updates (if you manually check for updates via OPNsense UI)

**Privacy guarantee:** Your family's conversations with ChatGPT/Claude stay between your home network and the LLM provider. YORI developers never see your data.

---

### What happens if someone hacks my router?

**If an attacker gains root access to your OPNsense router:**

**What they can access:**
- ✅ YORI audit logs (all LLM conversations)
- ✅ YORI CA private key (can intercept traffic)
- ✅ All network traffic (not specific to YORI)

**Mitigations:**
1. **Keep OPNsense updated** - Security patches released regularly
2. **Strong passwords** - Use SSH keys, not passwords
3. **Firewall management interface** - Don't expose OPNsense UI to internet
4. **Enable disk encryption** - Protects audit logs at rest
5. **Regular backups** - Recover from compromise

**Reality check:** If your router is compromised, YORI is the least of your problems. The attacker can see all your internet traffic, change DNS settings, inject malware, etc.

**YORI doesn't make this worse** - the CA certificate attack vector exists for any TLS-intercepting proxy.

---

### Can my kids bypass YORI?

**Possible bypass methods:**

1. **VPN/Proxy usage**
   - Kid uses VPN app to tunnel LLM traffic
   - **Mitigation:** Block VPN ports, whitelist only necessary traffic

2. **Direct IP access**
   - Directly connect to LLM provider's IP address (bypasses DNS)
   - **Mitigation:** YORI v0.2.0 will support IP-based rules

3. **Remove CA certificate**
   - Kid removes YORI CA from device trust store
   - **Mitigation:** Device management profiles (iOS) or admin access restrictions (Windows)

4. **Use different LLM**
   - Switch to provider not in YORI's endpoint list
   - **Mitigation:** Add endpoint to config, use "default deny" policy

5. **Physical access to router**
   - Kid reboots router into single-user mode, disables YORI
   - **Mitigation:** Physical security (lock router in closet)

**Bottom line:** Motivated teenagers can bypass most technical controls. YORI is a tool for awareness and education, not an impenetrable fortress.

---

## Troubleshooting

### YORI isn't intercepting any traffic. What's wrong?

**Common causes (in order of likelihood):**

1. **NAT rules not configured**
   - Check: Firewall → NAT → Port Forward
   - Should have redirect 443 → 8443 for LLM endpoints

2. **CA certificate not trusted on devices**
   - Test: Visit https://api.openai.com in browser
   - Should show YORI cert, not OpenAI's cert
   - If OpenAI's cert appears, CA not installed correctly

3. **YORI service not running**
   ```bash
   service yori status
   # If stopped: service yori start
   ```

4. **Firewall blocking YORI proxy**
   - Check: Firewall → Rules → LAN
   - Ensure port 8443 is allowed

**Debugging:**
```bash
# Watch traffic on proxy port
tcpdump -i lo0 -n tcp port 8443

# Generate test traffic from device
curl https://api.openai.com

# Should see packets on port 8443
```

---

### My family is complaining that websites are broken. Is it YORI?

**Unlikely, but check these:**

1. **Verify YORI is only intercepting LLM endpoints**
   ```bash
   # Check NAT rules
   pfctl -s nat | grep 8443

   # Should ONLY redirect LLM domains, not all HTTPS
   ```

2. **Check LLM_Endpoints alias**
   - Firewall → Aliases → LLM_Endpoints
   - Should contain ONLY LLM domains
   - If it has `*.` or broad wildcards, remove them

3. **Test with YORI disabled**
   ```bash
   service yori stop
   # If problem persists, not YORI's fault
   service yori start
   ```

**Most common cause:** Overly broad NAT rules that redirect all HTTPS traffic. YORI should only intercept specific LLM endpoints.

---

### How do I uninstall YORI completely?

```bash
# Stop service
service yori stop
service yori disable

# Remove package
pkg remove os-yori

# Remove configuration and data (optional)
rm -rf /usr/local/etc/yori
rm -rf /var/db/yori
rm -rf /var/log/yori

# Remove NAT rules (in web UI)
# Firewall → NAT → Port Forward → Delete YORI rule

# Remove CA certificate from devices
# (Varies by OS, reverse installation steps)
```

**Note:** Removing the package does NOT automatically remove:
- Configuration files
- Audit logs
- CA certificates on devices

You must manually clean these up for complete removal.

---

## Comparison with Alternatives

### How does YORI compare to SARK?

YORI is the lightweight home variant of [SARK](https://github.com/apathy-ca/sark) (enterprise LLM governance platform).

| Feature | YORI (Home) | SARK (Enterprise) |
|---------|-------------|-------------------|
| **Target** | Home networks (<50 users) | Enterprise (50K+ users) |
| **Deployment** | Single OPNsense router | Kubernetes cluster |
| **Database** | SQLite | PostgreSQL + TimescaleDB |
| **Cache** | In-memory (Rust) | Valkey/Redis cluster |
| **High Availability** | No | Yes (99.9% SLA) |
| **Authentication** | HTTP Basic | OIDC, LDAP, SAML |
| **Cost** | Free (open source) | Paid license |

**When to use YORI:**
- Home network with <20 devices
- Family parental controls
- DIY enthusiast
- Cost-conscious

**When to upgrade to SARK:**
- Business with >50 employees
- Need 99.9% uptime guarantee
- Compliance requirements (SOC 2, HIPAA)
- Enterprise support contract

---

## Future Development

### What features are planned for future versions?

**v0.2.0 (Q2 2026):**
- Policy bundles (download pre-made policies)
- Web-based policy editor (no-code)
- Encrypted SQLite database (SQLCipher)
- Multi-router policy sync

**v0.3.0 (Q3 2026):**
- Local LLM integration (Ollama preference)
- Cost tracking dashboard with budget alerts
- Advanced analytics (usage patterns, topic analysis)
- SIEM integration (export to Splunk, Datadog)
- pfSense port

**v1.0.0 (Q4 2026):**
- Stable API for integrations
- Plugin marketplace
- Mobile app (iOS/Android) for alerts
- Advanced content filtering

**Roadmap:** See [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed milestones.

---

### How can I request a feature or report a bug?

**Feature requests:**
- GitHub Discussions: https://github.com/apathy-ca/yori/discussions
- Tag with `enhancement` label
- Describe use case and benefit

**Bug reports:**
- GitHub Issues: https://github.com/apathy-ca/yori/issues
- Include YORI version, OPNsense version, steps to reproduce

**Security vulnerabilities:**
- **Do NOT open public issue**
- Use GitHub Security Advisories (private reporting)
- We'll respond within 48 hours

---

### Is YORI affiliated with OpenAI, Anthropic, or other LLM providers?

**No.** YORI is an independent open-source project with no affiliation to:
- OpenAI (ChatGPT)
- Anthropic (Claude)
- Google (Gemini)
- Mistral AI
- OPNsense (though we build on their platform)

**Legal:** YORI is provided as-is under MIT license. Using YORI may affect your ability to use certain LLM features (e.g., content filtering). Review provider Terms of Service before use.

---

## Getting More Help

**Documentation:**
- [Installation Guide](INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Configuration Reference](CONFIGURATION.md)
- [Policy Guide](POLICY_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

**Community:**
- GitHub Discussions (general questions)
- GitHub Issues (bugs and features)
- Discord Server (real-time chat) - link in README

**Professional Support:**
- Enterprise support available through SARK license
- Custom development on request (email: support@apathy.ca)

---

**FAQ version:** v0.1.0 (2026-01-19)

**Question count:** 20+ comprehensive Q&As covering installation, usage, privacy, and troubleshooting.
