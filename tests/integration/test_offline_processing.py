"""Integration test — offline file processing."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from voicechanger.profile import Profile


def _create_wav(
    path: Path, duration: float = 1.0, channels: int = 1,
    sample_rate: int = 44100,
) -> None:
    """Create a simple WAV file with a sine wave."""
    import math

    n_frames = int(sample_rate * duration)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(n_frames):
            for _ in range(channels):
                sample = int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate))
                wav.writeframesraw(struct.pack("<h", sample))


@pytest.fixture
def input_wav(tmp_path: Path) -> Path:
    path = tmp_path / "input.wav"
    _create_wav(path, duration=0.5, channels=1)
    return path


@pytest.fixture
def stereo_wav(tmp_path: Path) -> Path:
    path = tmp_path / "stereo.wav"
    _create_wav(path, duration=0.5, channels=2)
    return path


@pytest.fixture
def gain_profile() -> Profile:
    return Profile(
        name="test-gain",
        effects=[{"type": "Gain", "params": {"gain_db": 3.0}}],
    )


@pytest.fixture
def pitch_profile() -> Profile:
    """Profile with LivePitchShift that should become PitchShift offline."""
    return Profile(
        name="test-pitch",
        effects=[
            {"type": "LivePitchShift", "params": {"semitones": -4.0}},
            {"type": "Gain", "params": {"gain_db": 0.0}},
        ],
    )


class TestOfflineProcessing:
    """Test offline file processing through profiles."""

    def test_process_wav_file(self, input_wav: Path, tmp_path: Path, gain_profile: Profile) -> None:
        """Process a WAV file and verify output exists."""
        from voicechanger.offline import process_file

        output = tmp_path / "output.wav"
        process_file(gain_profile, input_wav, output)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_output_duration_preserved(
        self, input_wav: Path, tmp_path: Path, gain_profile: Profile
    ) -> None:
        """Output file has approximately the same duration as input."""
        from voicechanger.offline import process_file

        output = tmp_path / "output.wav"
        process_file(gain_profile, input_wav, output)

        with wave.open(str(input_wav)) as inp:
            in_duration = inp.getnframes() / inp.getframerate()

        with wave.open(str(output)) as out:
            out_duration = out.getnframes() / out.getframerate()

        assert abs(out_duration - in_duration) < 0.1

    def test_stereo_handling(
        self, stereo_wav: Path, tmp_path: Path, gain_profile: Profile
    ) -> None:
        """Process a stereo file correctly."""
        from voicechanger.offline import process_file

        output = tmp_path / "output.wav"
        process_file(gain_profile, stereo_wav, output)
        assert output.exists()

        with wave.open(str(stereo_wav)) as inp:
            in_channels = inp.getnchannels()

        with wave.open(str(output)) as out:
            out_channels = out.getnchannels()

        assert out_channels == in_channels

    def test_live_pitch_shift_remapped(
        self, input_wav: Path, tmp_path: Path, pitch_profile: Profile
    ) -> None:
        """LivePitchShift effects are remapped to PitchShift for offline."""
        from voicechanger.offline import _build_offline_effects

        effects = _build_offline_effects(pitch_profile.effects)
        # LivePitchShift should be remapped to PitchShift
        assert effects[0]["type"] == "PitchShift"
        assert effects[0]["params"]["semitones"] == -4.0
        # Gain stays as-is
        assert effects[1]["type"] == "Gain"
