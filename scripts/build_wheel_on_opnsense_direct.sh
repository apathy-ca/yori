#!/bin/sh
# Build YORI wheel directly on OPNsense
#
# This script temporarily enables the full FreeBSD package repository
# to install Rust, builds the wheel, then cleans up.
#
# Usage (on OPNsense):
#   fetch https://raw.githubusercontent.com/apathy-ca/yori/main/scripts/build_wheel_on_opnsense_direct.sh
#   sh build_wheel_on_opnsense_direct.sh
#
# Alternative manual approach:
#   1. Enable FreeBSD repo: echo 'FreeBSD: { enabled: yes }' > /usr/local/etc/pkg/repos/FreeBSD.conf
#   2. pkg update && pkg install rust python311 py311-sqlite3
#   3. Follow build steps below
#   4. Disable FreeBSD repo: rm /usr/local/etc/pkg/repos/FreeBSD.conf && pkg update

set -e

echo "=== YORI Wheel Builder for OPNsense ==="
echo ""
echo "This will temporarily enable the FreeBSD package repository"
echo "to install Rust compiler, build the wheel, then clean up."
echo ""
printf "Continue? (y/N) "
read REPLY
case "$REPLY" in
    [Yy]|[Yy][Ee][Ss])
        ;;
    *)
        echo "Aborted."
        exit 1
        ;;
esac

YORI_VERSION="${YORI_VERSION:-0.2.0}"
BUILD_DIR="/tmp/yori-build-$$"

echo "[1/7] Detecting system ABI..."
ABI=$(pkg -vv | grep "ABI" | cut -d'"' -f2)
if [ -z "$ABI" ]; then
    # Fallback to common OPNsense ABI
    ABI="FreeBSD:13:amd64"
fi
echo "Detected ABI: $ABI"

echo "[1.5/7] Creating temporary package repository configuration..."
mkdir -p /usr/local/etc/pkg/repos
cat > /usr/local/etc/pkg/repos/FreeBSD-temp.conf << EOF
FreeBSD-temp: {
  url: "pkg+http://pkg.FreeBSD.org/${ABI}/latest",
  enabled: yes,
  priority: 10
}
EOF

echo "[2/7] Updating package repository..."
pkg update || {
    echo "Warning: Failed to update with custom repo, trying alternative..."
    # Try using FreeBSD official repo instead
    cat > /usr/local/etc/pkg/repos/FreeBSD.conf << EOF
FreeBSD: {
  url: "pkg+http://pkg.FreeBSD.org/\${ABI}/latest",
  enabled: yes
}
EOF
    pkg update || {
        echo "Error: Unable to configure FreeBSD package repository"
        echo "Please check your network connection and try again"
        rm -f /usr/local/etc/pkg/repos/FreeBSD-temp.conf
        rm -f /usr/local/etc/pkg/repos/FreeBSD.conf
        exit 1
    }
}

echo "[3/7] Installing build dependencies..."
pkg install -y rust python311 py311-sqlite3

echo "[4/7] Bootstrapping pip and installing maturin..."
python3.11 -m ensurepip
python3.11 -m pip install --upgrade pip maturin

echo "[5/7] Downloading and extracting YORI source..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
fetch "https://github.com/apathy-ca/yori/archive/refs/tags/v${YORI_VERSION}.tar.gz"
tar xzf "v${YORI_VERSION}.tar.gz"
cd "yori-${YORI_VERSION}"

echo "[6/7] Building wheel (this may take 5-10 minutes)..."
maturin build --release

echo "[7/7] Cleaning up..."
rm -f /usr/local/etc/pkg/repos/FreeBSD-temp.conf
rm -f /usr/local/etc/pkg/repos/FreeBSD.conf
pkg update

echo "Note: Rust compiler will remain installed."
echo "To remove it later: pkg delete rust cargo"

echo ""
echo "=== Build Complete! ==="
echo ""
echo "Wheel location:"
ls -lh "$BUILD_DIR/yori-${YORI_VERSION}/target/wheels/"*.whl
echo ""
echo "To install:"
echo "  YORI_WHEEL=\"$BUILD_DIR/yori-${YORI_VERSION}/target/wheels/yori-*.whl\" sh install.sh"
echo ""
echo "Or copy to a permanent location first:"
echo "  cp $BUILD_DIR/yori-${YORI_VERSION}/target/wheels/yori-*.whl /tmp/"
echo "  YORI_WHEEL=/tmp/yori-*.whl sh install.sh"
echo ""
