"""Shared GUI state — GuiState, EditingProfile, generate_draft_name()."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from voicechanger.gui.logic import GuiEffectState


class PipelineMode(Enum):
    """How the GUI interacts with the audio pipeline.

    The GUI always launches a service subprocess — this enum is kept for
    backward compatibility only.
    """

    EMBEDDED = "EMBEDDED"
    REMOTE = "REMOTE"


@dataclass
class EditingProfile:
    """Transient state for a profile being edited in the Editor view."""

    name: str
    original_name: str
    is_builtin_fork: bool = False
    is_dirty: bool = False
    effects: list[GuiEffectState] = field(default_factory=list)
    author: str = ""
    description: str = ""


class GuiState:
    """Central state object shared across all GUI views."""

    def __init__(self) -> None:
        self.mode: PipelineMode = PipelineMode.EMBEDDED
        self.pipeline_running: bool = False
        self.pipeline_state: str = "STOPPED"
        self.active_profile_name: str = ""
        self.selected_input_device: str = "default"
        self.selected_output_device: str = "default"
        self._input_level: float = 0.0
        self._output_level: float = 0.0
        self.monitor_enabled: bool = True
        self.uptime_seconds: int = 0
        self.sample_rate: int = 48000
        self.buffer_size: int = 256
        self.editing_profile: EditingProfile | None = None

    @property
    def input_level(self) -> float:
        return self._input_level

    @input_level.setter
    def input_level(self, value: float) -> None:
        self._input_level = max(0.0, min(1.0, value))

    @property
    def output_level(self) -> float:
        return self._output_level

    @output_level.setter
    def output_level(self, value: float) -> None:
        self._output_level = max(0.0, min(1.0, value))


def generate_draft_name(base_name: str, existing_names: list[str]) -> str:
    """Generate a draft name for a forked builtin profile.

    Returns ``base_name-custom-N`` where N is the lowest positive integer
    that does not collide with *existing_names*.
    """
    n = 1
    while True:
        candidate = f"{base_name}-custom-{n}"
        if candidate not in existing_names:
            return candidate
        n += 1
