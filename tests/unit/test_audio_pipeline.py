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
