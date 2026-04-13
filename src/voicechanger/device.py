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

    DEFAULT_LABEL = "Default"
    _HW_MARKER = "Direct hardware device"

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

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def _alsa_subdevice_names(self, *, is_input: bool) -> dict[str, list[str]]:
        devices = self.list_input_devices() if is_input else self.list_output_devices()
        result: dict[str, list[str]] = {}
        for dev in devices:
            card_id = str(dev.get("name", ""))
            sub_name = str(dev.get("device_name", "")).strip()
            if not card_id:
                continue
            result.setdefault(card_id, []).append(sub_name or "Unknown")
        return result

    @staticmethod
    def _stream_names(*, is_input: bool) -> list[str]:
        try:
            from pedalboard.io import AudioStream

            return (
                list(AudioStream.input_device_names)
                if is_input
                else list(AudioStream.output_device_names)
            )
        except Exception:
            logger.warning("Could not enumerate pedalboard AudioStream devices", exc_info=True)
            return []

    @staticmethod
    def _default_stream_name(*, is_input: bool) -> str:
        try:
            from pedalboard.io import AudioStream

            return (
                str(AudioStream.default_input_device_name)
                if is_input
                else str(AudioStream.default_output_device_name)
            )
        except Exception:
            return ""

    @classmethod
    def default_input_name(cls) -> str:
        try:
            names = cls._stream_names(is_input=True)
            default_name = cls._default_stream_name(is_input=True)

            if default_name in names and "output" not in default_name.lower():
                return default_name

            for candidate in names:
                lower = candidate.lower()
                if "pipewire sound server" in lower:
                    return candidate

            for candidate in names:
                lower = candidate.lower()
                if "direct hardware device" in lower and "output" not in lower:
                    return candidate

            return names[0] if names else default_name
        except Exception:
            return ""

    @classmethod
    def default_output_name(cls) -> str:
        try:
            names = cls._stream_names(is_input=False)
            default_name = cls._default_stream_name(is_input=False)

            if default_name in names and "input" not in default_name.lower():
                return default_name

            for candidate in names:
                if "pipewire sound server" in candidate.lower():
                    return candidate

            for candidate in names:
                if "direct hardware device" in candidate.lower():
                    return candidate

            return names[0] if names else default_name
        except Exception:
            return ""

    def _build_device_tree(self, *, is_input: bool) -> dict[str, list[tuple[str, str]]]:
        juce_names = self._stream_names(is_input=is_input)
        alsa_names = self._alsa_subdevice_names(is_input=is_input)

        hw_by_card: dict[str, list[str]] = {}
        for raw in juce_names:
            if self._HW_MARKER not in raw:
                continue
            card_label = raw.split(",", maxsplit=1)[0].strip()
            hw_by_card.setdefault(card_label, []).append(raw)

        tree: dict[str, list[tuple[str, str]]] = {}
        for card_label, raws in hw_by_card.items():
            matched_names: list[str] = []
            norm_card = self._normalize(card_label)
            for alsa_card, names in alsa_names.items():
                norm_alsa = self._normalize(alsa_card)
                if norm_alsa in norm_card or norm_card in norm_alsa:
                    matched_names = names
                    break

            entries: list[tuple[str, str]] = []
            for idx, raw_name in enumerate(raws):
                sub_label = matched_names[idx] if idx < len(matched_names) else f"Device {idx + 1}"
                entries.append((sub_label, raw_name))
            tree[card_label] = entries

        return tree

    def input_device_tree(self) -> dict[str, list[tuple[str, str]]]:
        return self._build_device_tree(is_input=True)

    def output_device_tree(self) -> dict[str, list[tuple[str, str]]]:
        return self._build_device_tree(is_input=False)

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
