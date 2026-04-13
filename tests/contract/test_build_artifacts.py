"""Contract tests for release build artifacts."""

from __future__ import annotations

import zipfile
from pathlib import Path


def _find_wheel() -> Path | None:
    dist = Path("dist")
    if not dist.exists():
        return None
    wheels = list(dist.glob("*.whl"))
    return wheels[0] if wheels else None


def test_entry_points_present_in_built_wheel() -> None:
    """If a wheel exists locally, it must include expected CLI entry points."""
    wheel = _find_wheel()
    if wheel is None:
        # Contract test is CI-oriented; local runs may not have dist artifacts yet.
        return

    with zipfile.ZipFile(wheel) as zf:
        entry_points_files = [name for name in zf.namelist() if name.endswith("entry_points.txt")]
        assert entry_points_files, "entry_points.txt missing from wheel"
        content = zf.read(entry_points_files[0]).decode("utf-8")

    assert "voicechanger =" in content
    assert "voicechanger-gui =" in content


def test_pedalboard_patch_file_exists() -> None:
    """Release workflow must have pedalboard patch available as an artifact."""
    patches_dir = Path("native/patches")
    patch_files = list(patches_dir.glob("*.patch"))
    assert patch_files, "no pedalboard patch files found in native/patches"
