"""Integration tests for CLI-to-service flow."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voicechanger.cli import main
from voicechanger.config import AudioConfig, Config, ProfilesConfig, ServiceConfig
from voicechanger.service import Service


@pytest.fixture
def running_service(
    builtin_profiles: Path, tmp_profiles: dict[str, Path], tmp_path: Path
) -> Generator[tuple[Service, str], None, None]:
    """Start a service in a background thread."""
    socket_path = str(tmp_path / "test.sock")

    config = Config(
        audio=AudioConfig(),
        profiles=ProfilesConfig(
            builtin_dir=str(builtin_profiles),
            user_dir=str(tmp_profiles["user"]),
        ),
        service=ServiceConfig(socket_path=socket_path),
    )

    service = Service(config)

    with patch("voicechanger.audio._open_stream") as mock_open:
        mock_open.return_value = MagicMock()
        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()

        # Wait for server to be ready
        for _ in range(20):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(socket_path)
                sock.close()
                break
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.1)

        yield service, socket_path

        service._shutdown_event.set()
        thread.join(timeout=3)


class TestCLIServiceIntegration:
    """Test CLI commands against a running service."""

    def test_profile_switch_reaches_service(
        self,
        running_service: tuple[Service, str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        service, socket_path = running_service
        with patch("voicechanger.cli._get_socket_path", return_value=socket_path):
            with pytest.raises(SystemExit) as exc:
                main(["profile", "switch", "high-pitched"])
            assert exc.value.code == 0
        assert service.active_profile_name == "high-pitched"

    def test_profile_create_appears_in_list(
        self,
        running_service: tuple[Service, str],
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        service, socket_path = running_service
        with patch("voicechanger.cli._get_config") as mock_config:
            from voicechanger.config import Config, ProfilesConfig

            mock_config.return_value = Config(
                profiles=ProfilesConfig(
                    builtin_dir=str(builtin_profiles),
                    user_dir=str(tmp_profiles["user"]),
                )
            )
            # Create a profile
            with pytest.raises(SystemExit) as exc:
                main([
                    "profile", "create", "test-robot",
                    "--effect", "Gain", "gain_db=3.0",
                ])
            assert exc.value.code == 0

            # Verify it appears in list
            capsys.readouterr()  # Clear output
            with pytest.raises(SystemExit):
                main(["profile", "list"])
            output = capsys.readouterr().out
            assert "test-robot" in output

    def test_profile_delete_removes_file(
        self,
        running_service: tuple[Service, str],
        builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
    ) -> None:
        service, socket_path = running_service
        user_dir = tmp_profiles["user"]

        with patch("voicechanger.cli._get_config") as mock_config:
            from voicechanger.config import Config, ProfilesConfig

            mock_config.return_value = Config(
                profiles=ProfilesConfig(
                    builtin_dir=str(builtin_profiles),
                    user_dir=str(user_dir),
                )
            )
            # Create then delete
            with pytest.raises(SystemExit):
                main(["profile", "create", "to-delete", "--effect", "Gain", "gain_db=1.0"])
            assert (user_dir / "to-delete.json").exists()

            with pytest.raises(SystemExit) as exc:
                main(["profile", "delete", "to-delete", "--force"])
            assert exc.value.code == 0
            assert not (user_dir / "to-delete.json").exists()
