# YORI Installation Guide

Complete installation instructions for YORI on OPNsense routers.

> ⚠️ **Development Status:** This guide describes the installation process for YORI v0.1.0. The OPNsense plugin is not yet available in the official repository. See [Building from Source](#building-from-source) for development installation.

---

## Table of Contents

- [System Requirements](#system-requirements)
- [Pre-Installation Checklist](#pre-installation-checklist)
- [Installation Methods](#installation-methods)
  - [Method 1: OPNsense Plugin Repository (Recommended)](#method-1-opnsense-plugin-repository-recommended)
  - [Method 2: Manual Package Installation](#method-2-manual-package-installation)
  - [Method 3: Building from Source](#method-3-building-from-source)
- [Post-Installation Configuration](#post-installation-configuration)
- [Upgrading YORI](#upgrading-yori)
- [Uninstallation](#uninstallation)
- [Troubleshooting Installation](#troubleshooting-installation)

---

## System Requirements

### Minimum Requirements

- **Operating System:** OPNsense 24.1 or later (FreeBSD 13.2+)
- **CPU:** 1 core x86_64 (amd64) or ARM64
- **RAM:** 512MB available (in addition to OPNsense base requirements)
- **Disk Space:** 1GB free (for binary + audit logs)
- **Network:** LAN interface configured and operational

### Recommended Requirements

- **Operating System:** OPNsense 24.7+ (latest stable)
- **CPU:** 2+ cores x86_64
- **RAM:** 1GB+ available
- **Disk Space:** 5GB+ (for extended audit log retention)
- **Network:** Separate management interface (recommended)

### Supported Platforms

| Platform | Architecture | Status |
|----------|-------------|---------|
| OPNsense 24.1+ | x86_64 (amd64) | ✅ Supported |
| OPNsense 24.1+ | ARM64 | 🔄 Planned |
| pfSense | x86_64 | ⏳ Future (requires port) |
| FreeBSD 13+ | x86_64 | ⚠️ Advanced (manual compile) |

### Known Hardware Compatibility

**Tested and Working:**
- Protectli Vault (FW4B, FW6)
- PC Engines APU2/APU3/APU4
- Netgate SG-1100, SG-2100, SG-3100
- Dell OptiPlex Micro (as router)
- Raspberry Pi 4 (ARM64 - with caveats)

**Performance Notes:**
- For <10 devices: Any hardware running OPNsense 24.1+ is sufficient
- For 10-50 devices: Recommended 2+ cores, 2GB+ RAM
- For 50+ devices: Consider SARK enterprise variant instead

---

## Pre-Installation Checklist

Before installing YORI, complete these steps:

### 1. Verify OPNsense Version

```bash
# SSH into your OPNsense router
ssh root@192.168.1.1

# Check version
opnsense-version
# Should show: OPNsense 24.1 or later
```

### 2. Check Available Resources

```bash
# Check free RAM (should have 512MB+ free)
top
# Look for "Free" memory in the top section

# Check free disk space (need 1GB+ free)
df -h
# Look at /usr partition - should have 1G+ available
```

### 3. Verify Internet Connectivity

```bash
# Test external connectivity
ping -c 3 8.8.8.8

# Test package repository access
pkg update
```

### 4. Backup Current Configuration

**Critical:** Always backup before installing new packages.

1. In OPNsense web UI: **System → Configuration → Backups**
2. Click **Download configuration**
3. Save to a safe location (not on the router)

---

## Installation Methods

### Method 1: OPNsense Plugin Repository (Recommended)

This is the easiest method once YORI is available in the official OPNsense plugin repository.

#### Step 1: Access Plugin Manager

1. Log in to OPNsense web UI
2. Navigate to **System → Firmware → Plugins**
3. Wait for plugin list to load

#### Step 2: Search and Install

1. In the search box, type "yori"
2. Find **os-yori** in the results
3. Click the **+** (plus) button to install
4. Confirm installation when prompted

#### Step 3: Wait for Installation

Installation takes 1-3 minutes depending on internet speed:

```
Installing os-yori...
  Fetching os-yori-0.1.0.pkg: 100%
  Installing os-yori-0.1.0
  Extracting os-yori-0.1.0: 100%
  Running post-install scripts...
  Creating /var/db/yori directory...
  Installing rc.d service script...
  Compiling Python bytecode...
  Installation complete.
```

#### Step 4: Verify Installation

```bash
# SSH into router
ssh root@192.168.1.1

# Check package is installed
pkg info os-yori
# Should show version and description

# Verify YORI binary exists
which yori
# Should show: /usr/local/bin/yori

# Check service script
service yori status
# Should show: yori is not running (expected before configuration)
```

#### Step 5: Enable Service

```bash
# Enable YORI to start on boot
service yori enable

# Start the service
service yori start

# Verify it's running
service yori status
# Should show: yori is running as pid 12345
```

---

### Method 2: Manual Package Installation

Use this method if you have a pre-built `.pkg` file (e.g., from GitHub releases).

#### Step 1: Download Package

```bash
# SSH into OPNsense
ssh root@192.168.1.1

# Create temporary directory
mkdir -p /tmp/yori-install
cd /tmp/yori-install

# Download package (replace URL with actual release)
fetch https://github.com/apathy-ca/yori/releases/download/v0.1.0/os-yori-0.1.0.pkg

# Verify checksum (important for security)
fetch https://github.com/apathy-ca/yori/releases/download/v0.1.0/SHA256SUM
sha256 -c SHA256SUM os-yori-0.1.0.pkg
```

#### Step 2: Install Package

```bash
# Install using pkg
pkg install ./os-yori-0.1.0.pkg

# Confirm installation when prompted
# Press 'y' to proceed
```

#### Step 3: Post-Install Verification

Same as Method 1, Step 4 above.

---

### Method 3: Building from Source

For developers or advanced users who want to build from source.

> **Note:** This method requires a FreeBSD build environment. See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for detailed instructions.

#### Prerequisites

- FreeBSD 13.2+ build machine (can be a VM)
- Rust 1.92+ toolchain
- Python 3.11+
- OPNsense development tools

#### Quick Build

```bash
# Clone repository
git clone https://github.com/apathy-ca/yori.git
cd yori

# Install build dependencies
./scripts/install-deps.sh

# Build for FreeBSD (if on Linux/macOS, this cross-compiles)
./scripts/build.sh --target x86_64-unknown-freebsd --release

# Create package
./scripts/package.sh --version 0.1.0

# Output: dist/os-yori-0.1.0.pkg
```

Then follow [Method 2](#method-2-manual-package-installation) to install the built package.

**For detailed build instructions,** see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#building-from-source).

---

## Post-Installation Configuration

After installing YORI, complete these configuration steps before first use.

### 1. Access YORI Configuration UI

1. In OPNsense web UI, navigate to **Services → YORI → Settings**
2. You should see the YORI configuration page

> **If "YORI" doesn't appear in Services menu:**
> - Refresh browser (Ctrl+F5)
> - Log out and log back in to OPNsense
> - Check installation: `pkg info os-yori`

### 2. Basic Configuration

#### Operating Mode

Select initial operating mode:

- **Observe:** Logs all traffic, never blocks (recommended for first week)
- **Advisory:** Sends alerts but allows all traffic
- **Enforce:** Can block traffic based on policies (requires opt-in)

**Recommendation:** Start with **Observe** mode for 7 days to establish baseline.

#### Listen Address

Default: `0.0.0.0:8443`

- `0.0.0.0` means listen on all interfaces
- Port `8443` is the HTTPS proxy port

**Advanced:** Change to `127.0.0.1:8443` if using only local NAT redirection.

#### LLM Endpoints

Enable endpoints you want to monitor:

- ✅ **api.openai.com** - ChatGPT, GPT-4, DALL-E
- ✅ **api.anthropic.com** - Claude (all models)
- ✅ **gemini.google.com** - Google Gemini
- ✅ **api.mistral.ai** - Mistral AI

**Recommendation:** Enable all endpoints for comprehensive visibility.

#### Audit Database

Default settings:

```yaml
database: /var/db/yori/audit.db
retention_days: 365
```

**Customize retention:**
- **90 days:** Light usage, limited disk space
- **365 days:** Default, good for annual analysis
- **730 days:** Extended retention for compliance

**Disk usage estimate:**
- ~1MB per 1,000 requests
- Average home: ~100 requests/day = ~36MB/year

### 3. Save Configuration

Click **Save** to write configuration to `/usr/local/etc/yori/yori.conf`.

### 4. Start YORI Service

```bash
# Via web UI
Services → YORI → Settings → [Start Service] button

# Or via SSH
service yori start
```

Verify service started:

```bash
service yori status
# Should show: yori is running as pid [number]

# Check logs
tail -f /var/log/yori/yori.log
# Should show startup messages
```

### 5. Install CA Certificate on Devices

YORI uses TLS interception to inspect LLM traffic. Devices must trust YORI's Certificate Authority.

**Generate CA Certificate:**

1. Navigate to **Services → YORI → Certificate Management**
2. Click **Generate YORI CA**
3. Fill in details:
   - Common Name: `YORI Home LLM Gateway`
   - Organization: Your family name
   - Valid for: 3650 days (10 years)
4. Click **Generate**
5. Click **Download CA Certificate** → Save as `yori-ca.crt`

**Install on devices:** See [CA Certificate Installation](#ca-certificate-installation) section below.

### 6. Configure Transparent Proxy (NAT)

Set up NAT rules to redirect LLM traffic through YORI.

#### Create LLM Endpoint Alias

1. Navigate to **Firewall → Aliases**
2. Click **Add**
3. Configure:
   - **Name:** `LLM_Endpoints`
   - **Type:** Host(s)
   - **Content:**
     ```
     api.openai.com
     api.anthropic.com
     gemini.google.com
     api.mistral.ai
     ```
4. **Description:** "LLM API endpoints for YORI monitoring"
5. Click **Save**
6. Click **Apply Changes**

#### Create NAT Port Forward Rule

1. Navigate to **Firewall → NAT → Port Forward**
2. Click **Add** (top right)
3. Configure rule:
   - **Interface:** LAN (or your internal interface)
   - **Protocol:** TCP
   - **Source:** LAN net (or specific devices)
   - **Destination / Invert:** Unchecked
   - **Destination:** LLM_Endpoints (select the alias)
   - **Destination port range:** HTTPS (443)
   - **Redirect target IP:** 127.0.0.1
   - **Redirect target port:** 8443
   - **Description:** "Redirect LLM traffic to YORI"
   - **NAT reflection:** Disable
4. Click **Save**
5. Click **Apply Changes**

#### Verify NAT Rule

```bash
# Check active NAT rules
pfctl -s nat | grep 8443
# Should show rule redirecting 443 → 8443
```

---

## CA Certificate Installation

Detailed instructions for installing YORI's CA certificate on all device types.

### macOS

```bash
# Method 1: Double-click
# Just double-click yori-ca.crt, add to System keychain, then trust it

# Method 2: Command line
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain yori-ca.crt
```

**Verify:** Open Keychain Access → System → Find "YORI Home LLM Gateway" → Should show green checkmark.

### Windows 10/11

```powershell
# Method 1: GUI
# Right-click yori-ca.crt → Install Certificate
# Store Location: Local Machine
# Certificate Store: Trusted Root Certification Authorities

# Method 2: PowerShell (as Administrator)
Import-Certificate -FilePath "yori-ca.crt" `
  -CertStoreLocation "Cert:\LocalMachine\Root"
```

**Verify:** Run `certmgr.msc` → Trusted Root Certification Authorities → Certificates → Find "YORI Home LLM Gateway".

### Linux (Ubuntu/Debian)

```bash
# Copy to system trust store
sudo cp yori-ca.crt /usr/local/share/ca-certificates/yori-ca.crt

# Update trust store
sudo update-ca-certificates

# Verify
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt yori-ca.crt
# Should show: yori-ca.crt: OK
```

### iOS/iPadOS

1. AirDrop `yori-ca.crt` to device (or email to yourself)
2. Tap the file → **Profile Downloaded**
3. **Settings → General → VPN & Device Management**
4. Tap the YORI profile → **Install**
5. Enter device passcode
6. Tap **Install** again (warning appears)
7. **Settings → General → About → Certificate Trust Settings**
8. Enable **full trust** for "YORI Home LLM Gateway"

**Verify:** Visit https://www.howsmyssl.com/ - should load without warnings.

### Android

1. Transfer `yori-ca.crt` to device (USB or download)
2. **Settings → Security → Encryption & credentials**
3. **Install a certificate → CA certificate**
4. Warning appears → **Install anyway**
5. Navigate to `yori-ca.crt` → Select
6. Give it a name: "YORI CA"

**Verify:** Chrome should now trust YORI-intercepted connections.

### Chrome OS

```bash
# Method 1: Via Settings UI
# Settings → Security and Privacy → Manage certificates
# Authorities tab → Import → Select yori-ca.crt
# Trust for identifying websites: Yes

# Method 2: Via chrome://settings
# Navigate to: chrome://settings/certificates
# Authorities → Import → yori-ca.crt
```

---

## Upgrading YORI

### Upgrading from OPNsense Plugin Repository

```bash
# Update package repository
pkg update

# Upgrade os-yori
pkg upgrade os-yori

# Restart service
service yori restart
```

### Upgrading from Manual Package

```bash
# Download new version
fetch https://github.com/apathy-ca/yori/releases/download/v0.2.0/os-yori-0.2.0.pkg

# Verify checksum
fetch https://github.com/apathy-ca/yori/releases/download/v0.2.0/SHA256SUM
sha256 -c SHA256SUM os-yori-0.2.0.pkg

# Upgrade package
pkg install ./os-yori-0.2.0.pkg
# Note: pkg install handles upgrades automatically

# Restart service
service yori restart
```

### Post-Upgrade Steps

1. Review [CHANGELOG.md](../CHANGELOG.md) for breaking changes
2. Check configuration: `yori --check-config`
3. Verify service health: `service yori status`
4. Review logs: `tail -f /var/log/yori/yori.log`

---

## Uninstallation

### Complete Removal

```bash
# Stop service
service yori stop

# Disable service
service yori disable

# Remove package
pkg remove os-yori

# Remove configuration (optional)
rm -rf /usr/local/etc/yori

# Remove audit database (optional - contains all history)
rm -rf /var/db/yori

# Remove logs (optional)
rm -rf /var/log/yori
```

### Remove NAT Rules

1. **Firewall → NAT → Port Forward**
2. Find YORI redirect rule → Click **Delete**
3. **Apply Changes**

### Remove CA Certificate from Devices

Reverse the CA installation steps on each device to remove trust.

**macOS:**
```bash
sudo security delete-certificate -c "YORI Home LLM Gateway" \
  /Library/Keychains/System.keychain
```

**Windows:**
```powershell
# In certmgr.msc, find and delete the YORI certificate
```

**Linux:**
```bash
sudo rm /usr/local/share/ca-certificates/yori-ca.crt
sudo update-ca-certificates --fresh
```

---

## Troubleshooting Installation

### Package Not Found in Plugin Repository

**Symptom:** "yori" search returns no results in System → Firmware → Plugins

**Causes:**
- YORI not yet published to official repository (expected in v0.1.0)
- OPNsense version too old (need 24.1+)
- Package repository out of date

**Solutions:**
```bash
# Update package repository
pkg update

# Check OPNsense version
opnsense-version
# Upgrade if < 24.1

# Alternative: Use manual installation method
```

---

### Installation Fails: "Dependency not found"

**Symptom:**
```
Installing os-yori-0.1.0...
Error: Dependency python311 not found
```

**Solution:**
```bash
# Install missing dependencies manually
pkg install python311 py311-pip

# Retry installation
pkg install os-yori
```

---

### Service Won't Start After Installation

**Symptom:**
```bash
service yori start
# Returns error or service immediately stops
```

**Diagnosis:**
```bash
# Check logs for errors
cat /var/log/yori/yori.log

# Try running manually to see error
/usr/local/bin/yori --config /usr/local/etc/yori/yori.conf
```

**Common causes:**
1. **Port 8443 already in use:**
   ```bash
   sockstat -4 -l | grep 8443
   # If something else is using it, change YORI port in config
   ```

2. **Missing configuration file:**
   ```bash
   # Create default config
   cp /usr/local/share/examples/yori/yori.conf.sample \
      /usr/local/etc/yori/yori.conf
   ```

3. **Permission issues:**
   ```bash
   # Fix ownership
   chown -R root:wheel /usr/local/etc/yori
   chown -R yori:yori /var/db/yori
   ```

---

### CA Certificate Installation Fails on iOS

**Symptom:** Certificate installs but devices still show "untrusted" warnings

**Cause:** Certificate trust not enabled (iOS requires 2-step process)

**Solution:**
1. Install profile first: Settings → Profile Downloaded → Install
2. **Then enable trust:** Settings → General → About → Certificate Trust Settings
3. Toggle **Enable Full Trust** for YORI CA

---

### NAT Redirection Not Working

**Symptom:** LLM requests bypass YORI, audit logs empty

**Diagnosis:**
```bash
# Test if traffic is being redirected
tcpdump -i em0 -n tcp port 8443
# Generate LLM traffic on a device
# You should see packets on port 8443

# Check NAT rules are active
pfctl -s nat | grep 8443
```

**Solutions:**

1. **Verify alias is correct:**
   - Firewall → Aliases → LLM_Endpoints
   - Ensure all domains listed without http:// prefix

2. **Check rule order:**
   - NAT rules are processed top-to-bottom
   - YORI redirect rule should be before any blanket allow rules

3. **Verify interface:**
   - NAT rule must be on interface where LLM traffic enters
   - Usually "LAN" but check your topology

4. **Test with curl:**
   ```bash
   # From a LAN device (not the router)
   curl -v https://api.openai.com
   # Connection should be intercepted by YORI
   # Check YORI logs for this request
   ```

---

### Out of Disk Space After Installation

**Symptom:**
```
pkg: Insufficient space in /usr (need 1GB, have 500MB)
```

**Solutions:**

1. **Clean old packages:**
   ```bash
   pkg clean
   pkg autoremove
   ```

2. **Remove old OPNsense backups:**
   - System → Configuration → Backups → Delete old backups

3. **Reduce audit retention:**
   - Services → YORI → Settings → Retention: 90 days (instead of 365)

4. **Move audit database to larger partition:**
   ```yaml
   # In /usr/local/etc/yori/yori.conf
   audit:
     database: /var/db/yori/audit.db  # Change to larger mount point
   ```

---

## Next Steps

After successful installation:

1. **[Quick Start Guide](QUICK_START.md)** - Get monitoring in 15 minutes
2. **[Configuration Reference](CONFIGURATION.md)** - Detailed config options
3. **[User Guide](USER_GUIDE.md)** - Using the dashboard and features
4. **[Policy Guide](POLICY_GUIDE.md)** - Setting up alerts and policies

---

## Getting Help

**Installation Issues:**
- Check [Troubleshooting Guide](TROUBLESHOOTING.md)
- Search [GitHub Issues](https://github.com/apathy-ca/yori/issues)
- Ask in [GitHub Discussions](https://github.com/apathy-ca/yori/discussions)

**Security Vulnerabilities:**
- Report privately via [GitHub Security Advisories](https://github.com/apathy-ca/yori/security/advisories/new)

---

**Installation guide version:** v0.1.0 (2026-01-19)
