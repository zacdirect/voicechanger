"""GUI data logic — slider mapping, profile building, and live preview (no tkinter dependency)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

from voicechanger.audio import AudioPipeline
from voicechanger.effects import EFFECT_REGISTRY
from voicechanger.profile import Profile

logger = logging.getLogger(__name__)


@dataclass
class GuiEffectState:
    """Represents an effect's state in the GUI."""

    type: str
    params: dict[str, float] = field(default_factory=dict)


def slider_to_param(effect_type: str, param_name: str, slider_value: int) -> float:
    """Convert a slider value (0-100) to a parameter value."""
    schema = EFFECT_REGISTRY.get(effect_type, {}).get("params", {})
    param_schema = schema.get(param_name)
    if param_schema is None:
        return float(slider_value)

    pmin = param_schema.get("min", 0.0)
    pmax = param_schema.get("max", 1.0)
    return pmin + (pmax - pmin) * (slider_value / 100.0)


def param_to_slider(effect_type: str, param_name: str, param_value: float) -> int:
    """Convert a parameter value to a slider value (0-100)."""
    schema = EFFECT_REGISTRY.get(effect_type, {}).get("params", {})
    param_schema = schema.get(param_name)
    if param_schema is None:
        return int(param_value)

    pmin = param_schema.get("min", 0.0)
    pmax = param_schema.get("max", 1.0)
    if pmax == pmin:
        return 50
    return int(round(100.0 * (param_value - pmin) / (pmax - pmin)))


def build_profile_from_gui_state(
    name: str,
    author: str,
    description: str,
    effects: list[GuiEffectState],
) -> Profile:
    """Build a Profile from GUI state."""
    effect_dicts = [{"type": e.type, "params": dict(e.params)} for e in effects]
    return Profile(
        name=name,
        author=author,
        description=description,
        effects=effect_dicts,
    )


class PreviewManager:
    """Manages live audio preview for the GUI using AudioPipeline.

    All audio operations run on a background thread to avoid blocking
    the Flet event loop.
    """

    def __init__(self) -> None:
        self._pipeline = AudioPipeline()
        self._active = False
        self._lock = threading.Lock()
        self._update_timer: threading.Timer | None = None

    @property
    def is_active(self) -> bool:
        return self._active

    def start_preview(self, effects: list[GuiEffectState]) -> None:
        """Start live audio preview with the given effects (non-blocking)."""
        profile = self._build_preview_profile(effects)

        def _run() -> None:
            with self._lock:
                try:
                    self._pipeline.start(profile)
                    self._active = True
                except Exception:
                    logger.warning("Failed to start audio preview", exc_info=True)
                    self._active = False

        threading.Thread(target=_run, daemon=True).start()

    def update_preview(self, effects: list[GuiEffectState]) -> None:
        """Update the live preview with new effect parameters (non-blocking).

        Rapid calls are debounced: only the last update within 50 ms fires.
        """
        if not self._active:
            return
        profile = self._build_preview_profile(effects)

        # Cancel any pending debounced update
        if self._update_timer is not None:
            self._update_timer.cancel()

        def _run() -> None:
            with self._lock:
                try:
                    self._pipeline.switch_profile(profile)
                except Exception:
                    logger.warning("Failed to update preview", exc_info=True)

        self._update_timer = threading.Timer(0.05, _run)
        self._update_timer.daemon = True
        self._update_timer.start()

    def stop_preview(self) -> None:
        """Stop the live audio preview (non-blocking)."""
        if not self._active:
            return
        self._active = False

        # Cancel any pending debounced update
        if self._update_timer is not None:
            self._update_timer.cancel()
            self._update_timer = None

        def _run() -> None:
            with self._lock:
                try:
                    self._pipeline.stop()
                except Exception:
                    logger.warning("Failed to stop preview", exc_info=True)

        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def _build_preview_profile(effects: list[GuiEffectState]) -> Profile:
        """Build a transient profile for preview."""
        effect_dicts = [{"type": e.type, "params": dict(e.params)} for e in effects]
        return Profile(
            name="preview",
            author="",
            description="Live preview",
            effects=effect_dicts,
        )
