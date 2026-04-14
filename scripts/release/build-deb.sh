#!/bin/bash
# Build Debian package for voicechanger
#
# Usage:
#   ./build-deb.sh [--install-dir /tmp/voicechanger-deb]
#
# Creates a .deb package suitable for installation on Ubuntu 22.04+ and Raspberry Pi OS
# Generates both wheel and deb formats.

set -e

ARCH=${1:-$(dpkg --print-architecture)}
INSTALL_DIR=${2:-.}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Building Debian package for arch: $ARCH"
echo "Install directory: $INSTALL_DIR"
cd "$PROJECT_ROOT"

# Ensure we have the necessary build tools
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found" >&2
    exit 1
fi

if ! python3 -m pip show build &> /dev/null; then
    echo "Installing build tool..."
    python3 -m pip install --user build
fi

# Build wheel first
echo "Building wheel..."
python3 -m build --wheel --outdir dist/

# Convert wheel to deb using fpm (if available) or setuptools bdist_deb
if command -v fpm &> /dev/null; then
    echo "Building deb package using fpm..."
    
    WHEEL_FILE=$(ls -1 dist/*.whl | head -1)
    WHEEL_NAME=$(basename "$WHEEL_FILE")
    VERSION=$(echo "$WHEEL_NAME" | cut -d'-' -f2)
    
    fpm \
        -s python \
        -t deb \
        --python-bin python3 \
        --python-package-name-template "voicechanger" \
        --depends "python3 (>= 3.11)" \
        --depends "python3-numpy" \
        --depends "python3-flet" \
        --depends "python3-sounddevice" \
        --depends "systemd" \
        --rpm-dist el7 \
        --deb-systemd deploy/voicechanger.service \
        --deb-user voicechanger \
        --deb-group audio \
        --after-install scripts/release/post-install.sh \
        --before-remove scripts/release/pre-remove.sh \
        --description "Real-time voice changer for Raspberry Pi using Pedalboard" \
        --url "https://github.com/example/voicechanger" \
        --maintainer "Your Name <you@example.com>" \
        "$WHEEL_FILE"
    
    echo "✓ Generated deb package"
    
else
    echo "fpm not found, using setuptools bdist_deb..."
    python3 -m pip install wheel setuptools-deb 2>/dev/null || true
    
    python3 setup.py bdist_deb 2>/dev/null || {
        echo "⚠ bdist_deb not available; wheel package generated but deb requires fpm"
        echo "  Install fpm on your system to generate .deb packages"
        exit 1
    }
fi

# Move all artifacts to output directory
mkdir -p "$INSTALL_DIR"
cp dist/*.whl "$INSTALL_DIR/" 2>/dev/null || true
cp dist/*.deb "$INSTALL_DIR/" 2>/dev/null || true

echo ""
echo "✅ Build complete. Artifacts:"
ls -lh "$INSTALL_DIR"/*.{whl,deb} 2>/dev/null || echo "  (wheel and/or deb not found)"
