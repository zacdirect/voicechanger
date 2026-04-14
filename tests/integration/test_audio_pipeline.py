"""Integration tests for audio pipeline lifecycle."""

from __future__ import annotations

from unittest.mock import patch

from tests.fake_stream import fake_open_stream
from voicechanger.audio import AudioPipeline, PipelineState
from voicechanger.profile import Profile


class TestPipelineLifecycle:
    """Test full pipeline lifecycle with FakeAudioStream."""

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_full_lifecycle(self, _mock_open: object) -> None:
        """Test start -> apply profile -> switch profile -> stop."""
        pipeline = AudioPipeline()
        assert pipeline.state == PipelineState.STOPPED

        # Start with clean profile
        clean = Profile(name="clean", effects=[])
        pipeline.start(clean, sample_rate=48000, buffer_size=256)
        assert pipeline.state == PipelineState.RUNNING
        assert pipeline.active_profile_name == "clean"
        assert pipeline.plugin_count == 0

        # Switch to effects profile
        effects = Profile(
            name="effect-profile",
            effects=[
                {"type": "Gain", "params": {"gain_db": 3.0}},
                {"type": "Reverb", "params": {"room_size": 0.5, "wet_level": 0.3}},
            ],
        )
        pipeline.switch_profile(effects)
        assert pipeline.state == PipelineState.RUNNING
        assert pipeline.active_profile_name == "effect-profile"
        assert pipeline.plugin_count == 2

        # Switch back to clean
        pipeline.switch_profile(clean)
        assert pipeline.plugin_count == 0

        # Stop
        pipeline.stop()
        assert pipeline.state == PipelineState.STOPPED

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_start_stop_multiple_times(self, _mock_open: object) -> None:
        pipeline = AudioPipeline()
        profile = Profile(name="clean", effects=[])

        for _ in range(3):
            pipeline.start(profile, sample_rate=48000, buffer_size=256)
            assert pipeline.state == PipelineState.RUNNING
            pipeline.stop()
            assert pipeline.state == PipelineState.STOPPED

    @patch("voicechanger.audio._open_stream", side_effect=fake_open_stream)
    def test_degraded_recovery(self, _mock_open: object) -> None:
        """Start with bad profile (degrades), then switch to good profile (recovers)."""
        pipeline = AudioPipeline()
        bad = Profile(
            name="bad-only",
            effects=[{"type": "FakeEffect", "params": {}}],
        )
        pipeline.start(bad, sample_rate=48000, buffer_size=256)
        assert pipeline.state in (PipelineState.RUNNING, PipelineState.DEGRADED)

        good = Profile(
            name="good-profile",
            effects=[{"type": "Gain", "params": {"gain_db": 1.0}}],
        )
        pipeline.switch_profile(good)
        assert pipeline.state == PipelineState.RUNNING
        assert pipeline.plugin_count == 1
