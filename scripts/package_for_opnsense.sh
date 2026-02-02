#!/bin/bash
# Package YORI for OPNsense deployment
#
# This script cross-compiles the Rust extension and packages everything
# into a tarball that can be extracted directly on OPNsense.
#
# Usage:
#   ./scripts/package_for_opnsense.sh

set -e

VERSION="0.2.0"
PACKAGE_NAME="yori-${VERSION}-freebsd-amd64"
BUILD_DIR="dist/${PACKAGE_NAME}"

echo "=== YORI OPNsense Packager ==="
echo ""

# Check for cross
if ! command -v cross &> /dev/null; then
    echo "Error: 'cross' not found"
    echo "Install: cargo install cross"
    exit 1
fi

echo "[1/5] Cross-compiling Rust components for FreeBSD..."
echo "Building yori-proxy binary (pure Rust - no Python dependencies)..."
cross build --release --target x86_64-unknown-freebsd -p yori-proxy

echo "[2/5] Creating package directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{python,bin,etc,rc.d}

echo "[3/5] Copying files..."
# Copy Rust binary (main proxy server)
mkdir -p "$BUILD_DIR/bin"
cp target/x86_64-unknown-freebsd/release/yori-proxy \
   "$BUILD_DIR/bin/"

# Copy Python code (for optional Python-based management tools, if needed)
# Note: The main proxy is pure Rust and doesn't require Python
cp -r python/yori "$BUILD_DIR/python/" 2>/dev/null || echo "Python code not found (optional)"

# Create requirements.txt (for reference, not used in install)
cat > "$BUILD_DIR/requirements.txt" << 'REQEOF'
# YORI Python Dependencies
# Core dependencies (pure Python, no compilation needed):
pyyaml>=6.0
aiosqlite>=0.19.0
jinja2>=3.1.0

# Optional dependencies (may not be available on FreeBSD without Rust):
# fastapi, uvicorn, pydantic, httpx
# YORI can run in minimal mode without these
REQEOF

# Copy example config
mkdir -p "$BUILD_DIR/etc/yori/policies"
if [ -f examples/yori.conf.example ]; then
    cp examples/yori.conf.example "$BUILD_DIR/etc/yori/yori.conf"
elif [ -f yori.conf.example ]; then
    cp yori.conf.example "$BUILD_DIR/etc/yori/yori.conf"
else
    # Create minimal default config
    cat > "$BUILD_DIR/etc/yori/yori.conf" << 'CONFEOF'
# YORI Configuration
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

enforcement:
  enabled: false
  consent_accepted: false
CONFEOF
fi

# Copy OPNsense UI files
mkdir -p "$BUILD_DIR/opnsense"
if [ -d opnsense/src/opnsense ]; then
    cp -r opnsense/src/opnsense/* "$BUILD_DIR/opnsense/"
else
    echo "Warning: OPNsense UI files not found"
fi

echo "[4/5] Creating installation script..."
cat > "$BUILD_DIR/install.sh" << 'INSTALLEOF'
#!/bin/sh
# YORI Installation Script (from pre-built package)
set -e

PREFIX="${PREFIX:-/usr/local}"
YORI_VENV="$PREFIX/yori-venv"

# Check if YORI is already installed
if [ -f "$PREFIX/bin/yori-proxy" ] || [ -d "$YORI_VENV" ]; then
    echo "═══════════════════════════════════════════"
    echo "Existing YORI installation detected"
    echo "═══════════════════════════════════════════"

    if [ -f "$PREFIX/bin/yori-proxy" ]; then
        CURRENT_VERSION=$("$PREFIX/bin/yori-proxy" --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
        echo "Installed version: $CURRENT_VERSION"
    fi

    echo ""
    echo "Upgrade options:"
    echo "  1. Upgrade (keep config, backup database)"
    echo "  2. Clean install (wipe everything)"
    echo ""
    printf "Choose [1-2] or Ctrl+C to cancel: "
    read UPGRADE_CHOICE

    case "$UPGRADE_CHOICE" in
        1)
            echo "Performing upgrade..."
            # Stop service
            service yori stop 2>/dev/null || true

            # Backup database and config
            if [ -f /var/db/yori/audit.db ]; then
                echo "Backing up database..."
                cp /var/db/yori/audit.db /var/db/yori/audit.db.bak.$(date +%Y%m%d-%H%M%S)
            fi
            ;;
        2)
            echo "Performing clean install..."
            service yori stop 2>/dev/null || true
            rm -rf "$YORI_VENV"
            rm -rf "$PREFIX/bin/yori-proxy"
            rm -rf /var/db/yori
            rm -rf /var/log/yori
            echo "Old installation removed."
            ;;
        *)
            echo "Invalid choice. Exiting."
            exit 1
            ;;
    esac
    echo ""
fi

# Check if Python is already installed (it should be on OPNsense)
echo "Checking for Python 3.11..."
if ! python3.11 --version >/dev/null 2>&1; then
    echo "Error: Python 3.11 not found."
    echo "OPNsense should have Python pre-installed."
    echo "Please install manually: pkg install python311"
    exit 1
fi

echo "Python 3.11 found: $(python3.11 --version)"
echo "Note: Skipping pkg operations to avoid system conflicts."
echo "All dependencies are bundled in this package."

echo "Creating virtual environment..."
python3.11 -m ensurepip || true
python3.11 -m venv "$YORI_VENV"

echo "Installing YORI..."

# Upgrade pip in venv
"$YORI_VENV/bin/pip" install --upgrade pip

# Clear pip cache to avoid corruption
rm -rf /root/.cache/pip 2>/dev/null || true

# Install minimal Python dependencies (no compiled extensions)
echo "Installing Python dependencies..."
"$YORI_VENV/bin/pip" install --no-cache-dir pyyaml aiosqlite jinja2 || {
    echo "Error: Failed to install basic dependencies"
    exit 1
}

# Try to install optional web framework dependencies (may fail on FreeBSD)
echo "Attempting to install optional web framework dependencies..."
"$YORI_VENV/bin/pip" install --no-cache-dir --only-binary :all: \
    starlette httpx anyio 2>/dev/null || {
    echo "Note: Web framework dependencies not available, will use minimal mode"
}

# Copy Python code (optional - the Rust binary is the main proxy)
if [ -d python/yori ]; then
    mkdir -p "$YORI_VENV/lib/python3.11/site-packages/yori"
    cp -r python/yori/* "$YORI_VENV/lib/python3.11/site-packages/yori/"
    echo "Python management tools installed (optional)"
else
    echo "Skipping Python tools (not found - Rust binary is sufficient)"
fi

echo "Installing OPNsense UI files..."
# Create OPNsense MVC directory structure if it doesn't exist
mkdir -p "$PREFIX/opnsense/mvc/app/controllers/OPNsense"
mkdir -p "$PREFIX/opnsense/mvc/app/models/OPNsense"
mkdir -p "$PREFIX/opnsense/mvc/app/views/OPNsense"

# Copy UI files
cp -r opnsense/* "$PREFIX/opnsense/" 2>/dev/null || true

# Set permissions if directories were created
if [ -d "$PREFIX/opnsense/mvc/app/controllers/OPNsense/YORI" ]; then
    chown -R root:wheel "$PREFIX/opnsense/mvc/app/controllers/OPNsense/YORI"
fi
if [ -d "$PREFIX/opnsense/mvc/app/models/OPNsense/YORI" ]; then
    chown -R root:wheel "$PREFIX/opnsense/mvc/app/models/OPNsense/YORI"
fi
if [ -d "$PREFIX/opnsense/mvc/app/views/OPNsense/YORI" ]; then
    chown -R root:wheel "$PREFIX/opnsense/mvc/app/views/OPNsense/YORI"
fi

echo "Installing configuration..."
mkdir -p "$PREFIX/etc/yori/policies"
mkdir -p /var/db/yori
mkdir -p /var/log/yori

# Backup existing config if it exists
if [ -f "$PREFIX/etc/yori/yori.conf" ]; then
    echo "Existing configuration found, creating backup..."
    cp "$PREFIX/etc/yori/yori.conf" "$PREFIX/etc/yori/yori.conf.bak.$(date +%Y%m%d-%H%M%S)"
    echo "Config backed up to yori.conf.bak.*"
else
    echo "Installing default configuration..."
    cp etc/yori/yori.conf "$PREFIX/etc/yori/"
fi

echo "Installing Rust proxy binary..."
mkdir -p "$PREFIX/bin"
cp bin/yori-proxy "$PREFIX/bin/"
chmod +x "$PREFIX/bin/yori-proxy"

echo "Installing rc.d service..."
cat > "$PREFIX/etc/rc.d/yori" << 'RCEOF'
#!/bin/sh
# PROVIDE: yori
# REQUIRE: LOGIN NETWORKING
# KEYWORD: shutdown

. /etc/rc.subr

name=yori
rcvar=yori_enable

load_rc_config $name

: ${yori_enable:="NO"}
: ${yori_config:="/usr/local/etc/yori/yori.conf"}
: ${yori_pidfile:="/var/run/yori.pid"}
: ${yori_log:="/var/log/yori/yori.log"}

command="/usr/local/bin/yori-proxy"
command_args="--config ${yori_config}"
pidfile="${yori_pidfile}"

start_cmd="${name}_start"
stop_cmd="${name}_stop"

yori_start()
{
    echo "Starting ${name} (Rust proxy - maximum performance)."
    /usr/sbin/daemon -p ${pidfile} ${command} ${command_args} >> ${yori_log} 2>&1
}

yori_stop()
{
    if [ -f ${pidfile} ]; then
        echo "Stopping ${name}."
        kill $(cat ${pidfile})
        rm -f ${pidfile}
    fi
}

run_rc_command "$1"
RCEOF

chmod +x "$PREFIX/etc/rc.d/yori"

# Enable service
sysrc yori_enable="YES"

# Clear OPNsense cache
rm -rf "$PREFIX/opnsense/mvc/app/cache/"*
service configd restart 2>/dev/null || true

echo ""
echo "=== Installation Complete! ==="
echo "YORI has been installed to $YORI_VENV"
echo ""
echo "To start: service yori start"
echo "Config: $PREFIX/etc/yori/yori.conf"
INSTALLEOF

chmod +x "$BUILD_DIR/install.sh"

echo "[5/5] Creating tarball..."
cd dist
tar czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
cd ..

echo ""
echo "=== Package Complete! ==="
echo ""
echo "Package: dist/${PACKAGE_NAME}.tar.gz"
echo "Size: $(du -h "dist/${PACKAGE_NAME}.tar.gz" | cut -f1)"
echo ""
echo "To install on OPNsense:"
echo "  1. Copy to OPNsense:"
echo "     scp dist/${PACKAGE_NAME}.tar.gz root@opnsense:/tmp/"
echo ""
echo "  2. On OPNsense:"
echo "     cd /tmp"
echo "     tar xzf ${PACKAGE_NAME}.tar.gz"
echo "     cd ${PACKAGE_NAME}"
echo "     sh install.sh"
echo ""
