"""Unit tests for the hardware hint registry."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from voicechanger.hardware import HardwareHint, HardwareHintRegistry


class TestHardwareHintMatches:
    """Test substring-based device name matching."""

    def test_matches_exact_pattern(self) -> None:
        hint = HardwareHint(
            match=["PipeWire Sound Server"], num_input_channels=1, num_output_channels=2
        )
        assert hint.matches("PipeWire Sound Server") is True

    def test_matches_case_insensitive(self) -> None:
        hint = HardwareHint(match=["pipewire"], num_input_channels=1, num_output_channels=2)
        assert hint.matches("PipeWire Sound Server") is True

    def test_matches_substring(self) -> None:
        hint = HardwareHint(match=["pipewire"], num_input_channels=1, num_output_channels=2)
        assert hint.matches("Default PipeWire Sound Server Output") is True

    def test_matches_any_device_name(self) -> None:
        hint = HardwareHint(match=["bluetooth"], num_input_channels=1, num_output_channels=2)
        # Pattern found in out_device (second arg), not in_device
        assert hint.matches("Some Mic", "Bluetooth Audio Output") is True

    def test_matches_none_device_safe(self) -> None:
        hint = HardwareHint(match=["pipewire"], num_input_channels=1, num_output_channels=2)
        assert hint.matches(None, "PipeWire Sound Server") is True
        assert hint.matches(None, None) is False

    def test_no_match(self) -> None:
        hint = HardwareHint(match=["pipewire"], num_input_channels=1, num_output_channels=2)
        assert hint.matches("USB Audio Device", "HDMI Output") is False

    def test_multiple_patterns_any_matches(self) -> None:
        hint = HardwareHint(
            match=["pipewire", "alsa"],
            num_input_channels=1,
            num_output_channels=2,
        )
        assert hint.matches("ALSA Default") is True


class TestHardwareHintLoadSave:
    """Test JSON serialisation round-trip."""

    def test_load_from_valid_json(self, tmp_path: Path) -> None:
        data = {
            "schema_version": 1,
            "match": ["pipewire"],
            "num_input_channels": 1,
            "num_output_channels": 2,
            "note": "test",
        }
        file = tmp_path / "hint.json"
        file.write_text(json.dumps(data))
        hint = HardwareHint.load(file)
        assert hint.match == ["pipewire"]
        assert hint.num_input_channels == 1
        assert hint.num_output_channels == 2
        assert hint.note == "test"

    def test_save_and_reload(self, tmp_path: Path) -> None:
        hint = HardwareHint(
            match=["bluetooth", "bluez"],
            num_input_channels=1,
            num_output_channels=2,
            note="BT test",
        )
        file = tmp_path / "sub" / "bt.json"
        hint.save(file)
        assert file.exists()

        loaded = HardwareHint.load(file)
        assert loaded.match == ["bluetooth", "bluez"]
        assert loaded.num_input_channels == 1
        assert loaded.num_output_channels == 2
        assert loaded.note == "BT test"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        hint = HardwareHint(match=["x"], num_input_channels=1, num_output_channels=2)
        deep = tmp_path / "a" / "b" / "c" / "hint.json"
        hint.save(deep)
        assert deep.exists()


class TestHardwareHintRegistry:
    """Test registry lookup, precedence, and user-hint persistence."""

    def _make_hint_file(
        self, directory: Path, name: str, match: list[str], num_in: int, num_out: int
    ) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": 1,
            "match": match,
            "num_input_channels": num_in,
            "num_output_channels": num_out,
            "note": "",
        }
        (directory / name).write_text(json.dumps(data))

    def test_lookup_builtin_hit(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._make_hint_file(builtin, "pipewire.json", ["pipewire"], 1, 2)
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)
        result = registry.lookup("PipeWire Sound Server", "PipeWire Sound Server")
        assert result == (1, 2)

    def test_lookup_miss_returns_none(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._make_hint_file(builtin, "pipewire.json", ["pipewire"], 1, 2)
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)
        result = registry.lookup("Unknown USB Device", "Unknown USB Device")
        assert result is None

    def test_user_hint_takes_precedence_over_builtin(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        self._make_hint_file(builtin, "pipewire.json", ["pipewire"], 1, 2)
        # User has a different out channel count for the same device
        self._make_hint_file(user, "pipewire.json", ["pipewire"], 2, 6)
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)
        result = registry.lookup("PipeWire Sound Server", "PipeWire Sound Server")
        assert result == (2, 6)

    def test_empty_dirs_return_no_hints(self, tmp_path: Path) -> None:
        registry = HardwareHintRegistry(
            builtin_dir=tmp_path / "builtin",
            user_dir=tmp_path / "user",
        )
        assert registry.lookup("any", "any") is None

    def test_malformed_hint_file_is_skipped(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        builtin.mkdir()
        (builtin / "bad.json").write_text("not valid json{{{")
        self._make_hint_file(builtin, "good.json", ["pipewire"], 1, 2)
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=tmp_path / "user")
        # Good hint still loaded despite bad file
        result = registry.lookup("PipeWire", "PipeWire")
        assert result == (1, 2)

    def test_write_user_hint_creates_file(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)
        registry.write_user_hint("Mic In", "Stereo Out", num_in=1, num_out=2)
        json_files = list(user.glob("*.json"))
        assert len(json_files) == 1
        data = json.loads(json_files[0].read_text())
        assert data["num_input_channels"] == 1
        assert data["num_output_channels"] == 2
        assert "Stereo Out" in data["match"] or "Mic In" in data["match"]

    def test_write_user_hint_updates_in_memory(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)
        registry.write_user_hint("Mic In", "Stereo Out", num_in=1, num_out=2)
        # Registry now knows about this device without reload
        result = registry.lookup("Stereo Out", "Stereo Out")
        assert result == (1, 2)

    def test_write_user_hint_slug_from_out_device(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)
        registry.write_user_hint(None, "PipeWire Sound Server", num_in=1, num_out=2)
        files = list(user.glob("*.json"))
        assert len(files) == 1
        assert "pipewire" in files[0].name

    def test_write_user_hint_failure_does_not_raise(self, tmp_path: Path) -> None:
        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)
        # Monkey-patch save to fail on the hint object
        with patch.object(HardwareHint, "save", side_effect=OSError("read-only")):
            registry.write_user_hint("In", "Out", num_in=1, num_out=2)
        # No exception raised is the assertion


class TestNegotiateChannelsIntegration:
    """Test _negotiate_channels registry integration (no real subprocess probing)."""

    def test_registry_hit_skips_probe(self, tmp_path: Path) -> None:
        """When registry returns a hit, no subprocess probing should happen."""
        from voicechanger.audio import _channel_cache, _negotiate_channels

        builtin = tmp_path / "builtin"
        user = tmp_path / "user"
        builtin.mkdir()
        data = {
            "schema_version": 1, "match": ["TestDevice"],
            "num_input_channels": 1, "num_output_channels": 2, "note": "",
        }
        (builtin / "test.json").write_text(json.dumps(data))
        registry = HardwareHintRegistry(builtin_dir=builtin, user_dir=user)

        _channel_cache.clear()
        with patch("voicechanger.audio._probe_stream") as mock_probe:
            result = _negotiate_channels("TestDevice", "TestDevice", 48000, 256, registry)

        assert result == (1, 2)
        mock_probe.assert_not_called()

    def test_cache_hit_skips_registry_and_probe(self, tmp_path: Path) -> None:
        """In-memory cache is checked before registry."""
        from voicechanger.audio import _channel_cache, _negotiate_channels

        _channel_cache.clear()
        _channel_cache[("CachedIn", "CachedOut")] = (2, 6)

        registry = MagicMock(spec=HardwareHintRegistry)
        with patch("voicechanger.audio._probe_stream") as mock_probe:
            result = _negotiate_channels("CachedIn", "CachedOut", 48000, 256, registry)

        assert result == (2, 6)
        registry.lookup.assert_not_called()
        mock_probe.assert_not_called()

    def test_probe_result_persisted_to_registry(self, tmp_path: Path) -> None:
        """After probing, write_user_hint is called on a registry miss."""
        from voicechanger.audio import _channel_cache, _negotiate_channels

        _channel_cache.clear()
        registry = MagicMock(spec=HardwareHintRegistry)
        registry.lookup.return_value = None  # cache miss

        with patch("voicechanger.audio._probe_stream", return_value=True):
            result = _negotiate_channels("NewIn", "NewOut", 48000, 256, registry)

        registry.write_user_hint.assert_called_once()
        call_args = registry.write_user_hint.call_args
        # Called as write_user_hint(in_dev, out_dev, num_in=..., num_out=...)
        # Accept both positional and keyword forms
        args, kwargs = call_args
        actual_in = kwargs.get("num_in", args[2] if len(args) > 2 else None)
        actual_out = kwargs.get("num_out", args[3] if len(args) > 3 else None)
        assert actual_in == result[0]
        assert actual_out == result[1]
