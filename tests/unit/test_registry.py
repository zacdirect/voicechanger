"""Unit tests for ProfileRegistry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from voicechanger.profile import Profile
from voicechanger.registry import ProfileRegistry


class TestProfileDiscovery:
    """Test profile discovery from directories."""

    def test_discovers_builtin_profiles(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        names = registry.list()
        assert "clean" in names
        assert "high-pitched" in names
        assert "low-pitched" in names

    def test_discovers_user_profiles(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        user_dir = tmp_profiles["user"]
        user_profile = {
            "schema_version": 1,
            "name": "custom",
            "author": "user",
            "description": "Custom profile",
            "effects": [{"type": "Gain", "params": {"gain_db": 1.0}}],
        }
        (user_dir / "custom.json").write_text(json.dumps(user_profile))

        registry = ProfileRegistry(builtin_dir=builtin_profiles, user_dir=user_dir)
        names = registry.list()
        assert "custom" in names

    def test_empty_dirs(self, tmp_profiles: dict[str, Path]) -> None:
        registry = ProfileRegistry(
            builtin_dir=tmp_profiles["builtin"], user_dir=tmp_profiles["user"]
        )
        assert registry.list() == []


class TestProfileGet:
    """Test getting profiles by name."""

    def test_get_existing_profile(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = registry.get("clean")
        assert profile is not None
        assert profile.name == "clean"

    def test_get_nonexistent_profile(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        assert registry.get("nonexistent") is None


class TestProfileCreate:
    """Test creating user profiles."""

    def test_create_user_profile(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = Profile(name="my-voice", effects=[{"type": "Gain", "params": {"gain_db": 2.0}}])
        registry.create(profile)
        assert registry.exists("my-voice")
        assert (tmp_profiles["user"] / "my-voice.json").exists()

    def test_create_rejects_builtin_name(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = Profile(name="clean", effects=[])
        with pytest.raises(ValueError, match="built-in"):
            registry.create(profile)

    def test_create_rejects_name_collision(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = Profile(name="my-voice", effects=[])
        registry.create(profile)
        with pytest.raises(ValueError, match="exists"):
            registry.create(profile)


class TestProfileDelete:
    """Test deleting user profiles."""

    def test_delete_user_profile(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = Profile(name="to-delete", effects=[])
        registry.create(profile)
        assert registry.exists("to-delete")
        registry.delete("to-delete")
        assert not registry.exists("to-delete")

    def test_delete_builtin_rejected(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        with pytest.raises(ValueError, match="built-in"):
            registry.delete("clean")

    def test_delete_nonexistent(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        with pytest.raises(ValueError, match="not found"):
            registry.delete("nonexistent")


class TestBuiltinProtection:
    """Test that built-in profiles are protected."""

    def test_is_builtin(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        assert registry.is_builtin("clean")
        assert registry.is_builtin("high-pitched")
        assert not registry.is_builtin("nonexistent")


class TestProfileUpdate:
    """Test updating user profiles."""

    def test_update_user_profile(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = Profile(name="my-voice", effects=[{"type": "Gain", "params": {"gain_db": 1.0}}])
        registry.create(profile)

        updated = Profile(
            name="my-voice",
            effects=[{"type": "Gain", "params": {"gain_db": 5.0}}],
            author="tester",
        )
        registry.update(updated)

        result = registry.get("my-voice")
        assert result is not None
        assert result.effects[0]["params"]["gain_db"] == 5.0
        assert result.author == "tester"

    def test_update_persists_to_disk(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = Profile(name="my-voice", effects=[{"type": "Gain", "params": {"gain_db": 1.0}}])
        registry.create(profile)

        updated = Profile(name="my-voice", effects=[{"type": "Gain", "params": {"gain_db": 9.0}}])
        registry.update(updated)

        # Reload from disk
        registry2 = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        result = registry2.get("my-voice")
        assert result is not None
        assert result.effects[0]["params"]["gain_db"] == 9.0

    def test_update_rejects_builtin(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        with pytest.raises(ValueError, match="built-in"):
            registry.update(Profile(name="clean", effects=[]))

    def test_update_rejects_nonexistent(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        with pytest.raises(ValueError, match="not found"):
            registry.update(Profile(name="missing-profile", effects=[]))
