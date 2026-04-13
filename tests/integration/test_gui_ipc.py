"""Integration tests for GUI↔Service IPC remote control flow."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voicechanger.config import AudioConfig, Config, ProfilesConfig, ServiceConfig
from voicechanger.gui.ipc_client import IpcClient
from voicechanger.service import Service


@pytest.fixture
def running_service(
    builtin_profiles: Path, tmp_profiles: dict[str, Path], tmp_path: Path
) -> tuple[Service, str]:
    """Start a service in a background thread and yield (service, socket_path)."""
    socket_path = str(tmp_path / "gui_ipc_test.sock")
    config = Config(
        audio=AudioConfig(),
        profiles=ProfilesConfig(
            builtin_dir=str(builtin_profiles),
            user_dir=str(tmp_profiles["user"]),
        ),
        service=ServiceConfig(socket_path=socket_path),
    )
    service = Service(config)

    with patch("voicechanger.audio._open_stream", return_value=MagicMock()):
        thread = threading.Thread(target=service.run, daemon=True)
        thread.start()
        time.sleep(0.4)  # Wait for service to start

    yield service, socket_path

    service._shutdown_event.set()
    thread.join(timeout=3)


class TestGuiIpcIntegration:
    """Test GUI IpcClient talking to a real Service instance."""

    def test_connect_and_get_status(
        self, running_service: tuple[Service, str]
    ) -> None:
        _service, socket_path = running_service

        async def _test() -> None:
            client = IpcClient()
            connected = await client.connect(socket_path)
            assert connected is True

            result = await client.get_status()
            assert result["ok"] is True
            assert result["data"]["state"] == "RUNNING"
            assert result["data"]["active_profile"] == "clean"
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_set_monitor_roundtrip(
        self, running_service: tuple[Service, str]
    ) -> None:
        _service, socket_path = running_service

        async def _test() -> None:
            client = IpcClient()
            await client.connect(socket_path)

            result = await client.set_monitor(False)
            assert result["ok"] is True
            assert result["data"]["monitor_enabled"] is False

            result = await client.set_monitor(True)
            assert result["ok"] is True
            assert result["data"]["monitor_enabled"] is True

            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_switch_profile_roundtrip(
        self, running_service: tuple[Service, str]
    ) -> None:
        _service, socket_path = running_service

        async def _test() -> None:
            client = IpcClient()
            await client.connect(socket_path)

            result = await client.switch_profile("high-pitched")
            assert result["ok"] is True
            assert result["data"]["profile"] == "high-pitched"

            # Verify status reflects new profile
            status = await client.get_status()
            assert status["data"]["active_profile"] == "high-pitched"

            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())
