#!/bin/sh
# Build YORI wheel on OPNsense/FreeBSD
#
# Usage:
#   scp scripts/build_on_opnsense.sh root@opnsense:/tmp/
#   scp -r ../sark root@opnsense:/tmp/  # Include SARK dependencies
#   scp -r . root@opnsense:/tmp/yori/
#   ssh root@opnsense "sh /tmp/build_on_opnsense.sh"

set -e

echo "=== YORI FreeBSD Build Script ==="

# Install dependencies
echo "[1/5] Installing build dependencies..."
pkg install -y rust python311 py311-sqlite3

# Bootstrap pip if not present
if ! python3.11 -m pip --version >/dev/null 2>&1; then
    echo "Bootstrapping pip..."
    python3.11 -m ensurepip
    python3.11 -m pip install --upgrade pip
fi

# Install maturin
echo "[2/5] Installing maturin..."
python3.11 -m pip install --upgrade maturin

# Build the wheel
echo "[3/5] Building YORI wheel..."
cd /tmp/yori
maturin build --release

# Show results
echo "[4/5] Build complete!"
ls -lh target/wheels/

echo "[5/5] Wheel ready for installation:"
echo "  pip install target/wheels/yori-*.whl"
