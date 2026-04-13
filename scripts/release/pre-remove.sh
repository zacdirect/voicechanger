#!/bin/bash
# Pre-removal script for voicechanger Debian package
# Called before package is removed

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

echo "✅ Voicechanger removed"

exit 0
