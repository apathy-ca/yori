# YORI Packaging

This directory contains packaging infrastructure for distributing YORI as an installable plugin.

## Installation Methods

### Method 1: One-Line Installer (Recommended for Users)

The easiest way to install YORI on OPNsense:

```bash
curl -sSL https://raw.githubusercontent.com/apathy-ca/yori/main/install.sh | sh
```

or

```bash
fetch https://raw.githubusercontent.com/apathy-ca/yori/main/install.sh
sh install.sh
```

**With a local wheel file:**
```bash
# If you've built the wheel locally
YORI_WHEEL=/path/to/yori-0.2.0-*.whl sh install.sh
```

**What it does:**
1. Detects OPNsense version
2. Tries to download pre-built wheel from GitHub releases
3. Falls back to building from source if no release available
4. Or uses local wheel if YORI_WHEEL is set
5. Installs in isolated venv (/usr/local/yori-venv)
6. Copies OPNsense UI files
7. Creates configuration files
8. Installs and enables rc.d service

**Time:**
- ~2-3 minutes (with pre-built wheel)
- ~5-10 minutes (building from source)

### Method 2: FreeBSD Package (Future - Most Professional)

Once YORI is added to FreeBSD ports or OPNsense plugin repository:

```bash
pkg install os-yori
```

or via OPNsense Web UI:
```
System → Firmware → Plugins → os-yori [Install]
```

**Status:** Infrastructure ready in `freebsd/` directory, needs:
- Submission to FreeBSD ports
- Or hosting in custom pkg repository
- Or inclusion in OPNsense plugin repository

### Method 3: Manual Installation (Development/Testing)

Follow the detailed deployment plan in `docs/OPNSENSE_DEPLOYMENT_TEST_PLAN.md`

## For Developers: Building Packages

### Building FreeBSD Package

```bash
# On FreeBSD or OPNsense:
cd packaging/freebsd
make package

# Creates: yori-0.2.0.pkg
```

### Building Wheel for Release

```bash
# On development machine:
python -m build --wheel

# Or for FreeBSD:
# 1. Copy to OPNsense
# 2. Run: maturin build --release
# 3. Copy wheel back to dist/
```

### Creating GitHub Release with Pre-Built Wheel

To make installation faster for users, create a release with a pre-built FreeBSD wheel:

```bash
# Option A: Build on OPNsense (most reliable)
ssh root@opnsense
pkg install rust python311 py311-sqlite3
python3.11 -m ensurepip
python3.11 -m pip install maturin
cd /tmp
fetch https://github.com/apathy-ca/yori/archive/refs/tags/v0.2.0.tar.gz
tar xzf v0.2.0.tar.gz
cd yori-0.2.0
maturin build --release
# Wheel is in: target/wheels/yori-0.2.0-cp39-abi3-freebsd_13_x86_64.whl

# Copy back to dev machine
scp root@opnsense:/tmp/yori-0.2.0/target/wheels/yori-*.whl .

# Option B: Cross-compile with cross (less reliable, dependency issues)
cross build --release --target x86_64-unknown-freebsd --manifest-path rust/yori-core/Cargo.toml --lib
# Then manually package into wheel (complex)

# Create GitHub release
gh release create v0.2.0 \
  yori-0.2.0-cp39-abi3-freebsd_13_x86_64.whl \
  --title "YORI v0.2.0" \
  --notes "See CHANGELOG.md"

# Test installer downloads correctly
curl -sSL https://raw.githubusercontent.com/apathy-ca/yori/v0.2.0/install.sh | sh
```

**If no release exists**, the installer will automatically fall back to building from source on the target OPNsense system.

## Directory Structure

```
packaging/
├── README.md                 # This file
├── freebsd/
│   ├── Makefile             # FreeBSD port Makefile
│   ├── pkg-descr            # Package description
│   ├── pkg-plist            # File manifest
│   └── files/
│       └── yori.in          # rc.d service template
└── scripts/
    ├── build-pkg.sh         # Build FreeBSD package
    └── test-install.sh      # Test installation in VM
```

## Installation Flow

### One-Line Installer Flow

```
User runs: curl ... | sh
  ↓
install.sh detects OPNsense
  ↓
Installs dependencies (pkg install python311...)
  ↓
Downloads wheel from GitHub releases
  ↓
Installs wheel (pip install yori-*.whl)
  ↓
Downloads source for OPNsense UI files
  ↓
Copies UI files to /usr/local/opnsense/
  ↓
Creates rc.d service script
  ↓
Creates default config
  ↓
Enables service
  ↓
Done! User goes to Web UI
```

### FreeBSD Package Flow (Future)

```
User runs: pkg install os-yori
  ↓
pkg downloads os-yori-0.2.0.pkg
  ↓
Extracts files to /usr/local/
  ↓
Runs +INSTALL script
  ↓
Configures service
  ↓
Done! User goes to Web UI
```

## Requirements for pkg Repository

To host YORI in a custom pkg repository:

1. **Build the package:**
   ```bash
   cd packaging/freebsd
   make package
   ```

2. **Sign the package:**
   ```bash
   pkg repo signing-key yori-signing-key
   pkg repo . yori-signing-key
   ```

3. **Host repository:**
   ```bash
   # Create repo.conf
   mkdir -p /usr/local/etc/pkg/repos
   cat > /usr/local/etc/pkg/repos/yori.conf << EOF
   yori: {
     url: "https://pkg.yori.dev/FreeBSD:13:amd64/latest",
     enabled: yes
   }
   EOF
   ```

4. **Update and install:**
   ```bash
   pkg update
   pkg install yori
   ```

## Testing

### Test in VM

```bash
# Create OPNsense VM
# SSH to VM
ssh root@opnsense-vm

# Test installer
curl -sSL http://your-dev-machine/install.sh | sh

# Verify
service yori status
ls -la /usr/local/opnsense/mvc/app/controllers/OPNsense/YORI/
```

### Test Package

```bash
# Build package
make -C packaging/freebsd package

# Copy to test VM
scp yori-0.2.0.pkg root@opnsense-vm:/tmp/

# Install
ssh root@opnsense-vm
pkg install /tmp/yori-0.2.0.pkg
```

## Comparison: Current vs. Improved

### Current Process (Manual)

```bash
# 15+ steps, 30-60 minutes
1. Build wheel on dev machine
2. Cross-compile to FreeBSD
3. SCP wheel to OPNsense
4. SSH to OPNsense
5. pkg install python311 py311-pip
6. pip install wheel
7. Create directories
8. Copy config files
9. Copy policy files
10. Create rc.d script
11. Set permissions
12. Edit menu.xml
13. Copy UI files
14. Set more permissions
15. Restart services
```

### With One-Line Installer

```bash
# 1 step, 2-3 minutes
curl -sSL https://get.yori.dev/install.sh | sh
```

### With pkg (Future)

```bash
# 1 step, 1 minute
pkg install os-yori
```

## Next Steps

1. **Short term:** Deploy one-line installer
   - [ ] Build FreeBSD wheel
   - [ ] Upload to GitHub releases
   - [ ] Test installer on clean OPNsense VM
   - [ ] Document in README

2. **Medium term:** Create pkg repository
   - [ ] Set up pkg signing key
   - [ ] Build and sign packages
   - [ ] Host at pkg.yori.dev
   - [ ] Add to OPNsense community plugins

3. **Long term:** Official OPNsense plugin
   - [ ] Submit to OPNsense plugin repository
   - [ ] Follow OPNsense plugin guidelines
   - [ ] Get included in official plugin list
   - [ ] Available via Web UI plugin manager

## Resources

- [FreeBSD Porter's Handbook](https://docs.freebsd.org/en/books/porters-handbook/)
- [OPNsense Plugin Development](https://docs.opnsense.org/development/guidelines.html)
- [pkg Repository Format](https://man.freebsd.org/cgi/man.cgi?query=pkg-repository)
