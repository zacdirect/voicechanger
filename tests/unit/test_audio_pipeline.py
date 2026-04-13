"""Unit tests for AudioPipeline."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

from voicechanger.audio import AudioPipeline, PipelineState, _candidate_device_pairs
from voicechanger.profile import Profile


class TestPipelineStateMachine:
    """Test AudioPipeline state transitions."""

    def test_initial_state_is_stopped(self) -> None:
        pipeline = AudioPipeline()
        assert pipeline.state == PipelineState.STOPPED

    @patch("voicechanger.audio._open_stream")
    def test_start_transitions_to_running(self, mock_open: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        assert pipeline.state == PipelineState.RUNNING

    @patch("voicechanger.audio._open_stream")
    def test_stop_transitions_to_stopped(self, mock_open: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        pipeline.stop()
        assert pipeline.state == PipelineState.STOPPED

    @patch("voicechanger.audio._open_stream")
    def test_stop_when_already_stopped_is_noop(self, mock_open: MagicMock) -> None:
        pipeline = AudioPipeline()
        pipeline.stop()  # Should not raise
        assert pipeline.state == PipelineState.STOPPED


class TestCandidateDevicePairs:
    """Test ordered fallback pair generation for robust defaults."""

    def test_default_pair_uses_directional_fallbacks(self) -> None:
        fake_audio_stream = types.SimpleNamespace(
            default_input_device_name="Default ALSA Output (currently PipeWire Media Server)",
            default_output_device_name="Default ALSA Output (currently PipeWire Media Server)",
            input_device_names=[
                "Default ALSA Output (currently PipeWire Media Server)",
                "PipeWire Sound Server",
                "USB C Earbuds, USB Audio; Front output / input",
            ],
            output_device_names=[
                "Default ALSA Output (currently PipeWire Media Server)",
                "PipeWire Sound Server",
                "USB C Earbuds, USB Audio; Front output / input",
            ],
        )
        fake_io_module = types.SimpleNamespace(AudioStream=fake_audio_stream)

        with patch.dict("sys.modules", {"pedalboard.io": fake_io_module}):
            pairs = _candidate_device_pairs("default", "default")

        assert pairs
        first_in, first_out = pairs[0]
        assert first_in != "Default ALSA Output (currently PipeWire Media Server)"
        assert first_out in {
            "Default ALSA Output (currently PipeWire Media Server)",
            "PipeWire Sound Server",
            "USB C Earbuds, USB Audio; Front output / input",
        }


class TestPluginConstruction:
    """Test building plugin list from profile."""

    @patch("voicechanger.audio._open_stream")
    def test_empty_effects_no_plugins(self, mock_open: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        assert pipeline.plugin_count == 0

    @patch("voicechanger.audio._open_stream")
    def test_effects_produce_plugins(self, mock_open: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream
        pipeline = AudioPipeline()
        profile = Profile(
            name="test-effects",
            effects=[
                {"type": "Gain", "params": {"gain_db": 3.0}},
                {"type": "Reverb", "params": {"room_size": 0.5}},
            ],
        )
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        assert pipeline.plugin_count == 2

    @patch("voicechanger.audio._open_stream")
    def test_live_pitch_shift_falls_back(self, mock_open: MagicMock) -> None:
        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(
            name="live-pitch",
            effects=[{"type": "LivePitchShift", "params": {"semitones": -4.0}}],
        )
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        # With stock pedalboard, LivePitchShift should map to PitchShift instead of being dropped.
        assert pipeline.plugin_count == 1


class TestPassThroughFallback:
    """Test pass-through fallback on bad profile."""

    @patch("voicechanger.audio._open_stream")
    def test_bad_profile_falls_back_to_passthrough(self, mock_open: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream
        pipeline = AudioPipeline()
        # Profile with only unknown effects
        profile = Profile(
            name="bad-profile",
            effects=[{"type": "CompletelyFake", "params": {}}],
        )
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        # Should still be running (degraded/pass-through), not crashed
        assert pipeline.state in (PipelineState.RUNNING, PipelineState.DEGRADED)
        assert pipeline.plugin_count == 0


class TestDeviceOpenFallbacks:
    """Test startup retries alternate device pairs when open fails."""

    @patch("voicechanger.audio._candidate_device_pairs")
    @patch("voicechanger.audio._open_stream")
    def test_start_retries_alternate_pairs(
        self,
        mock_open: MagicMock,
        mock_pairs: MagicMock,
    ) -> None:
        mock_pairs.return_value = [
            ("bad-in", "bad-out"),
            ("good-in", "good-out"),
        ]
        mock_open.side_effect = [ValueError("no channels"), MagicMock()]

        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)

        assert mock_open.call_count == 2
        assert pipeline.state == PipelineState.RUNNING

    @patch("voicechanger.audio._candidate_device_pairs")
    @patch("voicechanger.audio._open_stream")
    def test_start_records_opened_device_details(
        self,
        mock_open: MagicMock,
        mock_pairs: MagicMock,
    ) -> None:
        mock_pairs.return_value = [("chosen-in", "chosen-out")]
        stream = MagicMock()
        stream.num_input_channels = 1
        stream.num_output_channels = 2
        mock_open.return_value = stream

        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)

        status = pipeline.get_status()
        assert status["opened_input_device"] == "chosen-in"
        assert status["opened_output_device"] == "chosen-out"
        assert status["opened_input_channels"] == 1
        assert status["opened_output_channels"] == 2


class TestMonitorEnabled:
    """Test AudioPipeline.set_monitor_enabled() mute control."""

    @patch("voicechanger.audio._open_stream")
    def test_monitor_enabled_by_default(self, mock_open: MagicMock) -> None:
        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        assert pipeline.monitor_enabled is True

    @patch("voicechanger.audio._open_stream")
    def test_disable_monitor(self, mock_open: MagicMock) -> None:
        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        pipeline.set_monitor_enabled(False)
        assert pipeline.monitor_enabled is False

    @patch("voicechanger.audio._open_stream")
    def test_enable_monitor(self, mock_open: MagicMock) -> None:
        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        pipeline.set_monitor_enabled(False)
        pipeline.set_monitor_enabled(True)
        assert pipeline.monitor_enabled is True

    def test_set_monitor_when_stopped_is_noop(self) -> None:
        pipeline = AudioPipeline()
        pipeline.set_monitor_enabled(False)
        # Should not raise, monitor stays at default
        assert pipeline.monitor_enabled is True

    @patch("voicechanger.audio._open_stream")
    def test_get_status_includes_monitor(self, mock_open: MagicMock) -> None:
        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        status = pipeline.get_status()
        assert "monitor_enabled" in status
        assert status["monitor_enabled"] is True

class TestProfileHotSwitch:
    """Test switching profiles while running."""

    @patch("voicechanger.audio._open_stream")
    def test_switch_profile(self, mock_open: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream
        pipeline = AudioPipeline()
        profile1 = Profile(name="clean", effects=[])
        profile2 = Profile(
            name="loud",
            effects=[{"type": "Gain", "params": {"gain_db": 6.0}}],
        )
        pipeline.start(profile1, sample_rate=48000, buffer_size=256)
        assert pipeline.plugin_count == 0
        pipeline.switch_profile(profile2)
        assert pipeline.plugin_count == 1
        assert pipeline.state == PipelineState.RUNNING

    @patch("voicechanger.audio._open_stream")
    def test_switch_to_bad_profile_degrades(self, mock_open: MagicMock) -> None:
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream
        pipeline = AudioPipeline()
        good = Profile(
            name="good-profile",
            effects=[{"type": "Gain", "params": {"gain_db": 1.0}}],
        )
        bad = Profile(
            name="bad-switch",
            effects=[{"type": "NotReal", "params": {}}],
        )
        pipeline.start(good, sample_rate=48000, buffer_size=256)
        pipeline.switch_profile(bad)
        assert pipeline.state in (PipelineState.RUNNING, PipelineState.DEGRADED)


class TestLevelCallback:
    """Test RMS level computation and thread-safe access."""

    @patch("voicechanger.audio._open_stream")
    def test_initial_levels_zero(self, mock_open: MagicMock) -> None:
        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        assert pipeline.input_level == 0.0
        assert pipeline.output_level == 0.0

    @patch("voicechanger.audio._open_stream")
    def test_update_levels(self, mock_open: MagicMock) -> None:
        import numpy as np

        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)

        # Simulate level update with a sine-like signal
        audio = np.full(1024, 0.5, dtype=np.float32)
        pipeline.update_levels(audio, audio)
        assert pipeline.input_level > 0.0
        assert pipeline.output_level > 0.0

    @patch("voicechanger.audio._open_stream")
    def test_levels_reset_on_stop(self, mock_open: MagicMock) -> None:
        import numpy as np

        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)

        audio = np.full(1024, 0.5, dtype=np.float32)
        pipeline.update_levels(audio, audio)
        assert pipeline.input_level > 0.0

        pipeline.stop()
        assert pipeline.input_level == 0.0
        assert pipeline.output_level == 0.0

    @patch("voicechanger.audio._open_stream")
    def test_levels_clamped_to_unit(self, mock_open: MagicMock) -> None:
        import numpy as np

        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)

        # Signal at max amplitude
        audio = np.ones(1024, dtype=np.float32)
        pipeline.update_levels(audio, audio)
        assert 0.0 <= pipeline.input_level <= 1.0
        assert 0.0 <= pipeline.output_level <= 1.0

    @patch("voicechanger.audio._open_stream")
    def test_get_status_includes_levels(self, mock_open: MagicMock) -> None:
        mock_open.return_value = MagicMock()
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)
        status = pipeline.get_status()
        assert "input_level" in status
        assert "output_level" in status

    @patch("voicechanger.audio._open_stream")
    def test_poll_levels_reads_with_buffer_size_and_boosts_meter(
        self, mock_open: MagicMock
    ) -> None:
        import numpy as np

        stream = MagicMock()
        stream.read.return_value = np.full((1, 256), 0.1, dtype=np.float32)
        mock_open.return_value = stream

        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)

        pipeline.poll_levels()

        stream.read.assert_called_with(256)
        # 0.1 boosted by x4 => noticeably above raw level.
        assert pipeline.input_level > 0.2
