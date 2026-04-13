"""Unit tests for IpcClient — async wrapper for Unix socket IPC protocol."""

from __future__ import annotations

import asyncio
import json
import os
import socket
from collections.abc import Generator
from typing import Any

import pytest

from voicechanger.gui.ipc_client import IpcClient


@pytest.fixture
def socket_path(tmp_path: Any) -> str:
    """Return a path for a temporary Unix socket."""
    return str(tmp_path / "test.sock")


@pytest.fixture
def echo_server(socket_path: str) -> Generator[str, None, None]:
    """Start a simple echo-back IPC server that returns canned responses."""
    responses: dict[str, dict[str, Any]] = {
        "get_status": {
            "ok": True,
            "data": {
                "state": "RUNNING",
                "active_profile": "clean",
                "uptime_seconds": 100,
                "audio": {
                    "sample_rate": 48000,
                    "buffer_size": 256,
                    "input_device": "default",
                    "output_device": "default",
                },
            },
        },
        "switch_profile": {
            "ok": True,
            "data": {"profile": "high-pitched", "effects_count": 2},
        },
        "list_profiles": {
            "ok": True,
            "data": {
                "active": "clean",
                "profiles": [
                    {"name": "clean", "type": "builtin", "effects_count": 0},
                ],
            },
        },
        "get_profile": {
            "ok": True,
            "data": {
                "name": "clean",
                "type": "builtin",
                "effects": [],
            },
        },
        "reload_profiles": {
            "ok": True,
            "data": {"profiles_count": 3},
        },
        "set_monitor": {
            "ok": True,
            "data": {"monitor_enabled": True},
        },
        "set_device": {
            "ok": True,
            "data": {
                "input_device": "hw:1,0",
                "output_device": "hw:2,0",
                "restarted": True,
            },
        },
    }

    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_sock.bind(socket_path)
    os.chmod(socket_path, 0o600)
    server_sock.listen(5)
    server_sock.settimeout(5.0)

    import threading

    stop_event = threading.Event()

    def serve() -> None:
        while not stop_event.is_set():
            try:
                conn, _ = server_sock.accept()
                data = conn.recv(4096)
                if data:
                    request = json.loads(data.decode("utf-8").strip())
                    command = request.get("command", "")
                    response = responses.get(command, {
                        "ok": False,
                        "error": {"code": "INVALID_COMMAND", "message": f"Unknown: {command}"},
                    })
                    conn.sendall(json.dumps(response).encode("utf-8") + b"\n")
                conn.close()
            except (OSError, TimeoutError):
                continue

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    yield socket_path

    stop_event.set()
    server_sock.close()


class TestIpcClientConnect:
    """Test IpcClient connection behavior."""

    def test_connect_to_running_service(self, echo_server: str) -> None:
        client = IpcClient()
        result = asyncio.get_event_loop().run_until_complete(client.connect(echo_server))
        assert result is True
        asyncio.get_event_loop().run_until_complete(client.close())

    def test_connect_to_nonexistent_socket(self, tmp_path: Any) -> None:
        client = IpcClient()
        path = str(tmp_path / "nonexistent.sock")
        result = asyncio.get_event_loop().run_until_complete(client.connect(path))
        assert result is False


class TestIpcClientCommands:
    """Test IpcClient command methods."""

    def test_get_status(self, echo_server: str) -> None:
        async def _test() -> None:
            client = IpcClient()
            await client.connect(echo_server)
            result = await client.get_status()
            assert result["ok"] is True
            assert result["data"]["state"] == "RUNNING"
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_switch_profile(self, echo_server: str) -> None:
        async def _test() -> None:
            client = IpcClient()
            await client.connect(echo_server)
            result = await client.switch_profile("high-pitched")
            assert result["ok"] is True
            assert result["data"]["profile"] == "high-pitched"
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_list_profiles(self, echo_server: str) -> None:
        async def _test() -> None:
            client = IpcClient()
            await client.connect(echo_server)
            result = await client.list_profiles()
            assert result["ok"] is True
            assert "profiles" in result["data"]
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_get_profile(self, echo_server: str) -> None:
        async def _test() -> None:
            client = IpcClient()
            await client.connect(echo_server)
            result = await client.get_profile("clean")
            assert result["ok"] is True
            assert result["data"]["name"] == "clean"
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_reload_profiles(self, echo_server: str) -> None:
        async def _test() -> None:
            client = IpcClient()
            await client.connect(echo_server)
            result = await client.reload_profiles()
            assert result["ok"] is True
            assert result["data"]["profiles_count"] == 3
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_set_monitor(self, echo_server: str) -> None:
        async def _test() -> None:
            client = IpcClient()
            await client.connect(echo_server)
            result = await client.set_monitor(True)
            assert result["ok"] is True
            assert result["data"]["monitor_enabled"] is True
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())

    def test_set_device(self, echo_server: str) -> None:
        async def _test() -> None:
            client = IpcClient()
            await client.connect(echo_server)
            result = await client.set_device(input_device="hw:1,0", output_device="hw:2,0")
            assert result["ok"] is True
            assert result["data"]["restarted"] is True
            await client.close()

        asyncio.get_event_loop().run_until_complete(_test())


class TestIpcClientErrorHandling:
    """Test error scenarios."""

    def test_command_on_disconnected_client(self) -> None:
        async def _test() -> None:
            client = IpcClient()
            result = await client.get_status()
            assert result["ok"] is False
            assert "error" in result

        asyncio.get_event_loop().run_until_complete(_test())

    def test_close_without_connect(self) -> None:
        """Closing without connecting should not raise."""
        client = IpcClient()
        asyncio.get_event_loop().run_until_complete(client.close())
