"""Unit tests for Service IPC command handlers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from voicechanger.config import AudioConfig, Config, ProfilesConfig, ServiceConfig
from voicechanger.service import Service


def _make_service(
    builtin_profiles: Path, tmp_profiles: dict[str, Path], tmp_path: Path
) -> Service:
    """Create a Service instance with temp directories (not running)."""
    socket_path = str(tmp_path / "test.sock")
    config = Config(
        audio=AudioConfig(),
        profiles=ProfilesConfig(
            builtin_dir=str(builtin_profiles),
            user_dir=str(tmp_profiles["user"]),
        ),
        service=ServiceConfig(socket_path=socket_path),
    )
    return Service(config)


class TestCmdSetMonitor:
    """Test _cmd_set_monitor handler."""

    @patch("voicechanger.audio._open_stream")
    def test_set_monitor_enabled(
        self,
        mock_open: MagicMock,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        mock_open.return_value = MagicMock()
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        # Simulate started pipeline
        from voicechanger.profile import Profile

        service._pipeline.start(Profile(name="clean", effects=[]))

        result = service._cmd_set_monitor({"enabled": True})
        assert result["ok"] is True
        assert result["data"]["monitor_enabled"] is True

    @patch("voicechanger.audio._open_stream")
    def test_set_monitor_disabled(
        self,
        mock_open: MagicMock,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        mock_open.return_value = MagicMock()
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        from voicechanger.profile import Profile

        service._pipeline.start(Profile(name="clean", effects=[]))

        result = service._cmd_set_monitor({"enabled": False})
        assert result["ok"] is True
        assert result["data"]["monitor_enabled"] is False

    def test_set_monitor_missing_param(
        self,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        result = service._cmd_set_monitor({})
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PARAMS"

    def test_set_monitor_pipeline_not_running(
        self,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        result = service._cmd_set_monitor({"enabled": True})
        assert result["ok"] is False
        assert result["error"]["code"] == "PIPELINE_NOT_RUNNING"


class TestGetStatusWithMonitor:
    """Test that get_status includes monitor_enabled field."""

    @patch("voicechanger.audio._open_stream")
    def test_status_includes_monitor_enabled(
        self,
        mock_open: MagicMock,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        mock_open.return_value = MagicMock()
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        from voicechanger.profile import Profile

        service._pipeline.start(Profile(name="clean", effects=[]))
        service._start_time = 0.0  # Fake uptime

        result = service._cmd_get_status({})
        assert result["ok"] is True
        assert "monitor_enabled" in result["data"]


class TestCmdSetDevice:
    """Test _cmd_set_device handler."""

    @patch("voicechanger.audio._open_stream")
    def test_set_both_devices(
        self,
        mock_open: MagicMock,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        mock_open.return_value = MagicMock()
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        from voicechanger.profile import Profile

        service._pipeline.start(Profile(name="clean", effects=[]))

        result = service._cmd_set_device(
            {"input_device": "hw:1,0", "output_device": "hw:2,0"}
        )
        assert result["ok"] is True
        assert result["data"]["input_device"] == "hw:1,0"
        assert result["data"]["output_device"] == "hw:2,0"
        assert result["data"]["restarted"] is True

    @patch("voicechanger.audio._open_stream")
    def test_set_only_input(
        self,
        mock_open: MagicMock,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        mock_open.return_value = MagicMock()
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        from voicechanger.profile import Profile

        service._pipeline.start(Profile(name="clean", effects=[]))

        result = service._cmd_set_device({"input_device": "hw:1,0"})
        assert result["ok"] is True
        assert result["data"]["input_device"] == "hw:1,0"
        assert result["data"]["restarted"] is True

    def test_set_device_missing_params(
        self,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        result = service._cmd_set_device({})
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PARAMS"

    def test_set_device_pipeline_not_running(
        self,
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        service = _make_service(builtin_profiles, tmp_profiles, tmp_path)
        result = service._cmd_set_device({"input_device": "hw:1,0"})
        assert result["ok"] is False
        assert result["error"]["code"] == "PIPELINE_NOT_RUNNING"
