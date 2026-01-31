#!/bin/sh
# YORI OPNsense Installation Script
# Usage: curl -sSL https://get.yori.dev/install.sh | sh

set -e

YORI_VERSION="${YORI_VERSION:-0.2.0}"
YORI_REPO="apathy-ca/yori"
INSTALL_DIR="/usr/local"
CONFIG_DIR="/usr/local/etc/yori"
DATA_DIR="/var/db/yori"
LOG_DIR="/var/log/yori"

echo "=== YORI v${YORI_VERSION} Installation ==="
echo ""

# Check if running as root
if [ "$(id -u)" != "0" ]; then
   echo "Error: This script must be run as root" 1>&2
   exit 1
fi

# Detect OPNsense
if [ ! -f /usr/local/opnsense/version/core ]; then
    echo "Warning: This doesn't appear to be an OPNsense system"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "[1/8] Installing dependencies..."
pkg install -y python311 py311-sqlite3

# Bootstrap pip if not present
if ! python3.11 -m pip --version >/dev/null 2>&1; then
    echo "Bootstrapping pip..."
    python3.11 -m ensurepip
    python3.11 -m pip install --upgrade pip
fi

echo "[2/8] Downloading YORI package..."
WHEEL_URL="https://github.com/${YORI_REPO}/releases/download/v${YORI_VERSION}/yori-${YORI_VERSION}-cp39-abi3-freebsd_13_x86_64.whl"
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

fetch "$WHEEL_URL" || {
    echo "Error: Failed to download YORI wheel"
    echo "URL: $WHEEL_URL"
    exit 1
}

echo "[3/8] Creating virtual environment..."
python3.11 -m venv /usr/local/yori-venv

echo "[3.5/8] Installing YORI Python package in venv..."
/usr/local/yori-venv/bin/pip install --upgrade pip
/usr/local/yori-venv/bin/pip install yori-*.whl

echo "[4/8] Creating directories..."
mkdir -p "$CONFIG_DIR/policies"
mkdir -p "$DATA_DIR"
mkdir -p "$LOG_DIR"

echo "[5/8] Installing OPNsense UI files..."
OPNSENSE_URL="https://github.com/${YORI_REPO}/archive/refs/tags/v${YORI_VERSION}.tar.gz"
fetch "$OPNSENSE_URL" -o yori-source.tar.gz
tar xzf yori-source.tar.gz
cd "yori-${YORI_VERSION}/opnsense/src"

# Copy MVC files
cp -r opnsense/* "$INSTALL_DIR/opnsense/"

# Set permissions
find "$INSTALL_DIR/opnsense/mvc/app/controllers/OPNsense/YORI" -type f -exec chmod 644 {} \;
find "$INSTALL_DIR/opnsense/mvc/app/models/OPNsense/YORI" -type f -exec chmod 644 {} \;
find "$INSTALL_DIR/opnsense/mvc/app/views/OPNsense/YORI" -type f -exec chmod 644 {} \;
chown -R root:wheel "$INSTALL_DIR/opnsense/mvc/app/controllers/OPNsense/YORI"
chown -R root:wheel "$INSTALL_DIR/opnsense/mvc/app/models/OPNsense/YORI"
chown -R root:wheel "$INSTALL_DIR/opnsense/mvc/app/views/OPNsense/YORI"

echo "[6/8] Installing rc.d service..."
cat > /usr/local/etc/rc.d/yori << 'RCEOF'
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

chmod +x /usr/local/etc/rc.d/yori

echo "[7/8] Creating default configuration..."
if [ ! -f "$CONFIG_DIR/yori.conf" ]; then
    cat > "$CONFIG_DIR/yori.conf" << 'CONFEOF'
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

echo "[8/8] Finalizing installation..."
# Enable service
sysrc yori_enable="YES"

# Clear OPNsense cache
rm -rf /usr/local/opnsense/mvc/app/cache/*

# Restart configd
service configd restart 2>/dev/null || true

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "YORI has been installed successfully."
echo ""
echo "Next steps:"
echo "  1. Access OPNsense web UI"
echo "  2. Go to Services → YORI → Enforcement"
echo "  3. Configure enforcement settings"
echo "  4. Start service: service yori start"
echo ""
echo "Configuration: $CONFIG_DIR/yori.conf"
echo "Logs: $LOG_DIR/"
echo "Data: $DATA_DIR/"
echo ""
echo "For help: https://github.com/${YORI_REPO}"
