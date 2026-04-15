"""Hardware hint registry — maps device names to known-good channel configurations.

Hints are JSON files stored in two directories:
  builtin/  — shipped with the package, covers common hardware (Pi, PipeWire, BT)
  user/     — generated per-install on first discovery of an unknown device pair

Lookup checks user hints first (highest specificity), then builtin hints.
On a miss, the caller probes channel counts and writes a user hint for next time.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


@dataclass
class HardwareHint:
    """Known-good channel configuration for a set of device name patterns."""

    match: list[str]
    num_input_channels: int
    num_output_channels: int
    schema_version: int = CURRENT_SCHEMA_VERSION
    note: str = ""

    def matches(self, *device_names: str | None) -> bool:
        """Return True if any match pattern is a substring of any device name."""
        for pattern in self.match:
            p = pattern.lower()
            for name in device_names:
                if name and p in name.lower():
                    return True
        return False

    @classmethod
    def load(cls, path: Path) -> HardwareHint:
        """Load a hardware hint from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            match=list(data.get("match", [])),
            num_input_channels=int(data["num_input_channels"]),
            num_output_channels=int(data["num_output_channels"]),
            schema_version=int(data.get("schema_version", CURRENT_SCHEMA_VERSION)),
            note=str(data.get("note", "")),
        )

    def save(self, path: Path) -> None:
        """Persist this hint to a JSON file, creating parent dirs as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": self.schema_version,
                    "match": self.match,
                    "num_input_channels": self.num_input_channels,
                    "num_output_channels": self.num_output_channels,
                    "note": self.note,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


class HardwareHintRegistry:
    """Discovers and manages hardware channel hints from builtin and user dirs."""

    def __init__(self, builtin_dir: Path | str, user_dir: Path | str) -> None:
        self._builtin_dir = Path(builtin_dir)
        self._user_dir = Path(user_dir)
        self._builtin: list[HardwareHint] = self._load_dir(self._builtin_dir)
        self._user: list[HardwareHint] = self._load_dir(self._user_dir)

    def _load_dir(self, directory: Path) -> list[HardwareHint]:
        if not directory.exists():
            return []
        hints: list[HardwareHint] = []
        for path in sorted(directory.glob("*.json")):
            try:
                hints.append(HardwareHint.load(path))
            except Exception:
                logger.warning("Failed to load hardware hint from %s, skipping", path)
        return hints

    def lookup(self, in_device: str | None, out_device: str | None) -> tuple[int, int] | None:
        """Return (num_input_channels, num_output_channels) for the first matching hint.

        User hints take precedence over builtin hints.
        Returns None if no hint matches — caller should probe and then write_user_hint.
        """
        for hint in self._user + self._builtin:
            if hint.matches(in_device, out_device):
                logger.debug(
                    "Hardware hint matched for (in=%r, out=%r): in_ch=%d out_ch=%d",
                    in_device, out_device,
                    hint.num_input_channels, hint.num_output_channels,
                )
                return hint.num_input_channels, hint.num_output_channels
        return None

    def write_user_hint(
        self,
        in_device: str | None,
        out_device: str | None,
        num_in: int,
        num_out: int,
    ) -> None:
        """Persist a newly discovered channel config and update in-memory state."""
        slug_source = out_device or in_device or "unknown"
        slug = re.sub(r"[^a-z0-9]+", "-", slug_source.lower()).strip("-")[:48]
        path = self._user_dir / f"{slug}.json"

        match_patterns = [s for s in [in_device, out_device] if s]
        hint = HardwareHint(
            match=match_patterns,
            num_input_channels=num_in,
            num_output_channels=num_out,
            note=(
                f"Discovered automatically for "
                f"input={in_device!r} output={out_device!r}"
            ),
        )
        try:
            hint.save(path)
            self._user.append(hint)
            logger.info("Saved hardware hint to %s (in_ch=%d, out_ch=%d)", path, num_in, num_out)
        except Exception:
            logger.warning("Failed to save hardware hint to %s", path, exc_info=True)
