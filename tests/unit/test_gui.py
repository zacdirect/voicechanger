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
