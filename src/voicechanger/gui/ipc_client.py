"""Async IPC client — wrapper around Unix domain socket protocol."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

MAX_MESSAGE_SIZE = 64 * 1024  # 64 KB


class IpcClient:
    """Async client for the voicechanger service IPC protocol.

    The service uses short-lived connections (one command per connection),
    so each ``send_command`` opens a fresh connection.
    """

    def __init__(self) -> None:
        self._socket_path: str = ""
        self._connected: bool = False

    async def connect(self, socket_path: str) -> bool:
        """Probe the service socket. Returns True if reachable."""
        self._socket_path = socket_path
        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            writer.close()
            await writer.wait_closed()
            self._connected = True
            return True
        except (OSError, ConnectionRefusedError, FileNotFoundError):
            self._connected = False
            return False

    async def close(self) -> None:
        """Mark the client as disconnected."""
        self._connected = False

    async def send_command(
        self, command: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send an IPC command and return the response dict.

        Opens a fresh connection for each command (matching service protocol).
        """
        if not self._connected or not self._socket_path:
            return {
                "ok": False,
                "error": {"code": "NOT_CONNECTED", "message": "Not connected to service"},
            }

        request: dict[str, Any] = {"command": command}
        if params:
            request["params"] = params

        try:
            reader, writer = await asyncio.open_unix_connection(self._socket_path)
            data = json.dumps(request).encode("utf-8") + b"\n"
            writer.write(data)
            await writer.drain()

            response_data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            writer.close()
            await writer.wait_closed()

            if not response_data:
                return {
                    "ok": False,
                    "error": {"code": "CONNECTION_CLOSED", "message": "Server closed connection"},
                }
            return json.loads(response_data.decode("utf-8").strip())
        except TimeoutError:
            return {
                "ok": False,
                "error": {"code": "TIMEOUT", "message": "Command timed out"},
            }
        except (OSError, json.JSONDecodeError) as e:
            return {
                "ok": False,
                "error": {"code": "CONNECTION_ERROR", "message": str(e)},
            }

    # Convenience methods for each IPC command

    async def get_status(self) -> dict[str, Any]:
        return await self.send_command("get_status")

    async def switch_profile(self, name: str) -> dict[str, Any]:
        return await self.send_command("switch_profile", {"name": name})

    async def list_profiles(self) -> dict[str, Any]:
        return await self.send_command("list_profiles")

    async def get_profile(self, name: str) -> dict[str, Any]:
        return await self.send_command("get_profile", {"name": name})

    async def reload_profiles(self) -> dict[str, Any]:
        return await self.send_command("reload_profiles")

    async def set_monitor(self, enabled: bool) -> dict[str, Any]:
        return await self.send_command("set_monitor", {"enabled": enabled})

    async def set_device(
        self,
        input_device: str | None = None,
        output_device: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if input_device is not None:
            params["input_device"] = input_device
        if output_device is not None:
            params["output_device"] = output_device
        return await self.send_command("set_device", params)
