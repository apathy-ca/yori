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

echo "[1/5] Cross-compiling Rust extension for FreeBSD..."
cross build --release --target x86_64-unknown-freebsd \
    --manifest-path rust/yori-core/Cargo.toml --lib

echo "[2/5] Creating package directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{lib,python,bin,etc,rc.d}

echo "[3/5] Copying files..."
# Copy Rust extension
cp target/x86_64-unknown-freebsd/release/libyori_core.so \
   "$BUILD_DIR/lib/yori_core.so"

# Copy Python code
cp -r python/yori "$BUILD_DIR/python/"

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
cp -r opnsense/src/opnsense "$BUILD_DIR/opnsense/"

echo "[4/5] Creating installation script..."
cat > "$BUILD_DIR/install.sh" << 'INSTALLEOF'
#!/bin/sh
# YORI Installation Script (from pre-built package)
set -e

PREFIX="${PREFIX:-/usr/local}"
YORI_VENV="$PREFIX/yori-venv"

echo "Installing YORI dependencies..."
pkg install -y python311 py311-sqlite3

echo "Creating virtual environment..."
python3.11 -m ensurepip || true
python3.11 -m venv "$YORI_VENV"

echo "Installing YORI..."
# Copy Rust extension to venv
mkdir -p "$YORI_VENV/lib/python3.11/site-packages/yori"
cp lib/yori_core.so "$YORI_VENV/lib/python3.11/site-packages/"

# Copy Python code
cp -r python/yori/* "$YORI_VENV/lib/python3.11/site-packages/yori/"

# Install Python dependencies in venv
"$YORI_VENV/bin/pip" install --upgrade pip
"$YORI_VENV/bin/pip" install \
    fastapi>=0.109.0 \
    "uvicorn[standard]>=0.27.0" \
    httpx>=0.26.0 \
    pydantic>=2.5.0 \
    pyyaml>=6.0 \
    python-multipart>=0.0.6 \
    aiosqlite>=0.19.0 \
    jinja2>=3.1.0

echo "Installing OPNsense UI files..."
cp -r opnsense/* "$PREFIX/opnsense/"
chown -R root:wheel "$PREFIX/opnsense/mvc/app/controllers/OPNsense/YORI"
chown -R root:wheel "$PREFIX/opnsense/mvc/app/models/OPNsense/YORI"
chown -R root:wheel "$PREFIX/opnsense/mvc/app/views/OPNsense/YORI"

echo "Installing configuration..."
mkdir -p "$PREFIX/etc/yori/policies"
mkdir -p /var/db/yori
mkdir -p /var/log/yori
if [ ! -f "$PREFIX/etc/yori/yori.conf" ]; then
    cp etc/yori/yori.conf "$PREFIX/etc/yori/"
fi

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

command="/usr/local/yori-venv/bin/python3.11"
command_args="-m yori.proxy_server --config ${yori_config}"
pidfile="${yori_pidfile}"

start_cmd="${name}_start"
stop_cmd="${name}_stop"

yori_start()
{
    echo "Starting ${name}."
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
