"""Unit tests for GUI profile authoring logic (NO tkinter dependency)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from voicechanger.audio import PipelineState
from voicechanger.gui.logic import (
    GuiEffectState,
    PreviewManager,
    build_profile_from_gui_state,
    param_to_slider,
    slider_to_param,
)
from voicechanger.profile import Profile


class TestSliderMapping:
    """Test mapping slider values (0-100) to effect parameter ranges."""

    def test_slider_to_param_gain(self) -> None:
        # gain_db range: -80 to 80, slider 50 = 0.0
        val = slider_to_param("Gain", "gain_db", 50)
        assert val == pytest.approx(0.0, abs=0.1)

    def test_slider_to_param_min(self) -> None:
        val = slider_to_param("Gain", "gain_db", 0)
        assert val == pytest.approx(-80.0, abs=0.1)

    def test_slider_to_param_max(self) -> None:
        val = slider_to_param("Gain", "gain_db", 100)
        assert val == pytest.approx(80.0, abs=0.1)

    def test_param_to_slider_gain(self) -> None:
        slider = param_to_slider("Gain", "gain_db", 0.0)
        assert slider == pytest.approx(50, abs=1)

    def test_param_to_slider_min(self) -> None:
        slider = param_to_slider("Gain", "gain_db", -80.0)
        assert slider == pytest.approx(0, abs=1)

    def test_param_to_slider_max(self) -> None:
        slider = param_to_slider("Gain", "gain_db", 80.0)
        assert slider == pytest.approx(100, abs=1)

    def test_reverb_room_size(self) -> None:
        # room_size range: 0-1, slider 75 = 0.75
        val = slider_to_param("Reverb", "room_size", 75)
        assert val == pytest.approx(0.75, abs=0.01)


class TestBuildProfile:
    """Test building a Profile from GUI state."""

    def test_build_profile_empty_effects(self) -> None:
        profile = build_profile_from_gui_state(
            name="test-empty",
            author="gui-user",
            description="Empty profile",
            effects=[],
        )
        assert profile.name == "test-empty"
        assert profile.effects == []

    def test_build_profile_with_effects(self) -> None:
        effects = [
            GuiEffectState(type="Gain", params={"gain_db": 3.0}),
            GuiEffectState(type="Reverb", params={"room_size": 0.6, "wet_level": 0.3}),
        ]
        profile = build_profile_from_gui_state(
            name="test-effects",
            author="gui-user",
            description="Profile with effects",
            effects=effects,
        )
        assert len(profile.effects) == 2
        assert profile.effects[0]["type"] == "Gain"
        assert profile.effects[1]["type"] == "Reverb"

    def test_profile_save_load_roundtrip(self, tmp_path: Path) -> None:
        effects = [
            GuiEffectState(type="LivePitchShift", params={"semitones": -4.0}),
            GuiEffectState(type="Gain", params={"gain_db": 2.0}),
        ]
        profile = build_profile_from_gui_state(
            name="round-trip-gui",
            author="tester",
            description="Roundtrip test",
            effects=effects,
        )
        path = tmp_path / "round-trip-gui.json"
        profile.save(path)

        loaded = Profile.load(path)
        assert loaded.name == "round-trip-gui"
        assert len(loaded.effects) == 2
        assert loaded.effects[0]["params"]["semitones"] == -4.0


class TestPreviewManager:
    """Test PreviewManager lifecycle (no tkinter, no real audio)."""

    def test_start_preview_creates_pipeline(self) -> None:
        mgr = PreviewManager()
        effects = [GuiEffectState(type="Gain", params={"gain_db": 3.0})]
        with patch.object(mgr._pipeline, "start") as mock_start:
            mgr.start_preview(effects)
            mock_start.assert_called_once()
            profile = mock_start.call_args[0][0]
            assert profile.name == "preview"
            assert len(profile.effects) == 1
            assert profile.effects[0]["type"] == "Gain"
        assert mgr.is_active

    def test_stop_preview(self) -> None:
        mgr = PreviewManager()
        effects = [GuiEffectState(type="Gain", params={"gain_db": 0.0})]
        with patch.object(mgr._pipeline, "start"):
            mgr.start_preview(effects)
        with patch.object(mgr._pipeline, "stop") as mock_stop:
            mgr.stop_preview()
            mock_stop.assert_called_once()
        assert not mgr.is_active

    def test_stop_when_not_active_is_noop(self) -> None:
        mgr = PreviewManager()
        with patch.object(mgr._pipeline, "stop") as mock_stop:
            mgr.stop_preview()
            mock_stop.assert_not_called()

    def test_update_preview_switches_profile(self) -> None:
        mgr = PreviewManager()
        effects1 = [GuiEffectState(type="Gain", params={"gain_db": 3.0})]
        with patch.object(mgr._pipeline, "start"):
            mgr.start_preview(effects1)
        # Force pipeline state to RUNNING so switch_profile works
        mgr._pipeline._state = PipelineState.RUNNING
        effects2 = [
            GuiEffectState(type="Gain", params={"gain_db": 6.0}),
            GuiEffectState(type="Reverb", params={"room_size": 0.5}),
        ]
        with patch.object(mgr._pipeline, "switch_profile") as mock_switch:
            mgr.update_preview(effects2)
            mock_switch.assert_called_once()
            profile = mock_switch.call_args[0][0]
            assert len(profile.effects) == 2

    def test_update_preview_when_not_active_starts(self) -> None:
        mgr = PreviewManager()
        effects = [GuiEffectState(type="Gain", params={"gain_db": 0.0})]
        with patch.object(mgr._pipeline, "start") as mock_start:
            mgr.update_preview(effects)
            mock_start.assert_called_once()
        assert mgr.is_active

    def test_preview_builds_correct_plugin_list(self) -> None:
        mgr = PreviewManager()
        effects = [
            GuiEffectState(type="LivePitchShift", params={"semitones": -4.0}),
            GuiEffectState(type="Distortion", params={"drive_db": 15.0}),
            GuiEffectState(type="Reverb", params={"room_size": 0.8, "wet_level": 0.5}),
        ]
        with patch.object(mgr._pipeline, "start") as mock_start:
            mgr.start_preview(effects)
            profile = mock_start.call_args[0][0]
            assert len(profile.effects) == 3
            assert profile.effects[0]["type"] == "LivePitchShift"
            assert profile.effects[1]["type"] == "Distortion"
            assert profile.effects[2]["type"] == "Reverb"

    def test_preview_handles_start_error_gracefully(self) -> None:
        mgr = PreviewManager()
        effects = [GuiEffectState(type="Gain", params={"gain_db": 0.0})]
        with patch.object(mgr._pipeline, "start", side_effect=Exception("no audio")):
            mgr.start_preview(effects)
        # Should not crash, and should not be marked active
        assert not mgr.is_active

    def test_preview_empty_effects(self) -> None:
        mgr = PreviewManager()
        with patch.object(mgr._pipeline, "start") as mock_start:
            mgr.start_preview([])
            profile = mock_start.call_args[0][0]
            assert profile.effects == []


class TestEditorSaveLogic:
    """Test editor save logic: build profile, auto-fork builtin detection."""

    def test_build_profile_for_save(self) -> None:
        """User profile save builds correct Profile."""
        from voicechanger.gui.state import EditingProfile

        editing = EditingProfile(
            name="my-voice",
            original_name="my-voice",
            effects=[GuiEffectState(type="Gain", params={"gain_db": 3.0})],
            author="tester",
            description="My voice",
        )
        profile = build_profile_from_gui_state(
            name=editing.name,
            author=editing.author,
            description=editing.description,
            effects=editing.effects,
        )
        assert profile.name == "my-voice"
        assert profile.author == "tester"
        assert len(profile.effects) == 1

    def test_builtin_fork_generates_new_name(self) -> None:
        """Editing a builtin triggers auto-fork with generated name."""
        from voicechanger.gui.state import EditingProfile, generate_draft_name

        existing = ["clean", "high-pitched", "low-pitched"]
        draft = generate_draft_name("clean", existing)
        assert draft == "clean-custom-1"

        editing = EditingProfile(
            name=draft,
            original_name="clean",
            is_builtin_fork=True,
            effects=[GuiEffectState(type="Gain", params={"gain_db": 0.0})],
        )
        profile = build_profile_from_gui_state(
            name=editing.name,
            author=editing.author,
            description=editing.description,
            effects=editing.effects,
        )
        assert profile.name == "clean-custom-1"
        assert editing.is_builtin_fork is True

    def test_fork_save_creates_via_registry(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        """Forked builtin saved via registry.create(), not update()."""
        from voicechanger.registry import ProfileRegistry

        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = build_profile_from_gui_state(
            name="clean-custom-1",
            author="",
            description="",
            effects=[GuiEffectState(type="Gain", params={"gain_db": 2.0})],
        )
        registry.create(profile)
        assert registry.exists("clean-custom-1")
        assert not registry.is_builtin("clean-custom-1")

    def test_user_profile_save_uses_update(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        """Existing user profile saved via registry.update()."""
        from voicechanger.registry import ProfileRegistry

        registry = ProfileRegistry(
            builtin_dir=builtin_profiles, user_dir=tmp_profiles["user"]
        )
        profile = Profile(name="my-voice", effects=[{"type": "Gain", "params": {"gain_db": 1.0}}])
        registry.create(profile)

        updated = build_profile_from_gui_state(
            name="my-voice",
            author="",
            description="",
            effects=[GuiEffectState(type="Gain", params={"gain_db": 5.0})],
        )
        registry.update(updated)
        result = registry.get("my-voice")
        assert result is not None
        assert result.effects[0]["params"]["gain_db"] == 5.0


class TestStatusPanelLogic:
    """Test status panel field formatting logic."""

    def test_uptime_formatting(self) -> None:
        """Verify uptime display from seconds."""
        from voicechanger.gui.state import GuiState

        state = GuiState()
        state.uptime_seconds = 3661  # 1h 1m 1s
        mins, secs = divmod(state.uptime_seconds, 60)
        hours, mins = divmod(mins, 60)
        assert hours == 1
        assert mins == 1
        assert secs == 1

    def test_level_color_thresholds(self) -> None:
        """Verify level color logic: green < 0.7, yellow < 0.9, red >= 0.9."""
        import flet as ft

        from voicechanger.gui.views.control import _level_color

        assert _level_color(0.0) == ft.Colors.GREEN
        assert _level_color(0.5) == ft.Colors.GREEN
        assert _level_color(0.7) == ft.Colors.YELLOW
        assert _level_color(0.85) == ft.Colors.YELLOW
        assert _level_color(0.9) == ft.Colors.RED
        assert _level_color(1.0) == ft.Colors.RED

    def test_level_to_db(self) -> None:
        """Verify dB conversion."""
        from voicechanger.gui.views.control import _level_to_db

        assert _level_to_db(0.0) == "-∞ dB"
        assert _level_to_db(1.0) == "0.0 dB"
        # 0.5 → ~-6.0 dB
        db_str = _level_to_db(0.5)
        assert "dB" in db_str
        val = float(db_str.replace(" dB", ""))
        assert -7.0 < val < -5.0


class TestOfflineToolsLogic:
    """Test offline processing Tools view logic."""

    def test_process_file_with_gain(self, tmp_path: Path) -> None:
        """Process a simple WAV file through a gain-only profile."""
        import wave

        import numpy as np

        from voicechanger.offline import process_file

        # Create a simple test WAV
        input_path = tmp_path / "input.wav"
        output_path = tmp_path / "output.wav"
        sample_rate = 44100
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
        samples = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype(np.int16)

        with wave.open(str(input_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())

        profile = Profile(
            name="gain-test", effects=[{"type": "Gain", "params": {"gain_db": 6.0}}]
        )
        process_file(profile, input_path, output_path)
        assert output_path.exists()

        with wave.open(str(output_path), "r") as wf:
            assert wf.getnframes() > 0

    def test_process_file_invalid_input(self, tmp_path: Path) -> None:
        """Error on nonexistent input file."""
        from voicechanger.offline import process_file

        input_path = tmp_path / "nonexistent.wav"
        output_path = tmp_path / "output.wav"
        profile = Profile(name="gain-test", effects=[])
        with pytest.raises(FileNotFoundError):
            process_file(profile, input_path, output_path)
