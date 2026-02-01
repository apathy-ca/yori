# YORI Installation Guide

## Quick Install (Recommended)

### Step 1: Build Package (on your dev machine)

```bash
# On Linux:
cd ~/Source/yori
./scripts/package_for_opnsense.sh
```

This creates: `dist/yori-0.2.0-freebsd-amd64.tar.gz` (~1.2MB)

### Step 2: Copy to OPNsense

```bash
scp dist/yori-0.2.0-freebsd-amd64.tar.gz root@opnsense:/tmp/
```

### Step 3: Install on OPNsense

```bash
# SSH to OPNsense
ssh root@opnsense

# Extract and install
cd /tmp
tar xzf yori-0.2.0-freebsd-amd64.tar.gz
cd yori-0.2.0-freebsd-amd64
sh install.sh
```

That's it! Pure Rust binary - maximum performance.

**Requirements:**
- OPNsense 24.1+ (FreeBSD 13+)
- No other dependencies - completely self-contained

**Installation time:** ~30 seconds

**Performance:** Pure Rust proxy - 50x-100x faster than Python

## What Gets Installed

```
/usr/local/yori-venv/           # Virtual environment with YORI
/usr/local/etc/yori/            # Configuration
  ├── yori.conf                 # Main config
  └── policies/                 # OPA policies
/usr/local/etc/rc.d/yori        # Service script
/usr/local/opnsense/mvc/        # Web UI integration
/var/db/yori/                   # Database
/var/log/yori/                  # Logs
```

## Starting YORI

```bash
# Start service
service yori start

# Check status
service yori status

# View logs
tail -f /var/log/yori/yori.log

# Access web UI
# Navigate to: YORI → Enforcement in OPNsense UI
```

## Configuration

Edit `/usr/local/etc/yori/yori.conf`:

```yaml
mode: observe  # observe, advisory, or enforce

listen: 0.0.0.0:8443

endpoints:
  - domain: api.openai.com
    enabled: true

enforcement:
  enabled: false
  consent_accepted: false
```

Restart after changes:
```bash
service yori restart
```

## Uninstall

```bash
# Stop service
service yori stop
sysrc yori_enable="NO"

# Remove files
rm -rf /usr/local/yori-venv
rm -rf /usr/local/etc/yori
rm /usr/local/etc/rc.d/yori
rm -rf /usr/local/opnsense/mvc/app/controllers/OPNsense/YORI
rm -rf /usr/local/opnsense/mvc/app/models/OPNsense/YORI
rm -rf /usr/local/opnsense/mvc/app/views/OPNsense/YORI
rm -rf /var/db/yori
rm -rf /var/log/yori

# Clear OPNsense cache
rm -rf /usr/local/opnsense/mvc/app/cache/*
service configd restart
```

## Troubleshooting

### Broken pkg/Segmentation Faults from Previous Attempts

If your system has mixed FreeBSD/OPNsense packages from previous installation attempts:

```bash
# The new installer avoids pkg entirely, but if pkg itself is broken:

# Option 1: Reinstall OPNsense (cleanest)
# Backup your config first, then reinstall from ISO

# Option 2: Fix pkg database (risky)
# Only if you know what you're doing:
pkg update -f
pkg upgrade -f

# Option 3: Just proceed anyway
# The new installer doesn't use pkg, so if Python 3.11 works, you're fine:
python3.11 --version  # Should show 3.11.x
cd /tmp/yori-0.2.0-freebsd-amd64
sh install.sh
```

### Service won't start

Check logs:
```bash
tail -50 /var/log/yori/yori.log
```

Verify Python can import:
```bash
/usr/local/yori-venv/bin/python -c "import yori; print('OK')"
```

### Web UI not showing

Clear OPNsense cache:
```bash
rm -rf /usr/local/opnsense/mvc/app/cache/*
service configd restart
service nginx restart
```

### Permission errors

Fix permissions:
```bash
chown -R www:www /usr/local/etc/yori
chown -R www:www /var/db/yori
```

## Advanced: Building from Source

If you want to build the package yourself, see `packaging/README.md`.

The package script does:
1. Cross-compiles Rust extension with `cross` tool
2. Bundles Python code
3. Creates self-contained tarball
4. No Rust needed on OPNsense!

## Upgrades

The installer automatically detects existing installations and offers upgrade options.

### Option 1: Upgrade (Recommended)

Keeps your configuration and backs up the database:

```bash
# Copy new package to OPNsense
scp dist/yori-0.2.0-freebsd-amd64.tar.gz root@OPNsense:/tmp/

# SSH and run installer
ssh root@OPNsense
cd /tmp
tar xzf yori-0.2.0-freebsd-amd64.tar.gz
cd yori-0.2.0-freebsd-amd64
sh install.sh

# Choose option "1" (Upgrade)
# - Stops service
# - Backs up config (yori.conf.bak.TIMESTAMP)
# - Backs up database (audit.db.bak.TIMESTAMP)
# - Installs new version
# - Preserves your configuration
# - Restarts service
```

### Option 2: Clean Install

Wipes everything and starts fresh:

```bash
# Same steps, but choose option "2" when prompted
# - Stops service
# - Removes all YORI files
# - Installs fresh
# - Uses default configuration
```

### Manual Upgrade (Advanced)

If you want full control:

```bash
# Stop service
service yori stop

# Backup config and database
cp /usr/local/etc/yori/yori.conf ~/yori.conf.backup
cp /var/db/yori/audit.db ~/audit.db.backup

# Install new version
cd /tmp/yori-0.2.0-freebsd-amd64
sh install.sh  # Choose option 2 (clean)

# Restore your config
cp ~/yori.conf.backup /usr/local/etc/yori/yori.conf

# Start service
service yori start
```
