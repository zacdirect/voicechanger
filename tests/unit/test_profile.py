"""Unit tests for Profile model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from voicechanger.profile import Profile, ProfileValidationError


class TestProfileValidation:
    """Test profile name validation."""

    def test_valid_name(self) -> None:
        p = Profile(name="darth-vader", effects=[])
        assert p.name == "darth-vader"

    def test_valid_name_min_length(self) -> None:
        p = Profile(name="ab", effects=[])
        assert p.name == "ab"

    def test_valid_name_max_length(self) -> None:
        name = "a" + "b" * 62 + "c"  # 64 chars
        p = Profile(name=name, effects=[])
        assert p.name == name

    def test_valid_name_numbers(self) -> None:
        p = Profile(name="profile123", effects=[])
        assert p.name == "profile123"

    def test_invalid_name_uppercase(self) -> None:
        with pytest.raises(ProfileValidationError, match="name"):
            Profile(name="DarthVader", effects=[])

    def test_invalid_name_leading_hyphen(self) -> None:
        with pytest.raises(ProfileValidationError, match="name"):
            Profile(name="-invalid", effects=[])

    def test_invalid_name_trailing_hyphen(self) -> None:
        with pytest.raises(ProfileValidationError, match="name"):
            Profile(name="invalid-", effects=[])

    def test_invalid_name_too_short(self) -> None:
        with pytest.raises(ProfileValidationError, match="name"):
            Profile(name="a", effects=[])

    def test_invalid_name_too_long(self) -> None:
        with pytest.raises(ProfileValidationError, match="name"):
            Profile(name="a" * 66, effects=[])

    def test_invalid_name_spaces(self) -> None:
        with pytest.raises(ProfileValidationError, match="name"):
            Profile(name="has space", effects=[])

    def test_invalid_name_special_chars(self) -> None:
        with pytest.raises(ProfileValidationError, match="name"):
            Profile(name="has_underscore", effects=[])

    def test_reserved_name_check(self) -> None:
        """Reserved names are checked by the registry, not the model."""
        # The Profile model itself doesn't check reserved names
        p = Profile(name="clean", effects=[])
        assert p.name == "clean"


class TestProfileSerialization:
    """Test profile JSON serialization/deserialization."""

    def test_load_valid_json(self, tmp_path: Path, sample_profile_dict: dict[str, Any]) -> None:
        path = tmp_path / "test-profile.json"
        path.write_text(json.dumps(sample_profile_dict))
        profile = Profile.load(path)
        assert profile.name == "test-profile"
        assert profile.author == "tester"
        assert profile.description == "A test profile"
        assert len(profile.effects) == 2

    def test_save_and_reload(self, tmp_path: Path) -> None:
        profile = Profile(
            name="round-trip",
            author="tester",
            description="Test round-trip",
            effects=[{"type": "Gain", "params": {"gain_db": 1.0}}],
        )
        path = tmp_path / "round-trip.json"
        profile.save(path)

        loaded = Profile.load(path)
        assert loaded.name == "round-trip"
        assert loaded.author == "tester"
        assert loaded.effects == [{"type": "Gain", "params": {"gain_db": 1.0}}]

    def test_load_clean_profile(self, tmp_path: Path, clean_profile_dict: dict[str, Any]) -> None:
        path = tmp_path / "clean.json"
        path.write_text(json.dumps(clean_profile_dict))
        profile = Profile.load(path)
        assert profile.name == "clean"
        assert profile.effects == []

    def test_save_produces_valid_json(self, tmp_path: Path) -> None:
        profile = Profile(name="test-json", effects=[])
        path = tmp_path / "test-json.json"
        profile.save(path)
        data = json.loads(path.read_text())
        assert data["schema_version"] == 1
        assert data["name"] == "test-json"
        assert data["effects"] == []

    def test_load_with_schema_version(
        self, tmp_path: Path, sample_profile_dict: dict[str, Any]
    ) -> None:
        sample_profile_dict["schema_version"] = 1
        path = tmp_path / "test-profile.json"
        path.write_text(json.dumps(sample_profile_dict))
        profile = Profile.load(path)
        assert profile.schema_version == 1

    def test_load_future_schema_version_warns(
        self, tmp_path: Path, sample_profile_dict: dict[str, Any]
    ) -> None:
        """Unknown schema_version > current loads with warning."""
        sample_profile_dict["schema_version"] = 99
        path = tmp_path / "test-profile.json"
        path.write_text(json.dumps(sample_profile_dict))
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile = Profile.load(path)
            assert len(w) == 1
            assert "schema_version" in str(w[0].message)
        assert profile.name == "test-profile"


class TestProfileMalformedInput:
    """Test handling of malformed profile files."""

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json at all")
        with pytest.raises(ProfileValidationError):
            Profile.load(path)

    def test_load_missing_name(self, tmp_path: Path) -> None:
        path = tmp_path / "no-name.json"
        path.write_text(json.dumps({"schema_version": 1, "effects": []}))
        with pytest.raises(ProfileValidationError, match="name"):
            Profile.load(path)

    def test_load_missing_effects(self, tmp_path: Path) -> None:
        path = tmp_path / "no-effects.json"
        path.write_text(json.dumps({"schema_version": 1, "name": "test-valid"}))
        with pytest.raises(ProfileValidationError, match="effects"):
            Profile.load(path)

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        path = tmp_path / "does-not-exist.json"
        with pytest.raises(FileNotFoundError):
            Profile.load(path)

    def test_load_effects_not_list(self, tmp_path: Path) -> None:
        path = tmp_path / "bad-effects.json"
        path.write_text(json.dumps({"schema_version": 1, "name": "test-valid", "effects": "nope"}))
        with pytest.raises(ProfileValidationError, match="effects"):
            Profile.load(path)

    def test_load_effect_missing_type(self, tmp_path: Path) -> None:
        path = tmp_path / "bad-effect.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "name": "test-valid",
                    "effects": [{"params": {"gain_db": 1.0}}],
                }
            )
        )
        with pytest.raises(ProfileValidationError, match="type"):
            Profile.load(path)
