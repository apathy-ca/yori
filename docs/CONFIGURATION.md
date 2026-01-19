# YORI Configuration Reference

Complete reference for configuring YORI via the `yori.conf` file.

---

## Table of Contents

- [Configuration File Location](#configuration-file-location)
- [File Format](#file-format)
- [Configuration Sections](#configuration-sections)
  - [Operating Mode](#operating-mode)
  - [Listen Address](#listen-address)
  - [LLM Endpoints](#llm-endpoints)
  - [Audit Logging](#audit-logging)
  - [Policy Engine](#policy-engine)
- [Complete Configuration Example](#complete-configuration-example)
- [Environment Variable Overrides](#environment-variable-overrides)
- [Validation and Defaults](#validation-and-defaults)
- [Advanced Configuration](#advanced-configuration)
- [Configuration via Web UI](#configuration-via-web-ui)
- [Troubleshooting Configuration](#troubleshooting-configuration)

---

## Configuration File Location

YORI searches for configuration in this order:

1. `/usr/local/etc/yori/yori.conf` (default on FreeBSD/OPNsense)
2. `/etc/yori/yori.conf` (alternate location)
3. `./yori.conf` (current working directory)

**Recommended location:** `/usr/local/etc/yori/yori.conf`

### Creating Configuration File

```bash
# Create directory
mkdir -p /usr/local/etc/yori

# Copy sample configuration
cp /usr/local/share/examples/yori/yori.conf.sample \
   /usr/local/etc/yori/yori.conf

# Edit configuration
ee /usr/local/etc/yori/yori.conf
```

### File Permissions

```bash
# Configuration should be readable by yori user
chown root:wheel /usr/local/etc/yori/yori.conf
chmod 644 /usr/local/etc/yori/yori.conf
```

---

## File Format

YORI uses YAML format for configuration.

**Basic structure:**

```yaml
# Operation mode
mode: observe

# Listen address for proxy
listen: 0.0.0.0:8443

# LLM endpoints to intercept
endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true

# Audit logging settings
audit:
  database: /var/db/yori/audit.db
  retention_days: 365

# Policy engine settings
policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego
```

**YAML Tips:**
- Indentation matters (use 2 spaces, not tabs)
- Strings don't need quotes unless they contain special characters
- Comments start with `#`
- Boolean values: `true` or `false` (lowercase)

---

## Configuration Sections

### Operating Mode

Controls how YORI handles LLM traffic.

```yaml
mode: observe
```

**Type:** String (enum)

**Valid Values:**
- `observe` - Log all traffic, never block (default)
- `advisory` - Log and send alerts, never block
- `enforce` - Can block traffic based on policies (requires user opt-in)

**Description:**

| Mode | Logs Traffic | Sends Alerts | Can Block | Use Case |
|------|-------------|--------------|-----------|----------|
| `observe` | ✅ | ❌ | ❌ | Learning usage patterns, baseline |
| `advisory` | ✅ | ✅ | ❌ | Awareness without control |
| `enforce` | ✅ | ✅ | ✅ | Active governance and blocking |

**Recommendations:**
- **Week 1-2:** Use `observe` to understand your household's AI usage
- **Week 3+:** Switch to `advisory` to get alerts without disruption
- **Advanced users only:** Use `enforce` after thoroughly testing policies

**Example:**

```yaml
# Conservative approach: start with observe
mode: observe

# After 2 weeks, move to advisory
mode: advisory

# Advanced: enable enforcement (requires well-tested policies)
mode: enforce
```

---

### Listen Address

Configures the address and port where YORI's proxy listens.

```yaml
listen: 0.0.0.0:8443
```

**Type:** String (format: `IP:PORT`)

**Default:** `0.0.0.0:8443`

**Components:**
- **IP Address:**
  - `0.0.0.0` - Listen on all interfaces (default)
  - `127.0.0.1` - Listen only on localhost (local NAT redirection only)
  - `192.168.1.1` - Listen on specific interface IP
- **Port:**
  - `8443` - Default HTTPS interception port
  - Must be different from OPNsense web UI (typically 443 or 8443)

**Common Configurations:**

```yaml
# Default: Accept connections on all interfaces
listen: 0.0.0.0:8443

# Localhost only (for transparent NAT redirection)
listen: 127.0.0.1:8443

# Specific LAN interface
listen: 192.168.1.1:8443

# Custom port (if 8443 conflicts with something)
listen: 0.0.0.0:9443
```

**Port Selection Guidelines:**
- Avoid 443 (likely used by OPNsense web UI)
- Avoid 8443 if OPNsense GUI uses it
- Common alternatives: 9443, 10443, 11443
- Must be >1024 to run as non-root (not recommended for YORI)

**Security Note:** Binding to `0.0.0.0` means YORI is reachable from all network interfaces. Ensure firewall rules restrict access appropriately.

---

### LLM Endpoints

Specifies which LLM providers to intercept and monitor.

```yaml
endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true
  - domain: gemini.google.com
    enabled: true
  - domain: api.mistral.ai
    enabled: true
```

**Type:** List of objects

**Object Schema:**
- `domain` (required): Domain name of LLM API (without `https://`)
- `enabled` (optional): Whether to intercept this endpoint (default: `true`)

**Default Endpoints:**

| Domain | Provider | Models | Enabled by Default |
|--------|----------|--------|-------------------|
| `api.openai.com` | OpenAI | GPT-4, GPT-3.5, DALL-E | ✅ |
| `api.anthropic.com` | Anthropic | Claude 3.5, Claude 3 | ✅ |
| `gemini.google.com` | Google | Gemini Pro, Gemini Ultra | ✅ |
| `api.mistral.ai` | Mistral AI | Mistral Large, Medium | ✅ |

**Adding Custom Endpoints:**

```yaml
endpoints:
  # Default endpoints
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true

  # Add custom/regional endpoints
  - domain: api.openai-azure.com
    enabled: true
  - domain: api.cohere.ai
    enabled: true
  - domain: api.huggingface.co
    enabled: true

  # Disable specific endpoint
  - domain: api.mistral.ai
    enabled: false
```

**Wildcard Support (Future):**

Currently, exact domain matching only. Subdomain wildcards planned for v0.2.0:

```yaml
# Planned for v0.2.0
endpoints:
  - domain: "*.openai.com"
    enabled: true
```

**Important Notes:**
- Domain names should NOT include protocol (`https://`)
- Domain names should NOT include paths (`/v1/chat`)
- Subdomains matter: `api.openai.com` ≠ `openai.com`
- Changes require service restart: `service yori restart`

---

### Audit Logging

Configures SQLite database for storing LLM request/response audit logs.

```yaml
audit:
  database: /var/db/yori/audit.db
  retention_days: 365
```

**Type:** Object

**Schema:**

#### `database`

**Type:** Path (string)

**Default:** `/var/db/yori/audit.db`

**Description:** Path to SQLite database file for audit logs.

**Recommendations:**

```yaml
# Default location (recommended)
audit:
  database: /var/db/yori/audit.db

# Alternative location (larger partition)
audit:
  database: /mnt/data/yori/audit.db

# RAM disk for high performance (volatile!)
audit:
  database: /tmp/yori/audit.db
```

**Storage Requirements:**

| Usage Level | Requests/Day | DB Size (1 year) |
|-------------|--------------|------------------|
| Light | 10 | ~3.6 MB |
| Medium | 100 | ~36 MB |
| Heavy | 1,000 | ~365 MB |
| Very Heavy | 10,000 | ~3.6 GB |

Formula: `~1 MB per 1,000 requests`

#### `retention_days`

**Type:** Integer

**Default:** `365`

**Range:** 1 to 3650 (10 years)

**Description:** Number of days to retain audit logs before automatic deletion.

**Recommendations:**

```yaml
# Short-term monitoring (home with limited disk)
audit:
  retention_days: 90

# Standard retention (recommended)
audit:
  retention_days: 365

# Extended retention (compliance, research)
audit:
  retention_days: 730  # 2 years

# Maximum retention (archive everything)
audit:
  retention_days: 3650  # 10 years
```

**Retention Strategy:**

- **90 days:** Sufficient for detecting usage patterns
- **365 days:** Recommended for annual cost analysis and trends
- **730+ days:** Useful for long-term research or compliance requirements

**Cleanup Behavior:**

YORI runs automatic cleanup daily at 03:00 local time:

```sql
DELETE FROM audit_events
WHERE timestamp < datetime('now', '-365 days');
```

**Manual Cleanup:**

```bash
# Trigger immediate cleanup
yori --cleanup-audit

# Vacuum database to reclaim space
sqlite3 /var/db/yori/audit.db "VACUUM;"
```

---

### Policy Engine

Configures the Rego policy engine for alerts and enforcement.

```yaml
policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego
```

**Type:** Object

**Schema:**

#### `directory`

**Type:** Path (string)

**Default:** `/usr/local/etc/yori/policies`

**Description:** Directory containing `.rego` policy files.

**Structure:**

```bash
/usr/local/etc/yori/policies/
├── home_default.rego       # Default allow-all policy
├── bedtime.rego            # After-hours alerts
├── high_usage.rego         # Usage threshold alerts
├── privacy.rego            # PII detection
└── homework_helper.rego    # Educational content detection
```

**Creating Policy Directory:**

```bash
mkdir -p /usr/local/etc/yori/policies
chown -R root:wheel /usr/local/etc/yori/policies
chmod 755 /usr/local/etc/yori/policies
```

#### `default`

**Type:** String (filename)

**Default:** `home_default.rego`

**Description:** Name of the default policy file to load if no specific policy matches.

**Behavior:**

- YORI loads all `.rego` files in the `directory`
- If multiple policies match a request, they are all evaluated
- The `default` policy runs if no other policy matches

**Policy Precedence (Future):**

```yaml
# Planned for v0.2.0: explicit policy ordering
policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego
  order:
    - privacy.rego       # Evaluate first
    - bedtime.rego       # Then bedtime
    - high_usage.rego    # Then usage limits
    - home_default.rego  # Finally default
```

**See Also:** [Policy Guide](POLICY_GUIDE.md) for writing custom policies.

---

## Complete Configuration Example

### Minimal Configuration

```yaml
# Minimal config - uses all defaults
mode: observe
```

This is valid! YORI will use default values for all omitted settings.

---

### Typical Home Configuration

```yaml
# Recommended configuration for home use
mode: observe
listen: 0.0.0.0:8443

endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true
  - domain: gemini.google.com
    enabled: true
  - domain: api.mistral.ai
    enabled: false  # Not used in this household

audit:
  database: /var/db/yori/audit.db
  retention_days: 365

policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego
```

---

### Advanced Configuration

```yaml
# Advanced configuration with custom settings
mode: advisory
listen: 127.0.0.1:9443  # Custom port, localhost only

endpoints:
  # Major providers
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true
  - domain: gemini.google.com
    enabled: true

  # Additional providers
  - domain: api.cohere.ai
    enabled: true
  - domain: api.together.xyz
    enabled: true

  # Azure OpenAI endpoint
  - domain: my-org.openai.azure.com
    enabled: true

audit:
  database: /mnt/data/yori/audit.db  # Larger partition
  retention_days: 730  # 2 years

policies:
  directory: /usr/local/etc/yori/policies
  default: strict_default.rego
```

---

### Development/Testing Configuration

```yaml
# Configuration for development and testing
mode: observe
listen: 127.0.0.1:8443

endpoints:
  - domain: api.openai.com
    enabled: true
  # Only monitor OpenAI for focused testing

audit:
  database: /tmp/yori-test.db  # Temporary database
  retention_days: 7  # Short retention for testing

policies:
  directory: ./test-policies  # Local policy directory
  default: test.rego
```

---

## Environment Variable Overrides

YORI supports environment variables to override configuration values (useful for containers or testing).

**Supported Variables:**

```bash
# Operating mode
export YORI_MODE=advisory

# Listen address
export YORI_LISTEN=0.0.0.0:9443

# Audit database path
export YORI_AUDIT_DB=/custom/path/audit.db

# Policy directory
export YORI_POLICY_DIR=/custom/policies
```

**Precedence (highest to lowest):**

1. Environment variables (if set)
2. Configuration file values
3. Built-in defaults

**Example Usage:**

```bash
# Override mode for testing
YORI_MODE=observe yori --config /usr/local/etc/yori/yori.conf

# Override multiple values
export YORI_MODE=advisory
export YORI_AUDIT_DB=/tmp/test.db
service yori restart
```

---

## Validation and Defaults

### Configuration Validation

YORI validates configuration on startup using Pydantic models.

**Check your configuration:**

```bash
# Validate configuration file
yori --check-config

# Expected output if valid:
# Configuration valid:
#   Mode: observe
#   Listen: 0.0.0.0:8443
#   Endpoints: 4 enabled
#   Audit DB: /var/db/yori/audit.db
#   Policies: 5 loaded from /usr/local/etc/yori/policies
```

**Common Validation Errors:**

```yaml
# ❌ Invalid mode
mode: monitoring  # Must be: observe, advisory, or enforce
# Error: mode must be one of: observe, advisory, enforce

# ❌ Invalid listen address
listen: 8443  # Missing IP address
# Error: listen must be in format IP:PORT

# ❌ Invalid retention
audit:
  retention_days: -1  # Must be positive
# Error: retention_days must be >= 1

# ❌ Missing required field
endpoints:
  - enabled: true  # Missing 'domain'
# Error: field 'domain' required
```

### Default Values

If you omit any configuration section, these defaults are used:

```yaml
# Complete default configuration
mode: observe
listen: 0.0.0.0:8443

endpoints:
  - domain: api.openai.com
    enabled: true
  - domain: api.anthropic.com
    enabled: true
  - domain: gemini.google.com
    enabled: true
  - domain: api.mistral.ai
    enabled: true

audit:
  database: /var/db/yori/audit.db
  retention_days: 365

policies:
  directory: /usr/local/etc/yori/policies
  default: home_default.rego
```

**View Active Configuration:**

```bash
# Show active configuration (including defaults)
yori --show-config

# Output in YAML format
yori --show-config --format yaml

# Output in JSON format
yori --show-config --format json
```

---

## Advanced Configuration

### Logging Configuration

Currently, YORI logs to syslog. Future versions will support log configuration:

```yaml
# Planned for v0.2.0
logging:
  level: info  # debug, info, warning, error
  destination: syslog  # syslog, file, stdout
  file: /var/log/yori/yori.log  # If destination=file
```

### TLS Configuration

TLS certificate management will be configurable in v0.2.0:

```yaml
# Planned for v0.2.0
tls:
  ca_cert: /usr/local/etc/yori/certs/yori-ca.crt
  ca_key: /usr/local/etc/yori/certs/yori-ca.key
  server_cert: /usr/local/etc/yori/certs/server.crt
  server_key: /usr/local/etc/yori/certs/server.key
  cert_validity_days: 3650
```

### Performance Tuning

Future configuration for performance optimization:

```yaml
# Planned for v0.3.0
performance:
  max_concurrent_requests: 1000
  request_timeout_seconds: 30
  cache_size_mb: 128
  worker_threads: 4
```

---

## Configuration via Web UI

The OPNsense plugin provides a web UI for configuration (v0.1.0).

### Accessing Configuration UI

1. Log in to OPNsense web UI
2. Navigate to **Services → YORI → Settings**
3. Modify settings via form
4. Click **Save** to write to `/usr/local/etc/yori/yori.conf`
5. Click **Restart Service** to apply changes

### Web UI vs Manual Editing

**Web UI (Recommended):**
- ✅ Input validation
- ✅ Dropdown menus for enums
- ✅ Automatic service restart
- ✅ Syntax error prevention
- ❌ Limited to supported options

**Manual Editing:**
- ✅ Full control over all options
- ✅ Bulk changes (copy-paste)
- ✅ Version control friendly
- ✅ Script-friendly
- ❌ Manual syntax errors possible
- ❌ Manual service restart required

**Best Practice:** Use web UI for initial setup, manual editing for advanced customization.

---

## Troubleshooting Configuration

### Service Won't Start After Config Change

**Symptom:**

```bash
service yori start
# Service fails to start, immediately exits
```

**Diagnosis:**

```bash
# Check configuration validity
yori --check-config
# Look for validation errors

# Check service logs
tail -f /var/log/yori/yori.log
# Look for config parsing errors

# Try running manually to see error
/usr/local/bin/yori --config /usr/local/etc/yori/yori.conf
# See immediate error output
```

**Common Fixes:**

```bash
# Restore from backup
cp /usr/local/etc/yori/yori.conf.bak \
   /usr/local/etc/yori/yori.conf

# Or revert to defaults
yori --generate-default-config > /usr/local/etc/yori/yori.conf

# Restart service
service yori restart
```

---

### Configuration Changes Not Taking Effect

**Symptom:** Changed `yori.conf` but behavior doesn't change.

**Cause:** Service must be restarted to reload configuration.

**Solution:**

```bash
# Always restart after config changes
service yori restart

# Verify new config is loaded
yori --show-config | grep mode
# Should show your new mode
```

---

### Port Already in Use

**Symptom:**

```
Error: Address already in use (os error 48)
Failed to bind to 0.0.0.0:8443
```

**Diagnosis:**

```bash
# Check what's using the port
sockstat -4 -l | grep 8443
```

**Solutions:**

```yaml
# Option 1: Change YORI's port
listen: 0.0.0.0:9443

# Option 2: Stop conflicting service
service other-service stop
```

---

### Database Permission Errors

**Symptom:**

```
Error: Permission denied (os error 13)
Cannot write to /var/db/yori/audit.db
```

**Solution:**

```bash
# Create database directory
mkdir -p /var/db/yori

# Set ownership (yori user)
chown -R yori:yori /var/db/yori

# Set permissions
chmod 755 /var/db/yori
chmod 644 /var/db/yori/audit.db  # If database exists
```

---

### Policy Files Not Loading

**Symptom:**

```
Warning: No policies loaded from /usr/local/etc/yori/policies
```

**Diagnosis:**

```bash
# Check directory exists
ls -la /usr/local/etc/yori/policies

# Check for .rego files
find /usr/local/etc/yori/policies -name "*.rego"
```

**Solution:**

```bash
# Create policy directory
mkdir -p /usr/local/etc/yori/policies

# Install default policies
cp /usr/local/share/examples/yori/policies/*.rego \
   /usr/local/etc/yori/policies/

# Verify
yori --list-policies
# Should show loaded policies
```

---

## Configuration Best Practices

1. **Always backup before changes:**
   ```bash
   cp /usr/local/etc/yori/yori.conf \
      /usr/local/etc/yori/yori.conf.bak
   ```

2. **Validate before restart:**
   ```bash
   yori --check-config && service yori restart
   ```

3. **Use version control:**
   ```bash
   cd /usr/local/etc/yori
   git init
   git add yori.conf
   git commit -m "Initial YORI configuration"
   ```

4. **Document customizations:**
   ```yaml
   # yori.conf
   # Custom configuration for Smith household
   # Last modified: 2026-01-15 by John
   # Reason: Added Azure OpenAI endpoint for work devices
   ```

5. **Test in observe mode first:**
   ```yaml
   # Always test new policies in observe mode
   mode: observe  # Verify behavior before switching to advisory/enforce
   ```

---

## See Also

- **[Installation Guide](INSTALLATION.md)** - Installing YORI
- **[Quick Start](QUICK_START.md)** - Getting started
- **[Policy Guide](POLICY_GUIDE.md)** - Writing custom policies
- **[User Guide](USER_GUIDE.md)** - Using YORI features
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues

---

**Configuration reference version:** v0.1.0 (2026-01-19)
