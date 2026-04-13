"""Unit tests for AudioPipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from voicechanger.audio import AudioPipeline, PipelineState
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
