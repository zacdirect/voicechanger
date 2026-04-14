#!/bin/bash
# Post-installation script for voicechanger Debian package
# Called after package files are unpacked to the filesystem.
#
# Creates a virtualenv under /opt/voicechanger/venv and installs the
# bundled wheels (voicechanger + patched pedalboard) so nothing is
# compiled on the target device.

set -e

INSTALL_DIR=/opt/voicechanger

echo "Configuring voicechanger..."

# ── System user / group ──
if ! id -u voicechanger > /dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -M -c "Voice Changer service" voicechanger || true
fi
usermod -aG audio voicechanger || true

# ── Config & state directories ──
mkdir -p /etc/voicechanger /var/lib/voicechanger
chown -R voicechanger:audio /var/lib/voicechanger 2>/dev/null || true

# ── Virtual environment + wheel install ──
# VOICECHANGER_PYTHON is set by the .deb post-install wrapper to the
# exact interpreter that matches the bundled wheels (e.g. python3.14).
PYTHON="${VOICECHANGER_PYTHON:-python3}"
echo "Creating virtualenv with $PYTHON..."
"$PYTHON" -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/venv/bin/pip" install --no-index --find-links "$INSTALL_DIR/wheels" \
    "$INSTALL_DIR/wheels"/voicechanger-*.whl \
    "$INSTALL_DIR/wheels"/pedalboard-*.whl 2>/dev/null \
  || "$INSTALL_DIR/venv/bin/pip" install --no-index --find-links "$INSTALL_DIR/wheels" \
    "$INSTALL_DIR/wheels"/voicechanger-*.whl

# ── Enable systemd service ──
if command -v systemctl > /dev/null; then
    systemctl daemon-reload || true
    systemctl enable voicechanger.service 2>/dev/null || true
fi

echo ""
echo "✅ Voicechanger installed successfully"
echo ""
echo "Next steps:"
echo "  1. List audio devices:  voicechanger list-devices"
echo "  2. Select input device: voicechanger set-device input <device>"
echo "  3. Start service:       sudo systemctl start voicechanger"
echo "  4. GUI (desktop):       voicechanger-gui"
