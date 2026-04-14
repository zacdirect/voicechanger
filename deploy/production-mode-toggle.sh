#!/bin/bash
# Production mode toggle for voicechanger on Raspberry Pi
#
# Switches between graphical (desktop) and headless (production) boot modes.
#
# Usage:
#   sudo ./production-mode-toggle.sh enable   # Boot to headless; auto-start service
#   sudo ./production-mode-toggle.sh disable  # Boot to desktop; manual service start
#
# Effects:
#   Enable:  Sets runlevel 3 (multi-user, no GUI), enables auto-boot to voicechanger systemd target
#   Disable: Sets runlevel 5 (graphical), removes auto-boot target configuration

set -e

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use: sudo $0)" >&2
    exit 1
fi

MODE="${1:-}"

if [[ "$MODE" != "enable" && "$MODE" != "disable" ]]; then
    echo "Usage: $0 {enable|disable}"
    echo ""
    echo "  enable  - Boot to headless (runlevel 3); service auto-starts"
    echo "  disable - Boot to desktop (runlevel 5); manual service start"
    exit 1
fi

VOICECHANGER_SERVICE="voicechanger.service"
GRAPHICAL_TARGET="graphical.target"
MULTI_USER_TARGET="multi-user.target"

if [[ "$MODE" == "enable" ]]; then
    echo "Enabling production (headless) mode..."
    
    # Check if systemd service exists
    if ! systemctl list-unit-files "$VOICECHANGER_SERVICE" >/dev/null 2>&1; then
        echo "ERROR: $VOICECHANGER_SERVICE not found. Install package first." >&2
        exit 1
    fi
    
    # Set service to auto-start on boot
    systemctl enable "$VOICECHANGER_SERVICE"
    echo "✓ Enabled $VOICECHANGER_SERVICE for boot"
    
    # Set boot target to multi-user (headless, runlevel 3)
    systemctl set-default "$MULTI_USER_TARGET"
    echo "✓ Set default target to $MULTI_USER_TARGET (headless)"
    
    # Stop X11 if running (optional; helps on ARM boards with limited resources)
    if systemctl is-active --quiet x11-common 2>/dev/null || systemctl is-active --quiet bluetooth 2>/dev/null; then
        echo "ℹ X11/Bluetooth may still be running; reboot to complete switch"
    fi
    
    echo ""
    echo "✅ Production mode enabled. Reboot to take effect: sudo reboot"
    
elif [[ "$MODE" == "disable" ]]; then
    echo "Disabling production mode (enabling desktop)..."
    
    # Set boot target to graphical (desktop, runlevel 5)
    systemctl set-default "$GRAPHICAL_TARGET"
    echo "✓ Set default target to $GRAPHICAL_TARGET (graphical)"
    
    # Note: Service remains enabled but won't auto-start on boot in graphical mode
    # (unless explicitly added to graphical.target)
    echo "ℹ $VOICECHANGER_SERVICE will not auto-start in desktop mode"
    echo "  Start manually with: sudo systemctl start $VOICECHANGER_SERVICE"
    
    echo ""
    echo "✅ Production mode disabled. Reboot to take effect: sudo reboot"
fi

exit 0
