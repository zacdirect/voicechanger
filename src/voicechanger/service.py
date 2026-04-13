"""Service daemon — Unix socket server, signal handling, audio pipeline management."""

from __future__ import annotations

import json
import logging
import os
import selectors
import signal
import socket
import threading
import time
from pathlib import Path
from typing import Any

from voicechanger.audio import AudioPipeline
from voicechanger.config import Config
from voicechanger.registry import ProfileRegistry

logger = logging.getLogger(__name__)

MAX_MESSAGE_SIZE = 64 * 1024  # 64 KB


def _resolve_socket_path(config_path: str) -> str:
    """Resolve the Unix socket path."""
    if config_path:
        return config_path
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return os.path.join(runtime_dir, "voicechanger.sock")


class Service:
    """Voice changer service daemon."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._pipeline = AudioPipeline()
        self._registry = ProfileRegistry(
            builtin_dir=Path(config.profiles.builtin_dir),
            user_dir=Path(config.profiles.user_dir),
        )
        self._socket_path = _resolve_socket_path(config.service.socket_path)
        self._shutdown_event = threading.Event()
        self._server_socket: socket.socket | None = None
        self._selector: selectors.DefaultSelector | None = None
        self._start_time: float = 0.0
        self._active_profile_name: str = config.profiles.active_profile

    @property
    def active_profile_name(self) -> str:
        return self._active_profile_name

    def run(self, initial_profile: str | None = None) -> int:
        """Run the service. Returns exit code."""
        self._start_time = time.monotonic()

        # Set up signal handlers (only works from main thread)
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except ValueError:
            pass  # Not in main thread (e.g., during tests)

        profile_name = initial_profile or self._config.profiles.active_profile

        # Load initial profile
        profile = self._registry.get(profile_name)
        if profile is None:
            logger.error("Profile '%s' not found, falling back to 'clean'", profile_name)
            profile = self._registry.get("clean")
            if profile is None:
                logger.error("No 'clean' profile found. Cannot start.")
                return 1

        self._active_profile_name = profile.name

        # Start audio pipeline
        try:
            self._pipeline.start(
                profile,
                sample_rate=self._config.audio.sample_rate,
                buffer_size=self._config.audio.buffer_size,
                input_device=self._config.audio.input_device,
                output_device=self._config.audio.output_device,
            )
        except Exception:
            logger.error("Failed to start audio pipeline", exc_info=True)
            return 1

        # Start socket server
        try:
            self._start_socket_server()
        except Exception:
            logger.error("Failed to start socket server", exc_info=True)
            self._pipeline.stop()
            return 1

        logger.info(
            "Service started",
            extra={
                "profile": self._active_profile_name,
                "socket": self._socket_path,
            },
        )

        # Main loop
        try:
            self._main_loop()
        finally:
            self._cleanup()

        return 0

    def _signal_handler(self, signum: int, frame: Any) -> None:
        logger.info("Received signal %d, shutting down", signum)
        self._shutdown_event.set()

    def _start_socket_server(self) -> None:
        """Start the Unix domain socket server."""
        # Clean up stale socket file
        socket_path = self._socket_path
        if os.path.exists(socket_path):
            os.unlink(socket_path)

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(socket_path)
        os.chmod(socket_path, 0o600)
        self._server_socket.listen(5)
        self._server_socket.setblocking(False)

        self._selector = selectors.DefaultSelector()
        self._selector.register(self._server_socket, selectors.EVENT_READ)

    def _main_loop(self) -> None:
        """Main event loop — handle IPC connections."""
        assert self._selector is not None

        while not self._shutdown_event.is_set():
            events = self._selector.select(timeout=0.5)
            for key, _mask in events:
                if key.fileobj is self._server_socket:
                    self._accept_connection()

    def _accept_connection(self) -> None:
        """Accept and handle a client connection."""
        assert self._server_socket is not None
        try:
            conn, _ = self._server_socket.accept()
        except OSError:
            return

        try:
            conn.settimeout(5.0)
            data = conn.recv(MAX_MESSAGE_SIZE)
            if not data:
                return

            # Reject oversized messages
            if len(data) >= MAX_MESSAGE_SIZE:
                response = {
                    "ok": False,
                    "error": {"code": "INVALID_PARAMS", "message": "Message too large"},
                }
                conn.sendall(json.dumps(response).encode("utf-8") + b"\n")
                return

            request = json.loads(data.decode("utf-8").strip())
            response = self._handle_command(request)
            conn.sendall(json.dumps(response).encode("utf-8") + b"\n")
        except json.JSONDecodeError:
            response = {
                "ok": False,
                "error": {"code": "INVALID_PARAMS", "message": "Invalid JSON"},
            }
            import contextlib
            with contextlib.suppress(OSError):
                conn.sendall(json.dumps(response).encode("utf-8") + b"\n")
        except Exception:
            logger.warning("Error handling client connection", exc_info=True)
        finally:
            conn.close()

    def _handle_command(self, request: dict[str, Any]) -> dict[str, Any]:
        """Dispatch an IPC command."""
        command = request.get("command", "")
        params = request.get("params", {})

        handlers = {
            "switch_profile": self._cmd_switch_profile,
            "list_profiles": self._cmd_list_profiles,
            "get_profile": self._cmd_get_profile,
            "get_status": self._cmd_get_status,
            "reload_profiles": self._cmd_reload_profiles,
        }

        handler = handlers.get(command)
        if handler is None:
            return {
                "ok": False,
                "error": {"code": "INVALID_COMMAND", "message": f"Unknown command: {command}"},
            }

        try:
            return handler(params)
        except Exception as e:
            logger.error("Error handling command '%s': %s", command, e)
            return {
                "ok": False,
                "error": {"code": "SERVICE_ERROR", "message": str(e)},
            }

    def _cmd_switch_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        if not name:
            return {
                "ok": False,
                "error": {"code": "INVALID_PARAMS", "message": "Missing 'name' parameter"},
            }

        profile = self._registry.get(name)
        if profile is None:
            return {
                "ok": False,
                "error": {"code": "PROFILE_NOT_FOUND", "message": f"Profile '{name}' not found"},
            }

        try:
            self._pipeline.switch_profile(profile)
            self._active_profile_name = name
            return {
                "ok": True,
                "data": {"profile": name, "effects_count": len(profile.effects)},
            }
        except Exception as e:
            return {
                "ok": False,
                "error": {"code": "PROFILE_LOAD_FAILED", "message": str(e)},
            }

    def _cmd_list_profiles(self, params: dict[str, Any]) -> dict[str, Any]:
        profiles = []
        for name in self._registry.list():
            profile = self._registry.get(name)
            if profile:
                profiles.append({
                    "name": name,
                    "type": self._registry.get_type(name),
                    "effects_count": len(profile.effects),
                    "description": profile.description,
                })

        return {
            "ok": True,
            "data": {
                "active": self._active_profile_name,
                "profiles": profiles,
            },
        }

    def _cmd_get_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        if not name:
            return {
                "ok": False,
                "error": {"code": "INVALID_PARAMS", "message": "Missing 'name' parameter"},
            }

        profile = self._registry.get(name)
        if profile is None:
            return {
                "ok": False,
                "error": {"code": "PROFILE_NOT_FOUND", "message": f"Profile '{name}' not found"},
            }

        return {
            "ok": True,
            "data": {
                "name": profile.name,
                "type": self._registry.get_type(name),
                "author": profile.author,
                "description": profile.description,
                "schema_version": profile.schema_version,
                "effects": profile.effects,
            },
        }

    def _cmd_get_status(self, params: dict[str, Any]) -> dict[str, Any]:
        uptime = time.monotonic() - self._start_time
        status = self._pipeline.get_status()
        return {
            "ok": True,
            "data": {
                "state": status["state"],
                "active_profile": self._active_profile_name,
                "uptime_seconds": int(uptime),
                "audio": {
                    "sample_rate": self._config.audio.sample_rate,
                    "buffer_size": self._config.audio.buffer_size,
                    "input_device": self._config.audio.input_device,
                    "output_device": self._config.audio.output_device,
                },
            },
        }

    def _cmd_reload_profiles(self, params: dict[str, Any]) -> dict[str, Any]:
        count = self._registry.reload()
        return {
            "ok": True,
            "data": {"profiles_count": count},
        }

    def _cleanup(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("Shutting down service")

        self._pipeline.stop()

        if self._selector:
            self._selector.close()

        if self._server_socket:
            self._server_socket.close()

        if os.path.exists(self._socket_path):
            os.unlink(self._socket_path)
