#!/bin/sh
# Build YORI wheel directly on OPNsense
#
# This script temporarily enables the full FreeBSD package repository
# to install Rust, builds the wheel, then cleans up.
#
# Usage (on OPNsense):
#   fetch https://raw.githubusercontent.com/apathy-ca/yori/main/scripts/build_wheel_on_opnsense_direct.sh
#   sh build_wheel_on_opnsense_direct.sh

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

echo "[1/7] Creating temporary package repository configuration..."
mkdir -p /usr/local/etc/pkg/repos
cat > /usr/local/etc/pkg/repos/FreeBSD-temp.conf << 'EOF'
FreeBSD-temp: {
  url: "pkg+http://pkg.FreeBSD.org/${ABI}/latest",
  enabled: yes,
  priority: 10
}
EOF

echo "[2/7] Updating package repository..."
pkg update

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
pkg update

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
