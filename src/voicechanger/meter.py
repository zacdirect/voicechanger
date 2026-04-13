"""OS-level audio metering via sounddevice.

Opens a lightweight input-only PortAudio stream to read mic RMS levels
directly from the OS audio subsystem.  Works alongside the daemon's
AudioStream without conflict (PipeWire / PulseAudio handle multi-client).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Scale factor applied to raw RMS to produce a 0–1 meter value.
_DEFAULT_SCALE = 4.0


class LevelMeter:
    """Passive input-level meter backed by sounddevice."""

    def __init__(self, *, scale: float = _DEFAULT_SCALE) -> None:
        self._scale = scale
        self._stream: Any = None
        self._level: float = 0.0
        self._lock = threading.Lock()

    @property
    def input_level(self) -> float:
        with self._lock:
            return self._level

    def start(self, device: str | None = None, sample_rate: int = 48000) -> None:
        """Open a PortAudio input stream for metering."""
        if self._stream is not None:
            return

        try:
            import sounddevice as sd
        except ImportError:
            logger.warning("sounddevice not installed — level meters disabled")
            return

        # Prefer 'pipewire' device on PipeWire systems; fall back to default.
        if device is None:
            try:
                sd.query_devices("pipewire")
                device = "pipewire"
            except ValueError:
                device = None  # system default

        def _callback(
            indata: np.ndarray,
            _frames: int,
            _time: Any,
            _status: Any,
        ) -> None:
            rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))
            level = min(rms * self._scale, 1.0)
            with self._lock:
                self._level = level

        try:
            self._stream = sd.InputStream(
                callback=_callback,
                channels=1,
                samplerate=sample_rate,
                blocksize=512,
                device=device,
            )
            self._stream.start()
            logger.info("Level meter started (device=%s)", device or "default")
        except Exception:
            logger.warning("Failed to open level meter stream", exc_info=True)
            self._stream = None

    def stop(self) -> None:
        """Close the metering stream."""
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                logger.debug("Error closing level meter stream", exc_info=True)
        with self._lock:
            self._level = 0.0
