"""Contract tests for IPC protocol."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from voicechanger.config import AudioConfig, Config, ProfilesConfig, ServiceConfig
from voicechanger.service import Service


@pytest.fixture
def service_setup(
    builtin_profiles: Path, tmp_profiles: dict[str, Path], tmp_path: Path
) -> Generator[tuple[Service, str], None, None]:
    """Set up a service with a temp socket for testing."""
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
    yield service, socket_path


def _send_ipc(
    socket_path: str, command: str, params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an IPC command and return the response."""
    request: dict[str, Any] = {"command": command}
    if params:
        request["params"] = params

    # Retry connection up to 2 seconds while server starts
    for _attempt in range(20):
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(socket_path)
            break
        except (FileNotFoundError, ConnectionRefusedError):
            sock.close()
            time.sleep(0.1)
    else:
        raise ConnectionError(f"Could not connect to {socket_path}")

    try:
        sock.sendall(json.dumps(request).encode("utf-8") + b"\n")
        data = sock.recv(65536)
        return json.loads(data.decode("utf-8").strip())
    finally:
        sock.close()


class TestIPCProtocol:
    """Test the IPC command interface."""

    @patch("voicechanger.audio._open_stream")
    def test_switch_profile(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        # Run service in background thread
        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            resp = _send_ipc(socket_path, "switch_profile", {"name": "high-pitched"})
            assert resp["ok"] is True
            assert resp["data"]["profile"] == "high-pitched"
            assert resp["data"]["effects_count"] == 2
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)

    @patch("voicechanger.audio._open_stream")
    def test_list_profiles(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            resp = _send_ipc(socket_path, "list_profiles")
            assert resp["ok"] is True
            names = [p["name"] for p in resp["data"]["profiles"]]
            assert "clean" in names
            assert "high-pitched" in names
            assert "low-pitched" in names
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)

    @patch("voicechanger.audio._open_stream")
    def test_get_profile(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            resp = _send_ipc(socket_path, "get_profile", {"name": "clean"})
            assert resp["ok"] is True
            assert resp["data"]["name"] == "clean"
            assert resp["data"]["effects"] == []
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)

    @patch("voicechanger.audio._open_stream")
    def test_get_status(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            resp = _send_ipc(socket_path, "get_status")
            assert resp["ok"] is True
            assert "state" in resp["data"]
            assert "active_profile" in resp["data"]
            assert "uptime_seconds" in resp["data"]
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)

    @patch("voicechanger.audio._open_stream")
    def test_reload_profiles(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            resp = _send_ipc(socket_path, "reload_profiles")
            assert resp["ok"] is True
            assert "profiles_count" in resp["data"]
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)


class TestIPCErrors:
    """Test error handling in IPC protocol."""

    @patch("voicechanger.audio._open_stream")
    def test_invalid_command(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            resp = _send_ipc(socket_path, "nonexistent_command")
            assert resp["ok"] is False
            assert resp["error"]["code"] == "INVALID_COMMAND"
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)

    @patch("voicechanger.audio._open_stream")
    def test_profile_not_found(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            resp = _send_ipc(socket_path, "switch_profile", {"name": "nonexistent"})
            assert resp["ok"] is False
            assert resp["error"]["code"] == "PROFILE_NOT_FOUND"
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)

    @patch("voicechanger.audio._open_stream")
    def test_json_framing(
        self, mock_open: MagicMock, service_setup: tuple[Service, str]
    ) -> None:
        """Verify JSON-over-newline framing works correctly."""
        mock_open.return_value = MagicMock()
        service, socket_path = service_setup

        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.3)

        try:
            # Send raw JSON with newline terminator
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(socket_path)
            sock.sendall(b'{"command": "get_status"}\n')
            data = sock.recv(65536)
            sock.close()

            # Response should be valid JSON terminated by newline
            assert data.endswith(b"\n")
            resp = json.loads(data.decode("utf-8").strip())
            assert resp["ok"] is True
        finally:
            service._shutdown_event.set()
            thread.join(timeout=3)
