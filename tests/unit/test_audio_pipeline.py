"""Unit tests for AudioPipeline."""

from __future__ import annotations

import types
from unittest.mock import patch

import numpy as np

from tests.fake_stream import FakeAudioStream, fake_open_stream
from voicechanger.audio import AudioPipeline, PipelineState, _candidate_device_pairs
from voicechanger.profile import Profile


class TestPipelineStateMachine:
    """Test AudioPipeline state transitions."""

    def test_initial_state_is_stopped(self) -> None:
        pipeline = AudioPipeline()
        assert pipeline.state == PipelineState.STOPPED

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_start_transitions_to_running(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        assert pipeline.state == PipelineState.RUNNING

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_stop_transitions_to_stopped(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        pipeline.stop()
        assert pipeline.state == PipelineState.STOPPED

    def test_stop_when_already_stopped_is_noop(self) -> None:
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

    def test_pipewire_first_when_default_and_bluealsa_present(self) -> None:
        """PipeWire is tried before BlueALSA dummy default when both are present."""
        fake_audio_stream = types.SimpleNamespace(
            default_input_device_name="00:00:00:00:00:00",
            default_output_device_name="00:00:00:00:00:00",
            input_device_names=[
                "00:00:00:00:00:00",
                "PipeWire Sound Server",
            ],
            output_device_names=[
                "00:00:00:00:00:00",
                "PipeWire Sound Server",
            ],
        )
        fake_io_module = types.SimpleNamespace(AudioStream=fake_audio_stream)

        with patch.dict("sys.modules", {"pedalboard.io": fake_io_module}):
            pairs = _candidate_device_pairs("default", "default")

        assert pairs, "Should have at least one candidate pair"
        assert pairs[0] == ("PipeWire Sound Server", "PipeWire Sound Server")
        # MAC-address dummy must not appear in any pair
        for in_d, out_d in pairs:
            assert "00:00:00:00:00:00" not in (in_d, out_d), (
                f"BlueALSA dummy device leaked into pairs: {in_d!r}, {out_d!r}"
            )

    def test_mac_address_devices_excluded_from_candidates(self) -> None:
        """Devices whose name is a bare MAC address are filtered from all candidate pairs."""
        fake_audio_stream = types.SimpleNamespace(
            default_input_device_name="AB:CD:EF:01:23:45",
            default_output_device_name="AB:CD:EF:01:23:45",
            input_device_names=["AB:CD:EF:01:23:45", "hw:1,0"],
            output_device_names=["AB:CD:EF:01:23:45", "hw:1,0"],
        )
        fake_io_module = types.SimpleNamespace(AudioStream=fake_audio_stream)

        with patch.dict("sys.modules", {"pedalboard.io": fake_io_module}):
            pairs = _candidate_device_pairs("default", "default")

        for in_d, out_d in pairs:
            assert "AB:CD:EF:01:23:45" not in (in_d, out_d)


class TestPluginConstruction:
    """Test building plugin list from profile."""

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_empty_effects_no_plugins(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        assert pipeline.plugin_count == 0

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_effects_produce_plugins(self, _mock_open: object) -> None:
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

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_live_pitch_shift_falls_back(self, _mock_open: object) -> None:
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

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_bad_profile_falls_back_to_passthrough(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(
            name="bad-profile",
            effects=[{"type": "CompletelyFake", "params": {}}],
        )
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        assert pipeline.state in (PipelineState.RUNNING, PipelineState.DEGRADED)
        assert pipeline.plugin_count == 0


class TestDeviceOpenFallbacks:
    """Test startup retries alternate device pairs when open fails."""

    @patch("voicechanger.audio._candidate_device_pairs")
    @patch("voicechanger.audio._open_stream")
    def test_start_retries_alternate_pairs(
        self,
        mock_open: object,
        mock_pairs: object,
    ) -> None:
        mock_pairs.return_value = [  # type: ignore[union-attr]
            ("bad-in", "bad-out"),
            ("good-in", "good-out"),
        ]
        good_stream = FakeAudioStream()
        mock_open.side_effect = [ValueError("no channels"), good_stream]  # type: ignore[union-attr]

        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)

        assert mock_open.call_count == 2  # type: ignore[union-attr]
        assert pipeline.state == PipelineState.RUNNING

    @patch("voicechanger.audio._candidate_device_pairs")
    @patch("voicechanger.audio._open_stream")
    def test_start_records_opened_device_details(
        self,
        mock_open: object,
        mock_pairs: object,
    ) -> None:
        mock_pairs.return_value = [("chosen-in", "chosen-out")]  # type: ignore[union-attr]
        stream = FakeAudioStream(num_input_channels=1, num_output_channels=2)
        mock_open.return_value = stream  # type: ignore[union-attr]

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

    def test_monitor_enabled_by_default(self) -> None:
        pipeline = AudioPipeline()
        assert pipeline.monitor_enabled is True

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_disable_monitor(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        pipeline.set_monitor_enabled(False)
        assert pipeline.monitor_enabled is False

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_enable_monitor(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        pipeline.set_monitor_enabled(False)
        pipeline.set_monitor_enabled(True)
        assert pipeline.monitor_enabled is True

    def test_set_monitor_when_stopped_is_noop(self) -> None:
        pipeline = AudioPipeline()
        pipeline.set_monitor_enabled(False)
        assert pipeline.monitor_enabled is True

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_get_status_includes_monitor(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        status = pipeline.get_status()
        assert "monitor_enabled" in status
        assert status["monitor_enabled"] is True

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_disable_monitor_updates_stream_plugins(self, _mock_open: object) -> None:
        """Verify that toggling monitor actually pushes new plugins to the stream."""
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)
        stream: FakeAudioStream = pipeline._stream
        initial_plugin_count = len(stream.plugins_history)

        pipeline.set_monitor_enabled(False)
        assert len(stream.plugins_history) > initial_plugin_count


class TestProfileHotSwitch:
    """Test switching profiles while running."""

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_switch_profile(self, _mock_open: object) -> None:
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

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_switch_to_bad_profile_degrades(self, _mock_open: object) -> None:
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

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_switch_profile_updates_stream_plugins(self, _mock_open: object) -> None:
        """Verify the stream receives a new plugin chain on profile switch."""
        pipeline = AudioPipeline()
        profile1 = Profile(name="clean", effects=[])
        pipeline.start(profile1, sample_rate=48000, buffer_size=256)
        stream: FakeAudioStream = pipeline._stream

        profile2 = Profile(
            name="loud",
            effects=[{"type": "Gain", "params": {"gain_db": 6.0}}],
        )
        plugins_before = len(stream.plugins_history)
        pipeline.switch_profile(profile2)
        assert len(stream.plugins_history) > plugins_before


class TestLevelCallback:
    """Test RMS level computation and thread-safe access."""

    def test_initial_levels_zero(self) -> None:
        pipeline = AudioPipeline()
        assert pipeline.input_level == 0.0
        assert pipeline.output_level == 0.0

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_update_levels(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)

        audio = np.full(1024, 0.5, dtype=np.float32)
        pipeline.update_levels(audio, audio)
        assert pipeline.input_level > 0.0
        assert pipeline.output_level > 0.0

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_levels_reset_on_stop(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)

        audio = np.full(1024, 0.5, dtype=np.float32)
        pipeline.update_levels(audio, audio)
        assert pipeline.input_level > 0.0

        pipeline.stop()
        assert pipeline.input_level == 0.0
        assert pipeline.output_level == 0.0

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_levels_clamped_to_unit(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)

        audio = np.ones(1024, dtype=np.float32)
        pipeline.update_levels(audio, audio)
        assert 0.0 <= pipeline.input_level <= 1.0
        assert 0.0 <= pipeline.output_level <= 1.0

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_get_status_includes_levels(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile)
        status = pipeline.get_status()
        assert "input_level" in status
        assert "output_level" in status

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_poll_levels_reads_from_stream(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])
        pipeline.start(profile, sample_rate=48000, buffer_size=256)

        stream: FakeAudioStream = pipeline._stream
        pipeline.poll_levels()

        assert len(stream.read_calls) >= 1
        assert stream.read_calls[0] == 256
        # FakeAudioStream returns 0.1-amplitude sine, boosted by x4 meter_scale
        assert pipeline.input_level > 0.2
