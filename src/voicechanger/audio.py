"""AudioPipeline — manages AudioStream lifecycle and effect chain."""

from __future__ import annotations

import enum
import logging
import threading
import warnings
from typing import Any

import numpy as np

from voicechanger.effects import validate_effect
from voicechanger.profile import Profile

logger = logging.getLogger(__name__)


class PipelineState(enum.Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    SWITCHING_PROFILE = "SWITCHING_PROFILE"
    STOPPING = "STOPPING"


def _build_plugins(profile: Profile) -> list[Any]:
    """Build a list of plugin mock objects from a profile's effects.

    In production, this would create actual Pedalboard plugin instances.
    For now, we build lightweight dicts that represent the validated plugins.
    The actual Pedalboard integration happens when pedalboard is available.
    """
    plugins: list[Any] = []
    for effect_dict in profile.effects:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            validated = validate_effect(effect_dict)
            for w in caught:
                logger.warning(str(w.message))

        if validated is not None:
            plugins.append(validated)
    return plugins


def _open_stream(
    sample_rate: int = 48000,
    buffer_size: int = 256,
    input_device: str = "default",
    output_device: str = "default",
) -> Any:
    """Open an audio stream.

    In production, this creates a pedalboard.io.AudioStream.
    Abstracted for testability.
    """
    try:
        from pedalboard.io import AudioStream

        stream = AudioStream(
            input_device_name=input_device,
            output_device_name=output_device,
            sample_rate=sample_rate,
            buffer_size=buffer_size,
        )
        return stream
    except ImportError:
        logger.warning("pedalboard not available — using stub stream")
        return None


class AudioPipeline:
    """Manages audio stream lifecycle and effect chain application."""

    def __init__(self) -> None:
        self._state = PipelineState.STOPPED
        self._stream: Any = None
        self._plugins: list[Any] = []
        self._active_profile_name: str = ""
        self._sample_rate: int = 48000
        self._buffer_size: int = 256
        self._monitor_enabled: bool = True
        self._input_level: float = 0.0
        self._output_level: float = 0.0
        self._level_lock = threading.Lock()

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)

    @property
    def active_profile_name(self) -> str:
        return self._active_profile_name

    @property
    def monitor_enabled(self) -> bool:
        return self._monitor_enabled

    @property
    def input_level(self) -> float:
        with self._level_lock:
            return self._input_level

    @property
    def output_level(self) -> float:
        with self._level_lock:
            return self._output_level

    def update_levels(self, input_audio: np.ndarray, output_audio: np.ndarray) -> None:
        """Update input/output RMS levels from audio buffers. Thread-safe."""
        in_rms = float(np.sqrt(np.mean(input_audio.astype(np.float64) ** 2)))
        out_rms = float(np.sqrt(np.mean(output_audio.astype(np.float64) ** 2)))
        with self._level_lock:
            self._input_level = min(1.0, in_rms)
            self._output_level = min(1.0, out_rms)

    def set_monitor_enabled(self, enabled: bool) -> None:
        """Toggle output monitoring. Only takes effect while running."""
        if self._state not in (PipelineState.RUNNING, PipelineState.DEGRADED):
            return
        self._monitor_enabled = enabled

    def start(
        self,
        profile: Profile,
        sample_rate: int = 48000,
        buffer_size: int = 256,
        input_device: str = "default",
        output_device: str = "default",
    ) -> None:
        """Start the audio pipeline with the given profile."""
        if self._state != PipelineState.STOPPED:
            self.stop()

        self._state = PipelineState.STARTING
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size

        self._stream = _open_stream(
            sample_rate=sample_rate,
            buffer_size=buffer_size,
            input_device=input_device,
            output_device=output_device,
        )

        self._apply_profile(profile)

    def stop(self) -> None:
        """Stop the audio pipeline."""
        if self._state == PipelineState.STOPPED:
            return

        self._state = PipelineState.STOPPING

        if self._stream is not None:
            try:
                if hasattr(self._stream, "close"):
                    self._stream.close()
            except Exception:
                logger.warning("Error closing audio stream", exc_info=True)
            self._stream = None

        self._plugins = []
        self._active_profile_name = ""
        self._state = PipelineState.STOPPED
        with self._level_lock:
            self._input_level = 0.0
            self._output_level = 0.0

    def switch_profile(self, profile: Profile) -> None:
        """Switch to a different profile while running."""
        if self._state not in (PipelineState.RUNNING, PipelineState.DEGRADED):
            logger.warning("Cannot switch profile in state %s", self._state)
            return

        self._state = PipelineState.SWITCHING_PROFILE
        self._apply_profile(profile)

    def _apply_profile(self, profile: Profile) -> None:
        """Apply a profile's effect chain."""
        plugins = _build_plugins(profile)
        self._plugins = plugins
        self._active_profile_name = profile.name

        if len(profile.effects) > 0 and len(plugins) == 0:
            # All effects were unknown — degraded mode
            self._state = PipelineState.DEGRADED
            logger.warning(
                "Profile '%s' has no valid effects, running in pass-through (degraded)",
                profile.name,
            )
        else:
            self._state = PipelineState.RUNNING

        # In production, set stream.plugins here
        if self._stream is not None and hasattr(self._stream, "plugins"):
            try:
                # pedalboard AudioStream accepts a list of Plugin objects
                # For now, the actual plugin instantiation would happen here
                pass
            except Exception:
                logger.warning("Failed to apply plugins to stream", exc_info=True)
                self._state = PipelineState.DEGRADED

    def get_status(self) -> dict[str, Any]:
        """Return current pipeline status."""
        return {
            "state": self._state.value,
            "active_profile": self._active_profile_name,
            "plugin_count": len(self._plugins),
            "sample_rate": self._sample_rate,
            "buffer_size": self._buffer_size,
            "monitor_enabled": self._monitor_enabled,
            "input_level": self.input_level,
            "output_level": self.output_level,
        }
