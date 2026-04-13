"""Unit tests for GUI state — PipelineMode, GuiState, EditingProfile, generate_draft_name."""

from __future__ import annotations

from voicechanger.gui.state import (
    EditingProfile,
    GuiState,
    PipelineMode,
    generate_draft_name,
)


class TestPipelineMode:
    """Test PipelineMode enum values."""

    def test_embedded_mode(self) -> None:
        assert PipelineMode.EMBEDDED.value == "EMBEDDED"

    def test_remote_mode(self) -> None:
        assert PipelineMode.REMOTE.value == "REMOTE"


class TestGuiState:
    """Test GuiState dataclass defaults and behavior."""

    def test_default_state(self) -> None:
        state = GuiState()
        assert state.mode == PipelineMode.EMBEDDED
        assert state.pipeline_running is False
        assert state.pipeline_state == "STOPPED"
        assert state.active_profile_name == ""
        assert state.monitor_enabled is True
        assert state.input_level == 0.0
        assert state.output_level == 0.0

    def test_input_level_clamped_high(self) -> None:
        state = GuiState()
        state.input_level = 1.5
        # Clamping is enforced by the setter or validation
        assert state.input_level <= 1.0

    def test_input_level_clamped_low(self) -> None:
        state = GuiState()
        state.input_level = -0.5
        assert state.input_level >= 0.0

    def test_output_level_clamped_high(self) -> None:
        state = GuiState()
        state.output_level = 2.0
        assert state.output_level <= 1.0

    def test_output_level_clamped_low(self) -> None:
        state = GuiState()
        state.output_level = -1.0
        assert state.output_level >= 0.0

    def test_remote_mode_assignment(self) -> None:
        state = GuiState()
        state.mode = PipelineMode.REMOTE
        assert state.mode == PipelineMode.REMOTE


class TestEditingProfile:
    """Test EditingProfile dataclass."""

    def test_default_state(self) -> None:
        ep = EditingProfile(name="test", original_name="test")
        assert ep.is_builtin_fork is False
        assert ep.is_dirty is False
        assert ep.effects == []
        assert ep.author == ""
        assert ep.description == ""

    def test_mark_dirty(self) -> None:
        ep = EditingProfile(name="test", original_name="test")
        ep.is_dirty = True
        assert ep.is_dirty is True


class TestGenerateDraftName:
    """Test auto-fork naming for builtin profiles."""

    def test_first_draft_name(self) -> None:
        existing: list[str] = ["clean", "high-pitched"]
        name = generate_draft_name("high-pitched", existing)
        assert name == "high-pitched-custom-1"

    def test_increments_on_collision(self) -> None:
        existing = ["clean", "high-pitched", "high-pitched-custom-1"]
        name = generate_draft_name("high-pitched", existing)
        assert name == "high-pitched-custom-2"

    def test_skips_multiple_collisions(self) -> None:
        existing = [
            "high-pitched",
            "high-pitched-custom-1",
            "high-pitched-custom-2",
            "high-pitched-custom-3",
        ]
        name = generate_draft_name("high-pitched", existing)
        assert name == "high-pitched-custom-4"

    def test_no_collision(self) -> None:
        existing: list[str] = []
        name = generate_draft_name("clean", existing)
        assert name == "clean-custom-1"
