#!/bin/bash
# Pre-removal script for voicechanger Debian package

set -e

echo "Removing voicechanger..."

# Stop service if running
if command -v systemctl > /dev/null; then
    echo "Stopping voicechanger service..."
    systemctl stop voicechanger.service 2>/dev/null || true
    systemctl disable voicechanger.service 2>/dev/null || true
fi

# Clean up runtime files
rm -f /run/voicechanger/*.sock 2>/dev/null || true
rm -rf /opt/voicechanger 2>/dev/null || true

echo "✅ Voicechanger removed"

exit 0
