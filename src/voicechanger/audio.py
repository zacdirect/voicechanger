"""AudioPipeline — manages AudioStream lifecycle and effect chain."""

from __future__ import annotations

import enum
import glob
import logging
import os
import subprocess
import sys
import threading
import warnings
from typing import Any

import numpy as np

from voicechanger.effects import validate_effect
from voicechanger.hardware import HardwareHintRegistry
from voicechanger.profile import Profile

logger = logging.getLogger(__name__)


def _configure_alsa_plugin_env() -> None:
    """Set ALSA plugin search path for PipeWire-backed default devices on Linux."""
    if os.environ.get("ALSA_PLUGIN_DIR"):
        return

    for module_path in glob.glob("/usr/lib/*/alsa-lib/libasound_module_pcm_pipewire.so"):
        os.environ["ALSA_PLUGIN_DIR"] = os.path.dirname(module_path)
        return


_configure_alsa_plugin_env()

# Channel count candidates to probe, in preference order.
# JUCE calls abort() (not raise) when the requested count is unsupported,
# so we probe each candidate in a subprocess to protect the main process.
_OUT_CHANNEL_CANDIDATES: tuple[int, ...] = (2, 1, 6, 8)
_IN_CHANNEL_CANDIDATES: tuple[int, ...] = (1, 2)
_PROBE_TIMEOUT = 8  # seconds per subprocess probe

# Cache: (in_device, out_device) -> (num_in, num_out)
# Avoids re-probing on profile switches within the same service run.
_channel_cache: dict[tuple[str | None, str | None], tuple[int, int]] = {}


def _probe_stream(
    input_device_name: str | None,
    output_device_name: str | None,
    sample_rate: int,
    buffer_size: int,
    num_input_channels: int,
    num_output_channels: int,
) -> bool:
    """Return True if AudioStream opens successfully with the given parameters.

    Runs in a subprocess so that a JUCE abort() on an unsupported channel
    count doesn't kill the main process.
    """
    code = (
        "from pedalboard.io import AudioStream; import pedalboard as pb; "
        f"s = AudioStream("
        f"input_device_name={input_device_name!r}, "
        f"output_device_name={output_device_name!r}, "
        f"plugins=pb.Pedalboard([]), "
        f"sample_rate={sample_rate}, "
        f"buffer_size={buffer_size}, "
        f"num_input_channels={num_input_channels}, "
        f"num_output_channels={num_output_channels}); "
        "s.__exit__(None, None, None)"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            timeout=_PROBE_TIMEOUT,
            capture_output=True,
            env=os.environ.copy(),
        )
        return result.returncode == 0
    except Exception:
        return False


def _negotiate_channels(
    input_device_name: str | None,
    output_device_name: str | None,
    sample_rate: int,
    buffer_size: int,
    registry: HardwareHintRegistry | None = None,
) -> tuple[int, int] | None:
    """Return (num_input_channels, num_output_channels) that work for this device pair.

    Returns None when ALL output probes fail — the device is unusable and the
    caller must not attempt to open it in the main process (to avoid JUCE
    abort()/segfault propagating to the service).

    Lookup order:
      1. In-memory cache (avoids re-probing on profile switches within one run)
      2. Hardware hint registry (builtin + user persistent hints)
      3. Subprocess probe (safe against JUCE abort())
         → on success, writes a user hint so the next run skips probing
    """
    cache_key = (input_device_name, output_device_name)
    if cache_key in _channel_cache:
        return _channel_cache[cache_key]

    # Consult the persistent hint registry before probing.
    if registry is not None:
        hint = registry.lookup(input_device_name, output_device_name)
        if hint is not None:
            _channel_cache[cache_key] = hint
            return hint

    logger.info(
        "Probing channel counts for input=%r output=%r (first-time, results cached)",
        input_device_name,
        output_device_name,
    )

    num_out: int | None = None
    for candidate in _OUT_CHANNEL_CANDIDATES:
        if _probe_stream(
            input_device_name, output_device_name,
            sample_rate, buffer_size, 1, candidate,
        ):
            num_out = candidate
            logger.info("Output channels negotiated: %d", num_out)
            break

    if num_out is None:
        logger.warning(
            "No output channel count worked for %r — device rejected",
            output_device_name,
        )
        return None

    num_in = 1  # mono mic default
    for candidate in _IN_CHANNEL_CANDIDATES:
        if _probe_stream(
            input_device_name, output_device_name,
            sample_rate, buffer_size, candidate, num_out,
        ):
            num_in = candidate
            logger.info("Input channels negotiated: %d", num_in)
            break
    else:
        logger.warning(
            "No input channel count worked for %r; using %d",
            input_device_name, num_in,
        )

    result = (num_in, num_out)
    _channel_cache[cache_key] = result

    # Persist the discovery so subsequent runs skip probing entirely.
    if registry is not None:
        registry.write_user_hint(input_device_name, output_device_name, num_in, num_out)

    return result


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
    try:
        import pedalboard as pb
    except ImportError:
        pb = None

    plugins: list[Any] = []
    for effect_dict in profile.effects:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            validated = validate_effect(effect_dict)
            for w in caught:
                logger.warning(str(w.message))

        if validated is not None:
            effect_type = validated.get("type", "")
            params = validated.get("params", {})
            if (
                effect_type == "LivePitchShift"
                and pb is not None
                and not hasattr(pb, "LivePitchShift")
            ):
                effect_type = "PitchShift"
                logger.warning("LivePitchShift not available; falling back to PitchShift")
            if pb is None:
                plugins.append({"type": effect_type, "params": params})
                continue

            effect_cls = getattr(pb, effect_type, None)
            if effect_cls is None:
                logger.warning("Effect '%s' not available in pedalboard, skipping", effect_type)
                continue
            try:
                plugins.append(effect_cls(**params))
            except Exception:
                logger.warning("Failed to instantiate effect '%s'", effect_type, exc_info=True)
    return plugins


def _open_stream(
    sample_rate: int = 48000,
    buffer_size: int = 256,
    input_device: str = "default",
    output_device: str = "default",
    plugins: list[Any] | None = None,
    hint_registry: HardwareHintRegistry | None = None,
) -> Any:
    """Open an audio stream.

    In production, this creates a pedalboard.io.AudioStream.
    Abstracted for testability.
    """
    try:
        from pedalboard.io import AudioStream
    except ImportError as exc:
        raise RuntimeError(
            "pedalboard is required for live audio processing. "
            "Install pedalboard to run the realtime service."
        ) from exc

    import pedalboard as pb

    # "default" means: let backend choose system defaults.
    in_name = None if input_device in ("", "default") else input_device
    out_name = None if output_device in ("", "default") else output_device

    # pedalboard backend requires at least one explicit device name.
    if in_name is None and out_name is None:
        out_name = str(AudioStream.default_output_device_name)
    chain = pb.Pedalboard(plugins or [])

    num_in_out = _negotiate_channels(
        in_name, out_name, sample_rate, buffer_size, hint_registry
    )
    if num_in_out is None:
        raise RuntimeError(
            f"Device rejected by probe (all channel counts failed): "
            f"input={in_name!r} output={out_name!r}"
        )
    num_in, num_out = num_in_out

    return AudioStream(
        input_device_name=in_name,
        output_device_name=out_name,
        plugins=chain,
        sample_rate=sample_rate,
        buffer_size=buffer_size,
        num_input_channels=num_in,
        num_output_channels=num_out,
    )


def _candidate_device_pairs(input_device: str, output_device: str) -> list[tuple[str, str]]:
    """Return ordered input/output pairs to try when opening AudioStream."""
    pairs: list[tuple[str, str]] = []

    def _add(inp: str, out: str) -> None:
        pair = (inp, out)
        if pair not in pairs:
            pairs.append(pair)

    def _card_key(name: str) -> str:
        token = name.split(",", maxsplit=1)[0]
        token = token.split(";", maxsplit=1)[0]
        return "".join(ch for ch in token.lower() if ch.isalnum())

    def _looks_input_capable(name: str) -> bool:
        lower = name.lower()
        return not ("output" in lower and "input" not in lower)

    def _looks_output_capable(name: str) -> bool:
        lower = name.lower()
        return not ("input" in lower and "output" not in lower)

    def _is_mac_addr(name: str) -> bool:
        """Detect BlueALSA dummy devices registered as a bare MAC address (e.g. 00:00:00:00:00:00).

        These appear when BlueALSA is installed but no real BT device is connected.
        Opening them causes a JUCE abort() / segfault inside pedalboard.
        """
        import re
        return bool(re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", name.strip()))

    wants_default_input = (input_device or "default") == "default"
    wants_default_output = (output_device or "default") == "default"

    if not (wants_default_input and wants_default_output):
        _add(input_device or "default", output_device or "default")

    try:
        from pedalboard.io import AudioStream

        default_in = str(AudioStream.default_input_device_name)
        default_out = str(AudioStream.default_output_device_name)

        in_names = list(AudioStream.input_device_names)
        out_names = list(AudioStream.output_device_names)

        # PipeWire-first: when defaulting, try PipeWire before resolving ALSA default.
        # This avoids BlueALSA dummy devices being attempted first on systems where
        # BlueALSA hijacks the ALSA default but a working PipeWire backend is present.
        pipewire_in = next((n for n in in_names if "pipewire sound server" in n.lower()), "")
        pipewire_out = next((n for n in out_names if "pipewire sound server" in n.lower()), "")
        if wants_default_input and wants_default_output and pipewire_in and pipewire_out:
            _add(pipewire_in, pipewire_out)

        if wants_default_input and wants_default_output:
            resolved_default_in = default_in if _looks_input_capable(default_in) else ""
            resolved_default_out = default_out if _looks_output_capable(default_out) else ""

            if not resolved_default_in:
                resolved_default_in = next(
                    (n for n in in_names if _looks_input_capable(n) and not _is_mac_addr(n)),
                    default_in,
                )
            if not resolved_default_out:
                resolved_default_out = next(
                    (n for n in out_names if _looks_output_capable(n) and not _is_mac_addr(n)),
                    default_out,
                )

            # Skip MAC-address dummy devices — they will segfault pedalboard.
            if not _is_mac_addr(resolved_default_in) and not _is_mac_addr(resolved_default_out):
                _add(resolved_default_in, resolved_default_out)
        else:
            resolved_in = default_in if wants_default_input else input_device
            resolved_out = default_out if wants_default_output else output_device
            if resolved_in and resolved_out:
                _add(resolved_in, resolved_out)

        in_candidates = [
            n for n in in_names
            if n
            and "default alsa output" not in n.lower()
            and not _is_mac_addr(n)
            and _looks_input_capable(n)
        ]
        out_candidates = [
            n for n in out_names
            if n
            and "default alsa output" not in n.lower()
            and not _is_mac_addr(n)
            and _looks_output_capable(n)
        ]

        # Prefer matched-card full-duplex routes (same hardware family), ranked by usability.
        def _pair_score(in_name: str, out_name: str) -> int:
            label = f"{in_name} || {out_name}".lower()
            score = 0
            if "front output / input" in label:
                score += 100
            if "pipewire sound server" in label:
                score += 50
            if "direct sample snooping" in label:
                score -= 20
            if "direct sample mixing" in label:
                score += 10
            if "direct hardware device" in label:
                score -= 5
            return score

        matched_pairs: list[tuple[str, str]] = []
        for in_name in in_candidates:
            in_key = _card_key(in_name)
            if not in_key:
                continue
            for out_name in out_candidates:
                if in_key == _card_key(out_name):
                    matched_pairs.append((in_name, out_name))

        matched_pairs.sort(key=lambda p: _pair_score(p[0], p[1]), reverse=True)
        for in_name, out_name in matched_pairs:
            _add(in_name, out_name)

        if pipewire_in and pipewire_out:
            _add(pipewire_in, pipewire_out)

        first_in = next(
            (n for n in in_names if n and "output" not in n.lower() and not _is_mac_addr(n)),
            default_in,
        )
        first_out = next(
            (n for n in out_names if n and "input" not in n.lower() and not _is_mac_addr(n)),
            default_out,
        )
        _add(first_in, first_out)
    except Exception:
        pass

    return pairs


class AudioPipeline:
    """Manages audio stream lifecycle and effect chain application."""

    def __init__(self, hint_registry: HardwareHintRegistry | None = None) -> None:
        self._hint_registry = hint_registry
        self._state = PipelineState.STOPPED
        self._stream: Any = None
        self._plugins: list[Any] = []
        self._active_profile_name: str = ""
        self._sample_rate: int = 48000
        self._buffer_size: int = 256
        self._monitor_enabled: bool = True
        self._meter_scale: float = 4.0
        self._opened_input_device: str = ""
        self._opened_output_device: str = ""
        self._opened_input_channels: int = 0
        self._opened_output_channels: int = 0
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
        if self._stream is not None and hasattr(self._stream, "plugins"):
            try:
                self._stream.plugins = self._effective_plugins()
            except Exception:
                logger.warning("Failed to apply monitor toggle", exc_info=True)

    def set_meter_scale(self, scale: float) -> None:
        """Set meter sensitivity multiplier used for visual level meters."""
        self._meter_scale = max(0.1, float(scale))

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
        self._apply_profile(profile)

        last_error: Exception | None = None
        for in_dev, out_dev in _candidate_device_pairs(input_device, output_device):
            try:
                self._stream = _open_stream(
                    sample_rate=sample_rate,
                    buffer_size=buffer_size,
                    input_device=in_dev,
                    output_device=out_dev,
                    plugins=self._effective_plugins(),
                    hint_registry=self._hint_registry,
                )
                if hasattr(self._stream, "__enter__"):
                    self._stream.__enter__()
                if hasattr(self._stream, "ignore_dropped_input"):
                    self._stream.ignore_dropped_input = True

                logger.info("Audio stream opened using input='%s' output='%s'", in_dev, out_dev)
                self._opened_input_device = in_dev
                self._opened_output_device = out_dev
                self._opened_input_channels = int(
                    getattr(self._stream, "num_input_channels", 0) or 0
                )
                self._opened_output_channels = int(
                    getattr(self._stream, "num_output_channels", 0) or 0
                )
                self._state = PipelineState.RUNNING
                return
            except Exception as exc:
                last_error = exc
                try:
                    if self._stream is not None and hasattr(self._stream, "close"):
                        self._stream.close()
                except Exception:
                    pass
                self._stream = None
                logger.warning(
                    "Audio stream open failed for input='%s' output='%s': %s",
                    in_dev,
                    out_dev,
                    exc,
                )

        self._state = PipelineState.STOPPED
        raise RuntimeError(f"Failed to open audio stream: {last_error}") from last_error

    def stop(self) -> None:
        """Stop the audio pipeline."""
        if self._state == PipelineState.STOPPED:
            return

        self._state = PipelineState.STOPPING

        if self._stream is not None:
            try:
                if hasattr(self._stream, "__exit__"):
                    self._stream.__exit__(None, None, None)
                elif hasattr(self._stream, "close"):
                    self._stream.close()
            except Exception:
                logger.warning("Error closing audio stream", exc_info=True)
            self._stream = None

        self._plugins = []
        self._active_profile_name = ""
        self._opened_input_device = ""
        self._opened_output_device = ""
        self._opened_input_channels = 0
        self._opened_output_channels = 0
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

    def poll_levels(self) -> None:
        """Read available input audio and update meters (non-blocking best effort)."""
        if self._state not in (PipelineState.RUNNING, PipelineState.DEGRADED):
            with self._level_lock:
                self._input_level = 0.0
                self._output_level = 0.0
            return

        if self._stream is None or not hasattr(self._stream, "read"):
            return

        try:
            chunk = self._stream.read(self._buffer_size)
            if chunk is None:
                return
            arr = np.asarray(chunk)
            if arr.size == 0:
                buffered = int(getattr(self._stream, "buffered_input_sample_count", 0) or 0)
                if buffered > 0:
                    chunk = self._stream.read(max(self._buffer_size, buffered))
                    arr = np.asarray(chunk)
            if arr.size == 0:
                return

            # Boost RMS for visibility (configurable to match different hardware levels).
            boosted = arr * self._meter_scale
            self.update_levels(
                boosted,
                boosted if self._monitor_enabled else np.zeros_like(boosted),
            )
        except TypeError:
            # Some mock/backends may not accept num_samples; fallback to zero-arg read.
            try:
                chunk = self._stream.read()
                arr = np.asarray(chunk)
                if arr.size == 0:
                    return
                boosted = arr * self._meter_scale
                self.update_levels(
                    boosted,
                    boosted if self._monitor_enabled else np.zeros_like(boosted),
                )
            except Exception:
                logger.debug("Level polling failed", exc_info=True)
        except Exception:
            logger.debug("Level polling failed", exc_info=True)

    def _effective_plugins(self) -> Any:
        """Return active plugin chain as a Pedalboard, including monitor mute when disabled."""
        import pedalboard as pb

        active_plugins = list(self._plugins)
        if not self._monitor_enabled:
            active_plugins.append(pb.Gain(gain_db=-120.0))
        return pb.Pedalboard(active_plugins)

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

        # Apply plugin chain to active stream if available
        if self._stream is not None and hasattr(self._stream, "plugins"):
            try:
                self._stream.plugins = self._effective_plugins()
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
            "meter_scale": self._meter_scale,
            "opened_input_device": self._opened_input_device,
            "opened_output_device": self._opened_output_device,
            "opened_input_channels": self._opened_input_channels,
            "opened_output_channels": self._opened_output_channels,
            "input_level": self.input_level,
            "output_level": self.output_level,
        }
