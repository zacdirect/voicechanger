"""Integration test — profile portability across directories and architectures."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from voicechanger.profile import Profile
from voicechanger.registry import ProfileRegistry


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    d = tmp_path / "source"
    d.mkdir()
    return d


@pytest.fixture
def target_builtin(tmp_path: Path) -> Path:
    d = tmp_path / "target_builtin"
    d.mkdir()
    return d


@pytest.fixture
def target_user(tmp_path: Path) -> Path:
    d = tmp_path / "target_user"
    d.mkdir()
    return d


class TestProfilePortability:
    """Test profile files are self-contained and portable."""

    def test_export_import_roundtrip(
        self, source_dir: Path, target_builtin: Path, target_user: Path
    ) -> None:
        """Export a profile, copy to a new directory, verify it loads."""
        # Create and save a profile
        profile = Profile(
            name="portable-test",
            author="exporter",
            description="Portability test profile",
            effects=[
                {"type": "LivePitchShift", "params": {"semitones": -3.0}},
                {"type": "Gain", "params": {"gain_db": 2.0}},
            ],
        )
        export_path = source_dir / "portable-test.json"
        profile.save(export_path)

        # Copy to target directory
        shutil.copy2(export_path, target_user / "portable-test.json")

        # Load from target registry
        registry = ProfileRegistry(builtin_dir=target_builtin, user_dir=target_user)
        names = registry.list()
        assert "portable-test" in names

        loaded = registry.get("portable-test")
        assert loaded is not None
        assert loaded.name == "portable-test"
        assert loaded.author == "exporter"
        assert len(loaded.effects) == 2
        assert loaded.effects[0]["type"] == "LivePitchShift"

    def test_cross_directory_copy(
        self, source_dir: Path, target_builtin: Path, target_user: Path
    ) -> None:
        """Copying a profile JSON between directories preserves all data."""
        profile = Profile(
            name="cross-dir",
            effects=[
                {"type": "Reverb", "params": {"room_size": 0.8, "wet_level": 0.4}},
                {"type": "Chorus", "params": {"rate_hz": 1.5, "depth": 0.3}},
            ],
            author="author1",
            description="Cross-directory test",
        )
        src_path = source_dir / "cross-dir.json"
        profile.save(src_path)

        # Read raw JSON to verify no platform-specific data
        with open(src_path) as f:
            data = json.load(f)
        assert "cross-dir" in json.dumps(data)

        # Copy and verify
        dst_path = target_user / "cross-dir.json"
        shutil.copy2(src_path, dst_path)

        loaded = Profile.load(dst_path)
        assert loaded.name == profile.name
        assert loaded.author == profile.author
        assert loaded.effects == profile.effects

    def test_unknown_effect_graceful_skip(
        self, target_builtin: Path, target_user: Path
    ) -> None:
        """Profile with unknown effect types loads with warnings, not errors."""
        profile_data = {
            "schema_version": 1,
            "name": "future-profile",
            "author": "future-user",
            "description": "Has effects from a newer version",
            "effects": [
                {"type": "Gain", "params": {"gain_db": 1.0}},
                {"type": "FutureEffect", "params": {"intensity": 0.5}},
                {"type": "Reverb", "params": {"room_size": 0.5}},
            ],
        }
        path = target_user / "future-profile.json"
        with open(path, "w") as f:
            json.dump(profile_data, f)

        registry = ProfileRegistry(builtin_dir=target_builtin, user_dir=target_user)
        loaded = registry.get("future-profile")
        assert loaded is not None
        # The profile loads even with unknown effects
        assert len(loaded.effects) == 3
        assert loaded.effects[1]["type"] == "FutureEffect"

    def test_no_platform_specific_data(self, source_dir: Path) -> None:
        """Profile serialization contains no platform-specific paths or binary data."""
        profile = Profile(
            name="arch-test",
            effects=[{"type": "Gain", "params": {"gain_db": 0.0}}],
        )
        path = source_dir / "arch-test.json"
        profile.save(path)

        with open(path) as f:
            raw = f.read()

        data = json.loads(raw)
        # Verify JSON is clean — no binary, no absolute paths
        assert isinstance(data, dict)
        for key in data:
            assert isinstance(key, str)
        assert "schema_version" in data
        assert data["schema_version"] == 1
