"""Offline audio file processing — no service or audio hardware required."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import numpy as np

from voicechanger.profile import Profile


def _build_offline_effects(effects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remap real-time-only effects for offline processing.

    LivePitchShift → PitchShift (stock pedalboard, no patch needed).
    """
    result: list[dict[str, Any]] = []
    for effect in effects:
        if effect["type"] == "LivePitchShift":
            result.append({
                "type": "PitchShift",
                "params": dict(effect.get("params", {})),
            })
        else:
            result.append(effect)
    return result


def _build_pedalboard(effects: list[dict[str, Any]]) -> Any:
    """Build a pedalboard.Pedalboard from effect dicts."""
    try:
        import pedalboard as pb
    except ImportError as err:
        raise ImportError("pedalboard is required for offline processing") from err

    plugins = []
    for effect in effects:
        cls = getattr(pb, effect["type"], None)
        if cls is None:
            continue
        params = effect.get("params", {})
        try:
            plugins.append(cls(**params))
        except Exception:
            continue

    return pb.Pedalboard(plugins)


def process_file(
    profile: Profile,
    input_path: Path,
    output_path: Path,
) -> None:
    """Process an audio file through a profile's effect chain.

    Uses stock pedalboard (no LivePitchShift patch needed).
    Falls back to numpy-only gain if pedalboard is not available.
    """
    effects = _build_offline_effects(profile.effects)

    # Read input
    with wave.open(str(input_path), "r") as wav_in:
        n_channels = wav_in.getnchannels()
        sample_width = wav_in.getsampwidth()
        sample_rate = wav_in.getframerate()
        n_frames = wav_in.getnframes()
        raw = wav_in.readframes(n_frames)

    # Convert to float numpy array
    if sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    # Reshape for multi-channel: (channels, frames)
    samples = (
        samples.reshape(-1, n_channels).T if n_channels > 1
        else samples.reshape(1, -1)
    )

    # Try pedalboard processing, fall back to numpy-only
    try:
        board = _build_pedalboard(effects)
        processed = board(samples, sample_rate)
    except ImportError:
        # Fallback: apply gain-only effects with numpy
        processed = samples.copy()
        for effect in effects:
            if effect["type"] == "Gain":
                gain_db = effect.get("params", {}).get("gain_db", 0.0)
                processed = processed * (10.0 ** (gain_db / 20.0))

    # Clip and convert back to int16
    processed = np.clip(processed, -1.0, 1.0)
    if n_channels > 1:
        int_samples = (processed.T * 32767).astype(np.int16)
    else:
        int_samples = (processed.reshape(-1) * 32767).astype(np.int16)

    # Write output
    with wave.open(str(output_path), "w") as wav_out:
        wav_out.setnchannels(n_channels)
        wav_out.setsampwidth(2)
        wav_out.setframerate(sample_rate)
        wav_out.writeframes(int_samples.tobytes())
