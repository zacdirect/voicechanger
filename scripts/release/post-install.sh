#!/bin/bash
# Post-installation script for voicechanger Debian package
# Called after package is installed

set -e

echo "Configuring voicechanger..."

# Create dedicated user and group if they don't exist
if ! getent group audio > /dev/null; then
    echo "Creating audio group..."
    groupadd -r audio || true
fi

if ! id -u voicechanger > /dev/null 2>&1; then
    echo "Creating voicechanger user..."
    useradd -r -s /usr/sbin/nologin -M -c "Voice Changer service" voicechanger || true
fi

# Add voicechanger user to audio group
usermod -aG audio voicechanger || true

# Create config directory if it doesn't exist
mkdir -p /etc/voicechanger
mkdir -p /var/lib/voicechanger

# Set permissions
chown -R voicechanger:audio /var/lib/voicechanger 2>/dev/null || true
chmod 755 /etc/voicechanger
chmod 755 /var/lib/voicechanger

# Enable systemd service
if command -v systemctl > /dev/null; then
    echo "Enabling voicechanger service..."
    systemctl daemon-reload || true
    systemctl enable voicechanger.service 2>/dev/null || true
fi

echo "✅ Voicechanger installed successfully"
echo ""
echo "Next steps:"
echo "  1. Configure audio device: voicechanger list-devices"
echo "  2. Select input device:    voicechanger set-device input <device-id>"
echo "  3. Start service:         sudo systemctl start voicechanger"
echo ""
echo "For GUI, run: voicechanger-gui"
echo "For production (headless) mode: sudo voicechanger production-mode enable"

exit 0
