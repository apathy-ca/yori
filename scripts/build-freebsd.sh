#!/bin/sh
#
# FreeBSD Cross-Compilation Build Script for YORI
#
# This script builds the yori-core Rust library for FreeBSD (x86_64-unknown-freebsd)
# to run on OPNsense routers.
#
# Requirements:
#   - Rust 1.92+ with FreeBSD target installed
#   - FreeBSD cross-compilation toolchain (optional for linking)
#
# Usage:
#   ./scripts/build-freebsd.sh [--release]
#

set -e  # Exit on error

# Configuration
TARGET="x86_64-unknown-freebsd"
BUILD_TYPE="${1:---release}"
WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==================================================="
echo "YORI FreeBSD Cross-Compilation Build"
echo "==================================================="
echo "Workspace: $WORKSPACE_ROOT"
echo "Target:    $TARGET"
echo "Mode:      $BUILD_TYPE"
echo "==================================================="
echo ""

# Change to workspace root
cd "$WORKSPACE_ROOT"

# Step 1: Ensure FreeBSD target is installed
echo "[1/4] Checking for FreeBSD target..."
if ! rustup target list | grep -q "^${TARGET} (installed)"; then
    echo "Installing FreeBSD target..."
    rustup target add "$TARGET"
else
    echo "FreeBSD target already installed"
fi
echo ""

# Step 2: Build the Rust workspace
echo "[2/4] Building Rust workspace for FreeBSD..."
if [ "$BUILD_TYPE" = "--release" ]; then
    cargo build --release --target "$TARGET" --workspace
    BUILD_DIR="target/${TARGET}/release"
else
    cargo build --target "$TARGET" --workspace
    BUILD_DIR="target/${TARGET}/debug"
fi
echo ""

# Step 3: Check binary size
echo "[3/4] Checking binary size..."
BINARY="${BUILD_DIR}/libyori_core.so"
if [ -f "$BINARY" ]; then
    SIZE_BYTES=$(stat -c%s "$BINARY" 2>/dev/null || stat -f%z "$BINARY" 2>/dev/null || echo "unknown")
    if [ "$SIZE_BYTES" != "unknown" ]; then
        SIZE_MB=$((SIZE_BYTES / 1024 / 1024))
        echo "Binary: $BINARY"
        echo "Size:   ${SIZE_MB}MB (${SIZE_BYTES} bytes)"

        # Check against 10MB target
        if [ "$SIZE_BYTES" -gt 10485760 ]; then
            echo "WARNING: Binary exceeds 10MB target (${SIZE_MB}MB)"
        else
            echo "✓ Binary size within 10MB target"
        fi
    else
        echo "Binary: $BINARY (size unknown)"
    fi
else
    echo "ERROR: Binary not found at $BINARY"
    exit 1
fi
echo ""

# Step 4: Display build artifacts
echo "[4/4] Build artifacts:"
ls -lh "$BUILD_DIR" | grep -E '\.(so|a|rlib)$' || echo "No artifacts found"
echo ""

echo "==================================================="
echo "Build complete!"
echo "==================================================="
echo ""
echo "FreeBSD binary: $BINARY"
echo ""
echo "Next steps:"
echo "  1. Copy binary to OPNsense router:"
echo "     scp $BINARY root@router:/usr/local/lib/python3.11/site-packages/"
echo ""
echo "  2. Test import on FreeBSD:"
echo "     python3.11 -c 'import yori_core; print(yori_core.__version__)'"
echo ""
