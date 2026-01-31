#!/bin/bash
# Build YORI wheel for FreeBSD using cross-compilation
#
# This script builds a FreeBSD wheel on a Linux development machine
# using the 'cross' tool for cross-compilation.
#
# Prerequisites:
#   - Docker (for cross)
#   - cross: cargo install cross
#
# Usage:
#   ./scripts/build_freebsd_wheel.sh

set -e

echo "=== YORI FreeBSD Wheel Builder ==="
echo ""

# Check for cross
if ! command -v cross &> /dev/null; then
    echo "Error: 'cross' not found"
    echo "Install: cargo install cross"
    exit 1
fi

# Check for docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found"
    echo "cross requires Docker to run FreeBSD cross-compilation containers"
    exit 1
fi

echo "Building Rust library for FreeBSD..."
cross build --release --target x86_64-unknown-freebsd \
    --manifest-path rust/yori-core/Cargo.toml --lib

echo ""
echo "Rust library built successfully:"
ls -lh target/x86_64-unknown-freebsd/release/libyori_core.*

echo ""
echo "=== Building Python Wheel ==="
echo ""
echo "NOTE: maturin doesn't support using cross-compiled libraries directly."
echo "The Rust library was built, but creating the wheel requires maturin"
echo "to be run on a FreeBSD system."
echo ""
echo "Next steps:"
echo "  1. Copy source to FreeBSD system (or FreeBSD VM)"
echo "  2. Run: maturin build --release"
echo ""
echo "Or use the pre-compiled Rust library and package manually."
echo ""
echo "For now, the best approach is to build on a FreeBSD VM."
echo "See: scripts/build_on_opnsense.sh for the build commands."
