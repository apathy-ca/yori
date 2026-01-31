# YORI v0.2.0 OPNsense Deployment Test Plan

**Objective:** Demonstrate actual utility by deploying YORI on OPNsense and intercepting real LLM traffic
**Platform:** OPNsense 24.1+ on FreeBSD 13.2+
**Estimated Time:** 4-6 hours (first time), 2-3 hours (subsequent)
**Difficulty:** Advanced

---

## Prerequisites

### Required Hardware/VMs

**Option A: Physical Hardware**
- OPNsense router (or PC with 2 NICs)
- Test client device (laptop/desktop)
- Network switch (if needed)

**Option B: Virtual Lab (Recommended for Testing)**
- Hypervisor: VirtualBox, VMware, Proxmox, or KVM
- OPNsense VM: 2GB RAM, 20GB disk, 2 NICs
- Client VM: Any OS with curl/browser
- Virtual network for isolated testing

### Required Software

- OPNsense 24.1+ ISO (download from opnsense.org)
- YORI package files (built from this repo)
- SSH client for OPNsense access
- Web browser for OPNsense UI

### Required Knowledge

- Basic OPNsense administration
- SSH/command line comfort
- Network configuration basics
- TLS/SSL certificate concepts

---

## Test Environment Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────┐
│  OPNsense Router (FreeBSD)          │
│  ┌───────────────────────────────┐  │
│  │  WAN: 192.168.1.x (dhcp)     │  │
│  │  LAN: 10.0.0.1/24            │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  YORI Service                 │  │
│  │  Listen: 10.0.0.1:8443       │  │
│  │  Database: /var/db/yori/     │  │
│  │  Policies: /usr/local/etc/   │  │
│  └───────────────────────────────┘  │
│                                     │
│  Firewall Rule:                     │
│  api.openai.com:443 → 10.0.0.1:8443│
└─────────────────────────────────────┘
    │ LAN Network: 10.0.0.0/24
    ▼
┌─────────────────────────────────────┐
│  Test Client                        │
│  IP: 10.0.0.100                    │
│  Gateway: 10.0.0.1                 │
│  DNS: 10.0.0.1                     │
│                                     │
│  curl -X POST https://api.openai.com/v1/chat/completions
│        ↓
│  Request intercepted by YORI
│        ↓
│  Policy evaluated → Block or Allow
└─────────────────────────────────────┘
```

---

## Phase 1: OPNsense Installation & Setup

**Duration:** 30-60 minutes

### Step 1.1: Install OPNsense

**If using VM:**
```bash
# Create VM with:
# - 2GB RAM minimum
# - 20GB disk
# - 2 Network adapters:
#   - NIC1: NAT or Bridged (WAN)
#   - NIC2: Host-only or Internal (LAN)
```

**Installation:**
1. Boot from OPNsense ISO
2. Select "Install (ZFS)"
3. Configure disk
4. Set root password (remember this!)
5. Complete installation
6. Reboot and remove ISO

**✅ Verification:**
```
OPNsense login prompt appears
Can login as root with password
```

### Step 1.2: Initial OPNsense Configuration

**Console setup (option 1):**
```
Configure interfaces:
  WAN: em0 (or your first NIC)
  LAN: em1 (or your second NIC)

Set LAN IP:
  IP: 10.0.0.1
  Subnet: 24
  DHCP: Yes (range 10.0.0.100-10.0.0.200)
```

**✅ Verification:**
```bash
# From console
ping -c 3 8.8.8.8          # Internet works
ping -c 3 10.0.0.1         # LAN works
```

### Step 1.3: Access Web UI

**From test client:**
```
1. Connect client to LAN network
2. Get DHCP address (should be 10.0.0.100+)
3. Browse to https://10.0.0.1
4. Login: root / [your password]
5. Skip wizard or configure basic settings
```

**✅ Verification:**
```
Can access web UI
Can see dashboard
System → Firmware shows current version
```

### Step 1.4: Enable SSH Access

**Web UI:**
```
System → Settings → Administration
✓ Enable Secure Shell
✓ Permit root user login
✓ Permit password login
Save
```

**Test SSH:**
```bash
ssh root@10.0.0.1
# Should connect without errors
```

**✅ Verification:**
```bash
# Once connected via SSH
uname -a                   # Shows FreeBSD 13.2+
freebsd-version            # Shows version
df -h                      # Shows disk usage
```

---

## Phase 2: YORI Package Installation

**Duration:** 30-60 minutes

### Step 2.1: Build YORI Package (On Linux Dev Machine)

**Prerequisites:**
```bash
cd ~/Source/yori

# Ensure latest code
git pull
pip install -e .

# Install build dependencies
pip install build wheel
```

**Build Python wheel:**
```bash
# Build wheel for Python
python -m build --wheel

# Build Rust extension for FreeBSD
maturin build --release --target x86_64-unknown-freebsd

# Package should be in:
ls -lh target/wheels/yori-*.whl
```

**✅ Verification:**
```bash
# You should have:
# target/wheels/yori-0.2.0-cp39-abi3-manylinux_2_34_x86_64.whl
# OR
# target/wheels/yori-0.2.0-cp39-abi3-freebsd_13_x86_64.whl
```

### Step 2.2: Transfer Package to OPNsense

```bash
# From your dev machine
scp target/wheels/yori-*.whl root@10.0.0.1:/tmp/

# Also copy config and policies
scp -r policies/*.rego root@10.0.0.1:/tmp/
scp examples/yori.conf.example root@10.0.0.1:/tmp/yori.conf
```

**✅ Verification:**
```bash
# SSH to OPNsense
ssh root@10.0.0.1
ls -lh /tmp/yori*.whl
ls -lh /tmp/*.rego
ls -lh /tmp/yori.conf
```

### Step 2.3: Install Dependencies on OPNsense

**SSH to OPNsense:**
```bash
ssh root@10.0.0.1

# Install Python and dependencies
pkg install python311 py311-sqlite3

# Bootstrap pip if needed
python3.11 -m ensurepip

# Create virtual environment
python3.11 -m venv /usr/local/yori-venv

# Install YORI in venv (do NOT activate - use venv python directly)
/usr/local/yori-venv/bin/pip install --upgrade pip
/usr/local/yori-venv/bin/pip install /tmp/yori-*.whl

# Verify installation
/usr/local/yori-venv/bin/python -c "import yori; print('YORI installed:', yori.__version__)"
```

**✅ Verification:**
```bash
# Should see:
# YORI installed: 0.2.0

# Test imports
python -c "from yori.config import YoriConfig; print('✓')"
python -c "from yori.enforcement import EnforcementEngine; print('✓')"
python -c "import yori._core; print('✓')"
```

### Step 2.4: Create YORI Directories

```bash
# Still SSH'd to OPNsense
mkdir -p /usr/local/etc/yori/policies
mkdir -p /var/db/yori
mkdir -p /var/log/yori

# Copy config
cp /tmp/yori.conf /usr/local/etc/yori/

# Copy policies
cp /tmp/*.rego /usr/local/etc/yori/policies/

# Set permissions
chmod 755 /usr/local/etc/yori
chmod 644 /usr/local/etc/yori/yori.conf
chmod 755 /var/db/yori
chmod 755 /var/log/yori
```

**✅ Verification:**
```bash
ls -la /usr/local/etc/yori/
ls -la /usr/local/etc/yori/policies/
ls -la /var/db/yori/
```

---

## Phase 3: YORI Service Configuration

**Duration:** 30 minutes

### Step 3.1: Create Test Configuration

**Edit config:**
```bash
# SSH to OPNsense
vi /usr/local/etc/yori/yori.conf
```

**Basic config for testing:**
```yaml
# YORI Configuration - Test Mode
mode: observe

listen: 0.0.0.0:8443

endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true

audit:
  database: /var/db/yori/audit.db
  retention_days: 365

policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego

enforcement:
  enabled: false
  consent_accepted: false
```

**✅ Verification:**
```bash
cat /usr/local/etc/yori/yori.conf
# Verify YAML is valid
```

### Step 3.2: Create rc.d Service Script

**Create service script:**
```bash
# SSH to OPNsense
vi /usr/local/etc/rc.d/yori
```

**Service script content:**
```bash
#!/bin/sh
#
# PROVIDE: yori
# REQUIRE: LOGIN NETWORKING
# KEYWORD: shutdown
#
# Add these lines to /etc/rc.conf to enable yori:
# yori_enable="YES"

. /etc/rc.subr

name=yori
rcvar=yori_enable

load_rc_config $name

: ${yori_enable:="NO"}
: ${yori_config:="/usr/local/etc/yori/yori.conf"}
: ${yori_pidfile:="/var/run/yori.pid"}
: ${yori_log:="/var/log/yori/yori.log"}

command="/usr/local/yori-venv/bin/python"
command_args="-m yori.main --config ${yori_config} >> ${yori_log} 2>&1 &"
pidfile="${yori_pidfile}"

start_cmd="${name}_start"
stop_cmd="${name}_stop"
status_cmd="${name}_status"

yori_start()
{
    echo "Starting ${name}."
    /usr/sbin/daemon -p ${pidfile} ${command} ${command_args}
}

yori_stop()
{
    if [ -f ${pidfile} ]; then
        echo "Stopping ${name}."
        kill -TERM $(cat ${pidfile})
        rm -f ${pidfile}
    else
        echo "${name} is not running."
    fi
}

yori_status()
{
    if [ -f ${pidfile} ]; then
        echo "${name} is running as pid $(cat ${pidfile})."
    else
        echo "${name} is not running."
    fi
}

run_rc_command "$1"
```

**Make executable:**
```bash
chmod +x /usr/local/etc/rc.d/yori
```

**Enable service:**
```bash
# Add to rc.conf
echo 'yori_enable="YES"' >> /etc/rc.conf
```

**✅ Verification:**
```bash
# Check service script syntax
/usr/local/etc/rc.d/yori status
# Should say "yori is not running" (not an error)
```

### Step 3.3: Create YORI Main Entry Point

**Create main.py if not exists:**
```bash
# Check if main.py exists in package
source /usr/local/yori-venv/bin/activate
python -c "import yori.main" 2>&1

# If it doesn't exist, you'll need to create a simple proxy server
# For now, we'll create a test script
```

**Create test server script:**
```bash
vi /usr/local/etc/yori/run_proxy.py
```

**Content:**
```python
#!/usr/local/yori-venv/bin/python
"""
YORI Test Proxy Server
Minimal implementation for testing interception
"""

import sys
import logging
from pathlib import Path

# Add YORI to path
sys.path.insert(0, '/usr/local/yori-venv/lib/python3.11/site-packages')

from yori.config import YoriConfig
from yori.enforcement import EnforcementEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/yori/proxy.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('yori.proxy')

def main():
    """Simple proxy to test YORI integration"""
    logger.info("Starting YORI proxy server...")

    # Load configuration
    config_path = Path("/usr/local/etc/yori/yori.conf")
    if config_path.exists():
        config = YoriConfig.from_yaml(config_path)
        logger.info(f"Loaded config: mode={config.mode}")
    else:
        logger.warning("Config not found, using defaults")
        config = YoriConfig()

    # Initialize enforcement engine
    engine = EnforcementEngine(config)
    logger.info(f"Enforcement enabled: {engine._is_enforcement_enabled()}")

    # TODO: Implement actual HTTP proxy
    # For now, just log that we started
    logger.info(f"YORI would listen on {config.listen}")
    logger.info("Press Ctrl+C to stop")

    # Keep running
    try:
        import time
        while True:
            time.sleep(60)
            logger.info("YORI proxy still running...")
    except KeyboardInterrupt:
        logger.info("Shutting down YORI proxy")

if __name__ == '__main__':
    main()
```

**Make executable:**
```bash
chmod +x /usr/local/etc/yori/run_proxy.py
```

**✅ Verification:**
```bash
# Test it runs
/usr/local/etc/yori/run_proxy.py &
sleep 5
pkill -f run_proxy.py

# Check log
tail /var/log/yori/proxy.log
# Should see startup messages
```

---

## Phase 4: Network Configuration for Interception

**Duration:** 30-60 minutes

### Step 4.1: Create TLS Certificate

**Option A: Self-Signed Certificate (Quick Test)**
```bash
# SSH to OPNsense
cd /usr/local/etc/yori

# Generate CA certificate
openssl req -new -x509 -days 365 -nodes \
  -out yori-ca.crt \
  -keyout yori-ca.key \
  -subj "/C=US/ST=State/L=City/O=YORI/CN=YORI-CA"

# Generate server certificate
openssl req -new -nodes \
  -out yori.csr \
  -keyout yori.key \
  -subj "/C=US/ST=State/L=City/O=YORI/CN=api.openai.com"

# Sign with CA
openssl x509 -req -days 365 \
  -in yori.csr \
  -CA yori-ca.crt \
  -CAkey yori-ca.key \
  -CAcreateserial \
  -out yori.crt

# Set permissions
chmod 600 yori*.key
chmod 644 yori*.crt
```

**Option B: Use OPNsense Built-in CA (Better)**
```
Web UI → System → Trust → Authorities
- Create new CA
- Export CA certificate

System → Trust → Certificates
- Create new certificate for api.openai.com
- Export certificate and key
```

**✅ Verification:**
```bash
ls -l /usr/local/etc/yori/*.crt
ls -l /usr/local/etc/yori/*.key
openssl x509 -in /usr/local/etc/yori/yori.crt -noout -text
```

### Step 4.2: Configure DNS Override

**Web UI:**
```
Services → Unbound DNS → Overrides → Host Overrides

Add Override:
  Host: api
  Domain: openai.com
  IP: 10.0.0.1 (OPNsense LAN IP)
  Description: YORI interception

Add Override:
  Host: api
  Domain: anthropic.com
  IP: 10.0.0.1
  Description: YORI interception

Save and Apply
```

**✅ Verification from client:**
```bash
# From test client (10.0.0.100)
nslookup api.openai.com
# Should return 10.0.0.1

dig api.openai.com +short
# Should return 10.0.0.1
```

### Step 4.3: Configure Port Forwarding (Alternative to DNS)

**If not using DNS override, use firewall NAT:**

```
Firewall → NAT → Port Forward

Add rule:
  Interface: LAN
  Protocol: TCP
  Destination: any
  Destination port: 443
  Redirect target IP: 10.0.0.1
  Redirect target port: 8443
  Description: YORI LLM interception
  Filter rule association: Add associated filter rule

Save and Apply
```

**⚠️ Note:** This will redirect ALL port 443 traffic. DNS override is more selective.

---

## Phase 5: Start YORI Service

**Duration:** 15 minutes

### Step 5.1: Start Service

```bash
# SSH to OPNsense
service yori start

# Check status
service yori status

# Check if listening
sockstat -l | grep 8443

# Check logs
tail -f /var/log/yori/yori.log
```

**✅ Verification:**
```bash
# Should see:
# - Service running
# - Process listening on port 8443
# - Log shows "Starting YORI proxy server"

ps aux | grep yori
# Should show python process running
```

### Step 5.2: Test Local Connection

```bash
# From OPNsense console
curl -k https://10.0.0.1:8443/health
# Should return something (even if 404, means service responds)

telnet 10.0.0.1 8443
# Should connect
# Ctrl+C to exit
```

**✅ Verification:**
```
Connection to port 8443 succeeds
```

---

## Phase 6: Client Configuration

**Duration:** 15 minutes

### Step 6.1: Configure Test Client

**Network settings:**
```
IP: 10.0.0.100 (or DHCP from OPNsense)
Subnet: 255.255.255.0
Gateway: 10.0.0.1
DNS: 10.0.0.1
```

**✅ Verification:**
```bash
# From client
ping 10.0.0.1          # OPNsense LAN
ping 8.8.8.8           # Internet
nslookup google.com    # DNS works
```

### Step 6.2: Install CA Certificate on Client

**Download CA cert:**
```bash
# From client
scp root@10.0.0.1:/usr/local/etc/yori/yori-ca.crt .
```

**Install certificate:**

**On Linux:**
```bash
sudo cp yori-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

**On macOS:**
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain yori-ca.crt
```

**On Windows:**
```
Double-click yori-ca.crt
Install Certificate → Local Machine → Place in "Trusted Root"
```

**✅ Verification:**
```bash
# Certificate should be trusted system-wide
openssl s_client -connect api.openai.com:443 -CAfile yori-ca.crt
# Should show "Verify return code: 0 (ok)"
```

---

## Phase 7: Live Traffic Testing

**Duration:** 60-90 minutes

### Test 7.1: Basic HTTP Interception

**From client:**
```bash
# Test DNS resolution
nslookup api.openai.com
# Should return 10.0.0.1

# Test connection to port 443
telnet api.openai.com 443
# Should connect to 10.0.0.1:8443 (via DNS override)
```

**✅ Verification:**
```bash
# On OPNsense, check logs
tail -f /var/log/yori/yori.log
# Should see connection attempt when you telnet
```

### Test 7.2: Curl Test - Simple Request

**From client:**
```bash
# Test with curl (ignoring cert for now)
curl -k https://api.openai.com/

# Should either:
# - Connect to YORI proxy (shows in logs)
# - Or return error (but YORI should log it)
```

**Check YORI logs:**
```bash
# SSH to OPNsense
tail -20 /var/log/yori/yori.log

# Check audit database
sqlite3 /var/db/yori/audit.db "SELECT * FROM audit_events LIMIT 5;"
```

**✅ Expected:**
```
YORI logs show incoming connection
Audit database has entry (if proxy implemented)
```

### Test 7.3: OpenAI API Test Request

**Create test script on client:**
```bash
cat > test_openai.sh << 'EOF'
#!/bin/bash

# Real OpenAI API test (requires API key)
# Replace with your actual API key

API_KEY="sk-your-key-here"

curl -k https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ],
    "max_tokens": 10
  }'
EOF

chmod +x test_openai.sh
./test_openai.sh
```

**✅ Expected behavior:**

**If proxy is implemented:**
- Request intercepted by YORI
- Logged to audit database
- Forwarded to real OpenAI (or blocked if enforcement enabled)

**If proxy is NOT implemented (current state):**
- DNS resolves to 10.0.0.1
- Connection attempts to reach YORI
- YORI sees connection but can't handle it yet
- Request fails (expected)

### Test 7.4: Monitor Traffic with tcpdump

**On OPNsense:**
```bash
# Watch traffic on LAN interface
tcpdump -i em1 -n port 8443

# Or watch for openai.com specifically
tcpdump -i em1 -n host api.openai.com
```

**From client, make request:**
```bash
curl -k https://api.openai.com/
```

**✅ Expected:**
```
tcpdump shows:
- DNS query for api.openai.com
- DNS response: 10.0.0.1
- TCP connection to 10.0.0.1:443 (redirected to 8443)
```

---

## Phase 8: Enforcement Testing

**Duration:** 60 minutes

### Test 8.1: Enable Observe Mode

**Edit config on OPNsense:**
```bash
vi /usr/local/etc/yori/yori.conf
```

**Set to observe mode:**
```yaml
mode: observe

enforcement:
  enabled: false
  consent_accepted: false
```

**Restart service:**
```bash
service yori restart
tail -f /var/log/yori/yori.log
```

**✅ Expected:**
```
Log shows: "mode=observe"
No blocking should occur
All requests logged only
```

### Test 8.2: Test Allowlist

**Add client to allowlist:**
```bash
vi /usr/local/etc/yori/yori.conf
```

```yaml
enforcement:
  enabled: false
  allowlist:
    devices:
      - ip: "10.0.0.100"
        name: "test-client"
        enabled: true
        permanent: false
```

**Restart and test:**
```bash
service yori restart

# From client
curl -k https://api.openai.com/
```

**Check logs:**
```bash
# Should see allowlist check
grep -i allowlist /var/log/yori/yori.log
```

**✅ Expected:**
```
Client recognized as allowlisted
Request would bypass enforcement (if enabled)
```

### Test 8.3: Test Time Exceptions

**Add homework hours exception:**
```yaml
enforcement:
  allowlist:
    time_exceptions:
      - name: "homework_hours"
        days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
        start_time: "15:00"
        end_time: "18:00"
        device_ips: ["10.0.0.100"]
        enabled: true
```

**Test during and outside hours:**
```bash
# Set system time if needed
date

# Make request
curl -k https://api.openai.com/
```

**Check logs:**
```bash
grep -i "time exception\|homework" /var/log/yori/yori.log
```

**✅ Expected:**
```
If during homework hours: exception applies
If outside hours: no exception
```

### Test 8.4: Enable Enforcement Mode (With Consent)

**⚠️ WARNING: This will actually block requests**

**Edit config:**
```yaml
mode: enforce

enforcement:
  enabled: true
  consent_accepted: true  # Required!

  allowlist:
    devices:
      # Remove test client from allowlist to test blocking
      []
```

**Add blocking policy:**
```bash
vi /usr/local/etc/yori/policies/test_block.rego
```

```rego
package yori.test

# Block all requests (for testing)
default allow = false

allow {
    false  # Never allow
}
```

**Update config to use policy:**
```yaml
policies:
  directory: /usr/local/etc/yori/policies
  files:
    test_block:
      enabled: true
      action: block
```

**Restart service:**
```bash
service yori restart
```

**Test from client:**
```bash
curl -k https://api.openai.com/
# Should be blocked (if proxy implemented)
```

**✅ Expected:**
```
Request blocked
Block page returned (HTML)
Block event logged to database
```

### Test 8.5: Test Emergency Override

**Activate emergency override:**
```bash
# On OPNsense
# TODO: Create CLI tool or web UI button
# For now, edit config:

vi /usr/local/etc/yori/yori.conf
```

```yaml
enforcement:
  enabled: true
  consent_accepted: true
  emergency_override:
    enabled: true
    activated_by: "admin"
    require_password: false
```

**Restart and test:**
```bash
service yori restart

# From client - should now work despite block policy
curl -k https://api.openai.com/
```

**✅ Expected:**
```
Emergency override bypasses all enforcement
Requests allowed
Override logged to audit
```

---

## Phase 9: Audit & Reporting

**Duration:** 30 minutes

### Test 9.1: Check Audit Database

```bash
# SSH to OPNsense
sqlite3 /var/db/yori/audit.db

# Show schema
.schema

# Count events
SELECT COUNT(*) FROM audit_events;

# Recent events
SELECT
  timestamp,
  event_type,
  client_ip,
  policy_name,
  action
FROM audit_events
ORDER BY timestamp DESC
LIMIT 10;

# Blocked requests
SELECT
  timestamp,
  client_ip,
  policy_name,
  reason
FROM audit_events
WHERE event_type = 'block'
ORDER BY timestamp DESC;

.exit
```

**✅ Expected:**
```
Database contains audit events
Events show timestamps, IPs, policies, actions
All test requests logged
```

### Test 9.2: Generate Statistics

```bash
# SSH to OPNsense
source /usr/local/yori-venv/bin/activate

python << 'EOF'
from yori.audit_enforcement import EnforcementAuditLogger

logger = EnforcementAuditLogger("/var/db/yori/audit.db")
stats = logger.get_enforcement_stats()

print("Enforcement Statistics:")
print(f"  Total blocks: {stats['total_blocks']}")
print(f"  Total overrides: {stats['total_overrides']}")
print(f"  Total bypasses: {stats['total_bypasses']}")

events = logger.get_recent_events(limit=20)
print(f"\nRecent events: {len(events)}")
for event in events[:5]:
    print(f"  - {event}")
EOF
```

**✅ Expected:**
```
Statistics show actual numbers from testing
Recent events listed
```

---

## Phase 10: Performance & Load Testing

**Duration:** 30 minutes (optional)

### Test 10.1: Measure Latency Overhead

**Without YORI (baseline):**
```bash
# From client - direct to real API
time curl https://www.google.com/
# Note the time
```

**With YORI:**
```bash
# Via YORI proxy
time curl -k https://api.openai.com/
# Compare times
```

**✅ Target:**
```
YORI overhead < 10ms
Total response time reasonable
```

### Test 10.2: Load Test

```bash
# From client - install apache bench
sudo apt install apache2-utils  # or yum, brew, etc.

# Send 100 requests, 10 concurrent
ab -n 100 -c 10 -k https://api.openai.com/

# Check YORI performance
# SSH to OPNsense
top  # Should show reasonable CPU/memory
```

**✅ Target:**
```
Memory < 256MB
CPU < 50% average
No crashes or errors
```

---

## Test Completion Checklist

### Phase 1: OPNsense Setup ✓
- [ ] OPNsense installed
- [ ] Network configured (WAN + LAN)
- [ ] Web UI accessible
- [ ] SSH enabled

### Phase 2: Package Installation ✓
- [ ] YORI wheel built
- [ ] Transferred to OPNsense
- [ ] Installed in virtualenv
- [ ] All imports work

### Phase 3: Service Configuration ✓
- [ ] Config file created
- [ ] rc.d script created
- [ ] Service enabled
- [ ] Directories created

### Phase 4: Network Setup ✓
- [ ] TLS certificates created
- [ ] DNS overrides configured
- [ ] Client can resolve to 10.0.0.1
- [ ] Port 8443 accessible

### Phase 5: Service Running ✓
- [ ] Service starts without errors
- [ ] Listening on port 8443
- [ ] Logs show startup
- [ ] Process running

### Phase 6: Client Config ✓
- [ ] Client has correct network settings
- [ ] DNS resolves through OPNsense
- [ ] CA certificate installed
- [ ] Can ping gateway

### Phase 7: Traffic Tests ✓
- [ ] DNS interception works
- [ ] Connections reach YORI
- [ ] tcpdump shows traffic
- [ ] Logs show requests

### Phase 8: Enforcement Tests ✓
- [ ] Observe mode works
- [ ] Allowlist recognized
- [ ] Time exceptions apply
- [ ] Enforcement mode blocks
- [ ] Emergency override works

### Phase 9: Audit ✓
- [ ] Database has entries
- [ ] Statistics generated
- [ ] Events queryable
- [ ] Logs complete

### Phase 10: Performance ✓
- [ ] Latency acceptable
- [ ] Load test passes
- [ ] Memory within limits
- [ ] No crashes

---

## Known Limitations & Workarounds

### Limitation 1: Proxy Not Fully Implemented

**Status:** Current code has stub proxy
**Impact:** Requests intercepted but not forwarded
**Workaround:**
- Tests prove interception works (DNS + port forwarding)
- Can validate enforcement logic
- Full proxy implementation needed for production

### Limitation 2: OPNsense Plugin UI Missing

**Status:** No web UI integration yet
**Impact:** Must use SSH/config files
**Workaround:**
- Edit /usr/local/etc/yori/yori.conf manually
- Use `service yori restart` to apply changes
- Query database directly with sqlite3

### Limitation 3: Certificate Management Manual

**Status:** Certificates created manually
**Impact:** Requires client-side CA installation
**Workaround:**
- Use OPNsense built-in CA feature
- Document CA installation steps
- Consider Let's Encrypt for production

---

## Troubleshooting Guide

### Issue: YORI Service Won't Start

**Check:**
```bash
# View full error
service yori start
tail -50 /var/log/yori/yori.log

# Check Python environment
source /usr/local/yori-venv/bin/activate
python -c "import yori"

# Check permissions
ls -la /usr/local/etc/yori/
ls -la /var/db/yori/
```

**Fix:**
- Ensure virtualenv has all dependencies
- Check config file syntax (YAML)
- Verify file permissions

### Issue: DNS Not Resolving to 10.0.0.1

**Check:**
```bash
# From client
nslookup api.openai.com 10.0.0.1  # Direct query to OPNsense

# From OPNsense
service unbound status
unbound-control dump_cache | grep openai
```

**Fix:**
- Verify host override in Unbound
- Restart Unbound: `service unbound restart`
- Clear DNS cache on client

### Issue: Requests Not Being Intercepted

**Check:**
```bash
# On OPNsense
sockstat -l | grep 8443           # Is YORI listening?
tcpdump -i em1 port 8443          # See any traffic?
netstat -an | grep 8443           # Check connections
```

**Fix:**
- Verify DNS override working
- Check firewall rules not blocking
- Ensure port forwarding correct
- Test with telnet first

### Issue: Database Empty

**Check:**
```bash
ls -lh /var/db/yori/audit.db      # Does it exist?
sqlite3 /var/db/yori/audit.db ".tables"  # Tables created?
tail -f /var/log/yori/yori.log    # Any database errors?
```

**Fix:**
- Initialize database manually if needed
- Check write permissions on /var/db/yori/
- Verify audit logging enabled in code

---

## Success Criteria

### Minimum Viable Demonstration

✅ **Traffic Interception:**
- DNS resolves LLM domains to OPNsense
- Connections reach YORI service
- tcpdump shows traffic flow

✅ **Enforcement Logic:**
- Allowlist recognized
- Time exceptions apply
- Enforcement mode blocks
- Emergency override works

✅ **Audit Trail:**
- All events logged to database
- Statistics generated
- Query historical data

### Full Production Readiness (Future)

- [ ] Proxy forwards requests to real APIs
- [ ] TLS termination working
- [ ] Block page returned to clients
- [ ] OPNsense web UI integrated
- [ ] Performance benchmarks met
- [ ] Documentation complete

---

## Next Steps After Testing

### If Tests Pass:
1. Document successful configuration
2. Create installation guide from working setup
3. Begin proxy implementation
4. Design OPNsense plugin UI

### If Tests Fail:
1. Document failure points
2. Identify missing components
3. Prioritize implementation work
4. Re-test after fixes

---

## Appendix: Quick Reference Commands

**OPNsense SSH:**
```bash
ssh root@10.0.0.1
```

**Service Management:**
```bash
service yori start|stop|restart|status
```

**View Logs:**
```bash
tail -f /var/log/yori/yori.log
tail -f /var/log/yori/proxy.log
```

**Database Query:**
```bash
sqlite3 /var/db/yori/audit.db "SELECT * FROM audit_events LIMIT 10;"
```

**Network Testing:**
```bash
# From client
nslookup api.openai.com
telnet api.openai.com 443
curl -k https://api.openai.com/

# From OPNsense
tcpdump -i em1 port 8443
sockstat -l | grep 8443
netstat -an | grep 8443
```

---

**Total Estimated Time:** 4-6 hours (first deployment), 2-3 hours (subsequent)

**Difficulty:** Advanced

**Recommendation:** Start with VM environment before attempting on production hardware

