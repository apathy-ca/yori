# YORI Troubleshooting Guide

Solutions to common problems and debugging techniques for YORI.

---

## Table of Contents

- [Service Issues](#service-issues)
- [Traffic Interception Problems](#traffic-interception-problems)
- [Certificate Issues](#certificate-issues)
- [Dashboard and UI Problems](#dashboard-and-ui-problems)
- [Policy and Alert Issues](#policy-and-alert-issues)
- [Performance Problems](#performance-problems)
- [Database Issues](#database-issues)
- [Network and Connectivity](#network-and-connectivity)
- [Diagnostic Commands](#diagnostic-commands)

---

## Service Issues

### Service Won't Start

**Symptoms:**
```bash
service yori start
# Returns immediately, service not running
```

**Diagnosis:**
```bash
# Check service status
service yori status

# Check logs for errors
tail -50 /var/log/yori/yori.log

# Try running manually
/usr/local/bin/yori --config /usr/local/etc/yori/yori.conf
```

**Common Causes:**

1. **Port 8443 already in use**
   ```bash
   sockstat -4 -l | grep 8443
   # If another process is using port 8443:
   # - Change YORI listen port in config, OR
   # - Stop conflicting service
   ```

2. **Invalid configuration file**
   ```bash
   yori --check-config
   # Look for YAML syntax errors
   ```

3. **Missing dependencies**
   ```bash
   pkg info os-yori
   # Verify package is installed

   python3.11 -c "import yori_core"
   # If ImportError: Rust core not built correctly
   ```

4. **Permission errors**
   ```bash
   ls -la /usr/local/etc/yori/yori.conf
   # Should be: -rw-r--r-- root:wheel

   ls -la /var/db/yori/
   # Should be: drwxr-xr-x yori:yori
   ```

**Solutions:**
```bash
# Fix permissions
chown root:wheel /usr/local/etc/yori/yori.conf
chmod 644 /usr/local/etc/yori/yori.conf
mkdir -p /var/db/yori
chown yori:yori /var/db/yori

# Recreate config from sample
cp /usr/local/share/examples/yori/yori.conf.sample \
   /usr/local/etc/yori/yori.conf

# Restart service
service yori restart
```

---

### Service Crashes Immediately After Start

**Symptoms:**
```bash
service yori start
# Service starts, then immediately stops
```

**Diagnosis:**
```bash
# Check crash logs
cat /var/log/yori/yori.log | grep -i "error\|crash\|panic"

# Check system logs
tail -f /var/log/messages | grep yori
```

**Common Causes:**

1. **Out of Memory (OOM)**
   ```bash
   top
   # Check available memory
   # YORI needs 100MB minimum
   ```

2. **Rust panic in core library**
   ```bash
   # Look for panic messages
   grep "thread.*panicked" /var/log/yori/yori.log
   ```

3. **Database corruption**
   ```bash
   sqlite3 /var/db/yori/audit.db "PRAGMA integrity_check;"
   # If not "ok", database is corrupted
   ```

**Solutions:**
```bash
# Free up memory
service unnecessary_service stop

# Rebuild database
mv /var/db/yori/audit.db /var/db/yori/audit.db.backup
service yori start  # Will create new empty database

# Report bug if Rust panic
# Include full panic message from logs
```

---

## Traffic Interception Problems

### No Traffic Being Intercepted

**Symptoms:**
- Dashboard shows 0 requests
- Audit log is empty
- Devices can use LLMs normally

**Diagnosis:**
```bash
# Check if YORI is receiving connections
tcpdump -i lo0 -n tcp port 8443

# From a device, try:
curl -v https://api.openai.com

# Should see connection attempt on port 8443
```

**Common Causes:**

1. **NAT rules not configured**
   ```bash
   # Check NAT rules
   pfctl -s nat | grep 8443
   # Should show redirect from 443 to 8443
   ```

   **Solution:** Configure NAT rules (see [Installation Guide](INSTALLATION.md#configure-transparent-proxy))

2. **LLM_Endpoints alias incorrect**
   - Navigate to Firewall → Aliases → LLM_Endpoints
   - Verify it contains:
     ```
     api.openai.com
     api.anthropic.com
     gemini.google.com
     api.mistral.ai
     ```
   - NO wildcards, NO http:// prefixes

3. **CA certificate not installed on devices**
   ```bash
   # From device, check certificate:
   openssl s_client -connect api.openai.com:443 -showcerts
   # Should show YORI CA in chain, not OpenAI's cert
   ```

4. **Firewall blocking proxy port**
   - Check Firewall → Rules → LAN
   - Ensure port 8443 is allowed from LAN net

**Quick Test:**
```bash
# Temporarily bypass firewall to test
# (DO NOT leave this way)
pfctl -d  # Disable firewall
# Test if YORI intercepts now
pfctl -e  # Re-enable firewall
```

---

### Some Requests Intercepted, Others Not

**Symptoms:**
- Dashboard shows some activity but missing requests you know happened
- Intermittent interception

**Possible Causes:**

1. **Different LLM endpoint used**
   - Some apps use regional endpoints (e.g., `api.openai-azure.com`)
   - **Solution:** Add endpoint to config

2. **DNS caching on devices**
   - Device cached old DNS resolution before NAT rule added
   - **Solution:** Clear DNS cache on device or reboot device

3. **VPN or proxy on device**
   - Device tunneling traffic outside your network
   - **Solution:** Disable VPN/proxy or add YORI CA to VPN config

4. **IPv6 traffic bypassing IPv4 NAT**
   - NAT rules only apply to IPv4
   - **Solution:** Disable IPv6 on LAN or add IPv6 NAT rules

---

## Certificate Issues

### Devices Show "Certificate Not Trusted" Errors

**Symptoms:**
- Browser shows SSL/TLS warning when accessing LLM sites
- Apps refuse to connect to LLM APIs
- Error: "NET::ERR_CERT_AUTHORITY_INVALID"

**Diagnosis:**
```bash
# From device, check what certificate is presented:
openssl s_client -connect api.openai.com:443 -showcerts | grep "subject\|issuer"

# Should show:
# issuer=CN = YORI Home LLM Gateway
# subject=CN = api.openai.com

# If shows OpenAI's certificate, YORI isn't intercepting
# If shows YORI certificate, CA not trusted on device
```

**Solutions by Platform:**

**macOS:**
```bash
# Verify CA is in system keychain
security find-certificate -c "YORI Home LLM Gateway"

# If not found, reinstall:
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain yori-ca.crt

# Verify trust settings
# Open Keychain Access → System → YORI cert → Trust → Always Trust
```

**Windows:**
```powershell
# Check if installed
certutil -store Root | findstr "YORI"

# Reinstall if missing
certutil -addstore "Root" yori-ca.crt
```

**iOS:**
- Settings → General → VPN & Device Management → YORI profile
- Verify profile is installed
- Settings → General → About → Certificate Trust Settings
- Verify "Enable Full Trust" is ON (this is often missed!)

**Android:**
- Settings → Security → Trusted Credentials → User tab
- Should show "YORI CA"
- If not, reinstall from Settings → Security → Install from storage

---

### Certificate Errors After YORI Update

**Symptoms:**
- Certificates worked before, stopped after YORI update
- Error: "Certificate expired" or "Certificate invalid"

**Cause:** CA certificate regenerated during update, old cert on devices is no longer valid.

**Solution:**
```bash
# On OPNsense:
# Services → YORI → Certificate Management → Download CA Certificate

# Distribute new yori-ca.crt to all devices
# Overwrite old certificate (same installation process)
```

**Prevention:**
- Don't regenerate CA unless necessary
- If regenerating, communicate to family to reinstall
- Consider 10-year certificate validity to avoid frequent updates

---

## Dashboard and UI Problems

### Dashboard Shows "No Data Available"

**Symptoms:**
- Charts are empty
- Statistics cards show 0
- "Last updated: Never"

**Diagnosis:**
```bash
# Check if any requests logged
sqlite3 /var/db/yori/audit.db "SELECT COUNT(*) FROM audit_events;"
# If 0: No traffic has been intercepted
# If >0: Dashboard query issue
```

**Solutions:**

1. **No traffic intercepted yet**
   - Wait for first LLM request
   - Generate test request: `curl https://api.openai.com`
   - Refresh dashboard after 1-2 minutes

2. **Dashboard cache stale**
   - Hard refresh browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   - Clear browser cache
   - Try incognito/private window

3. **Database permission issue**
   ```bash
   ls -la /var/db/yori/audit.db
   # Should be readable by www user (for PHP dashboard)
   chmod 644 /var/db/yori/audit.db
   ```

---

### Dashboard Loads But Charts Don't Render

**Symptoms:**
- Page loads, but charts show blank spaces
- JavaScript errors in browser console

**Diagnosis:**
```
# Open browser developer tools (F12)
# Check Console tab for errors
# Common errors:
# - "Chart.js is not defined"
# - "Failed to load resource: /ui/yori/js/charts.js"
```

**Solutions:**

1. **JavaScript library not loading**
   - Check internet connectivity (Chart.js loaded from CDN)
   - Or install local copy

2. **Browser compatibility**
   - Update to latest browser version
   - Try different browser (Chrome, Firefox, Safari)

3. **Ad blocker interfering**
   - Disable ad blocker for OPNsense UI
   - Whitelist router IP address

---

## Policy and Alert Issues

### Policy Not Triggering

**Symptoms:**
- Policy shows "Active" but no alerts generated
- Manually tested policy works

**Diagnosis:**
```bash
# Check policy is loaded
yori policy list
# Should show your policy file

# Enable debug logging
yori --log-level debug

# Watch policy evaluation
tail -f /var/log/yori/policy.log

# Make test request, check if policy evaluated
```

**Common Causes:**

1. **Policy conditions too strict**
   ```rego
   # Example: Never matches because hour is always < 25
   alert {
       input.context.hour > 25  # BUG: Should be 22
   }
   ```

2. **Device hostname mismatch**
   ```rego
   kids_device {
       input.device.hostname == "sarahs-iphone"
   }
   # But actual hostname is "Sarah's iPhone" (apostrophe!)
   ```

   **Solution:** Check actual hostnames in audit logs, use exact match

3. **Case sensitivity issues**
   ```rego
   # Won't match if prompt is "HOMEWORK"
   contains(prompt, "homework")

   # Fix: Use lower()
   contains(lower(prompt), "homework")
   ```

4. **Policy not in correct directory**
   ```bash
   ls -la /usr/local/etc/yori/policies/
   # Verify your .rego file is present
   ```

---

### Alerts Not Sending (Email/Push)

**Symptoms:**
- Policy triggers (visible in logs)
- Alert appears in web UI
- But no email or push notification received

**Diagnosis:**
```bash
# Test email configuration
yori alerts test email

# Check alert logs
tail -f /var/log/yori/alerts.log

# Look for SMTP errors or connection failures
```

**Email Issues:**

1. **SMTP credentials invalid**
   - Re-enter password in Settings → Alerts → Email
   - For Gmail: Use app-specific password, not account password

2. **SMTP server blocking**
   ```bash
   # Test connectivity
   telnet smtp.gmail.com 587
   # Should connect, then type "QUIT"
   ```

3. **Firewall blocking outbound SMTP**
   - Check Firewall → Rules → WAN
   - Ensure port 587 (or 465) allowed outbound

**Push (Pushover) Issues:**

1. **Invalid API token**
   - Regenerate token at pushover.net/apps
   - Re-enter in YORI settings

2. **User key incorrect**
   - Check pushover.net for your user key
   - Copy-paste carefully (no spaces)

---

## Performance Problems

### High CPU Usage

**Symptoms:**
```bash
top
# yori process using >50% CPU constantly
```

**Diagnosis:**
```bash
# Check number of policies loaded
yori policy list | wc -l

# Check policy complexity
# Each policy evaluated for every request
```

**Solutions:**

1. **Too many policies**
   - Disable unused policies
   - Combine similar policies into one file

2. **Inefficient policy logic**
   ```rego
   # BAD: Regex on every request
   alert {
       regex.match("complex.*regex.*pattern", prompt)
   }

   # BETTER: Simple string check first
   alert {
       contains(prompt, "keyword")
       regex.match("only if needed", prompt)
   }
   ```

3. **High request volume**
   - Normal if you're processing 100+ req/sec
   - Consider hardware upgrade or SARK for enterprise use

---

### Slow Dashboard Loading

**Symptoms:**
- Dashboard takes >10 seconds to load
- Browser shows "Loading..." for extended time

**Cause:** Large audit database (millions of rows)

**Solutions:**
```bash
# Check database size
ls -lh /var/db/yori/audit.db

# Count rows
sqlite3 /var/db/yori/audit.db "SELECT COUNT(*) FROM audit_events;"

# If >1 million rows:
# 1. Reduce retention
# 2. Vacuum database
sqlite3 /var/db/yori/audit.db "VACUUM;"

# 3. Add indexes (should already exist)
sqlite3 /var/db/yori/audit.db "
CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_device ON audit_events(device_ip);
"
```

---

## Database Issues

### Database Locked Errors

**Symptoms:**
```
Error: database is locked
```

**Cause:** SQLite doesn't handle concurrent writes well.

**Solutions:**
```bash
# Check for stuck processes
fuser /var/db/yori/audit.db
# Kill any processes holding lock

# If persistent, restart YORI
service yori restart

# Prevent: Enable WAL mode (Write-Ahead Logging)
sqlite3 /var/db/yori/audit.db "PRAGMA journal_mode=WAL;"
```

---

### Database Corruption

**Symptoms:**
```bash
sqlite3 /var/db/yori/audit.db "PRAGMA integrity_check;"
# Returns errors instead of "ok"
```

**Recovery:**
```bash
# Try to recover
sqlite3 /var/db/yori/audit.db ".recover" | sqlite3 audit_recovered.db

# If recovery fails, restore from backup
cp /var/db/yori/audit.db.backup /var/db/yori/audit.db

# If no backup, start fresh (data loss)
mv /var/db/yori/audit.db /var/db/yori/audit.db.corrupted
service yori restart  # Creates new empty database
```

**Prevention:**
```bash
# Set up daily backups
echo "0 2 * * * cp /var/db/yori/audit.db /var/db/yori/audit.db.backup" | crontab -
```

---

## Network and Connectivity

### LLM Requests Timing Out

**Symptoms:**
- Requests to ChatGPT/Claude take forever
- Eventually timeout with 504 Gateway Timeout

**Diagnosis:**
```bash
# Test direct connectivity (bypass YORI)
curl -I https://api.openai.com

# If works, YORI issue
# If fails, network/firewall issue
```

**Solutions:**

1. **YORI proxy timeout too short**
   ```yaml
   # In yori.conf (future v0.2.0)
   proxy:
     timeout_seconds: 60  # Increase from default 30
   ```

2. **Upstream DNS slow**
   - YORI needs to resolve LLM provider domains
   - Test: `dig api.openai.com`
   - Solution: Configure faster DNS (1.1.1.1, 8.8.8.8)

3. **NAT connection tracking full**
   ```bash
   sysctl net.inet.ip.fw.dyn_count
   sysctl net.inet.ip.fw.dyn_max
   # If count near max, increase max
   sysctl net.inet.ip.fw.dyn_max=10000
   ```

---

## Diagnostic Commands

### Comprehensive Health Check

```bash
#!/bin/sh
# YORI Health Check Script

echo "=== Service Status ==="
service yori status

echo -e "\n=== Configuration Validity ==="
yori --check-config

echo -e "\n=== Listening Ports ==="
sockstat -4 -l | grep 8443

echo -e "\n=== NAT Rules ==="
pfctl -s nat | grep 8443

echo -e "\n=== Database Status ==="
sqlite3 /var/db/yori/audit.db "SELECT COUNT(*) as total_events FROM audit_events;"
sqlite3 /var/db/yori/audit.db "PRAGMA integrity_check;"

echo -e "\n=== Loaded Policies ==="
yori policy list

echo -e "\n=== Recent Logs ==="
tail -20 /var/log/yori/yori.log

echo -e "\n=== Disk Space ==="
df -h /var/db/yori

echo -e "\n=== Memory Usage ==="
ps aux | grep yori | grep -v grep
```

Save as `/root/yori-healthcheck.sh`, run when troubleshooting.

---

### Packet Capture for Debugging

```bash
# Capture traffic to/from YORI proxy
tcpdump -i lo0 -nn -s0 -w /tmp/yori-capture.pcap port 8443

# Let it run while reproducing issue
# Stop with Ctrl+C

# Analyze capture
tcpdump -r /tmp/yori-capture.pcap -A | less

# Look for:
# - Connection attempts
# - TLS handshakes
# - HTTP requests/responses
# - Connection resets or timeouts
```

---

### Debug Logging

```bash
# Enable maximum verbosity
export YORI_LOG_LEVEL=DEBUG
export RUST_LOG=debug
service yori restart

# Watch all logs
tail -f /var/log/yori/yori.log

# Disable after debugging
unset YORI_LOG_LEVEL RUST_LOG
service yori restart
```

---

## Getting Help

If you've tried these solutions and still have issues:

1. **Gather diagnostic information:**
   ```bash
   # Run health check script
   /root/yori-healthcheck.sh > yori-diagnostics.txt

   # Collect logs
   tar -czf yori-logs.tar.gz /var/log/yori/
   ```

2. **Search existing issues:**
   - https://github.com/apathy-ca/yori/issues

3. **Open new issue:**
   - Include YORI version: `yori --version`
   - Include OPNsense version: `opnsense-version`
   - Attach `yori-diagnostics.txt`
   - Describe expected vs actual behavior
   - Include steps to reproduce

4. **Ask in community:**
   - GitHub Discussions: https://github.com/apathy-ca/yori/discussions
   - Discord: Link in README

---

## See Also

- [User Guide](USER_GUIDE.md) - Normal operation
- [FAQ](FAQ.md) - Common questions
- [Installation Guide](INSTALLATION.md) - Setup instructions
- [Configuration Reference](CONFIGURATION.md) - Config options

---

**Troubleshooting guide version:** v0.1.0 (2026-01-19)
