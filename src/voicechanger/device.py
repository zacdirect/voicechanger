"""Audio device enumeration via ALSA utilities."""

from __future__ import annotations

import logging
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

_CARD_RE = re.compile(r"^card\s+(\d+):\s+(\w+)\s+\[(.+?)\],\s+device\s+(\d+):\s+(.+?)\s+\[(.+?)\]")


def _run_command(cmd: list[str]) -> str:
    """Run a subprocess command and return stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        logger.warning("Failed to run %s", " ".join(cmd))
        return ""


def _parse_device_lines(output: str) -> list[dict[str, Any]]:
    """Parse card lines from aplay/arecord output."""
    devices: list[dict[str, Any]] = []
    for line in output.splitlines():
        match = _CARD_RE.match(line)
        if match:
            devices.append({
                "card": int(match.group(1)),
                "name": match.group(2),
                "card_description": match.group(3),
                "device": int(match.group(4)),
                "device_name": match.group(5),
                "device_description": match.group(6),
            })
    return devices


def parse_aplay_output(output: str) -> list[dict[str, Any]]:
    """Parse output of `aplay -l`."""
    return _parse_device_lines(output)


def parse_arecord_output(output: str) -> list[dict[str, Any]]:
    """Parse output of `arecord -l`."""
    return _parse_device_lines(output)


class DeviceMonitor:
    """Enumerates and monitors audio devices."""

    def __init__(
        self,
        preferred_input: str = "",
        preferred_output: str = "",
    ) -> None:
        self._preferred_input = preferred_input
        self._preferred_output = preferred_output

    def list_input_devices(self) -> list[dict[str, Any]]:
        output = _run_command(["arecord", "-l"])
        return parse_arecord_output(output)

    def list_output_devices(self) -> list[dict[str, Any]]:
        output = _run_command(["aplay", "-l"])
        return parse_aplay_output(output)

    def has_preferred_input(self) -> bool:
        if not self._preferred_input:
            return False
        devices = self.list_input_devices()
        return any(self._preferred_input in d.get("name", "") for d in devices)

    def has_preferred_output(self) -> bool:
        if not self._preferred_output:
            return False
        devices = self.list_output_devices()
        return any(self._preferred_output in d.get("name", "") for d in devices)
