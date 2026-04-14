#!/bin/bash
# Post-installation script for voicechanger Debian package.
# Creates system user/group and enables the systemd service.
# All Python packages are pre-installed under /opt/voicechanger/lib
# by the build process — no pip or venv needed.

set -e

echo "Configuring voicechanger..."

# ── System user / group ──
if ! id -u voicechanger > /dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -M -c "Voice Changer service" voicechanger || true
fi
usermod -aG audio voicechanger || true

# ── Config & state directories ──
mkdir -p /etc/voicechanger /var/lib/voicechanger
chown -R voicechanger:audio /var/lib/voicechanger 2>/dev/null || true

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
