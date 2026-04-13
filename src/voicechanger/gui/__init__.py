"""GUI package — entry point with embedded/remote mode detection."""

from __future__ import annotations

import logging
import os
import socket

logger = logging.getLogger(__name__)


def _detect_mode():
    """Detect whether a service daemon is already running.

    Probes the Unix socket; if a connection succeeds, the GUI starts in
    REMOTE mode.  Otherwise it falls back to EMBEDDED.
    """
    from voicechanger.gui.state import PipelineMode

    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    socket_path = os.path.join(runtime_dir, "voicechanger.sock")

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect(socket_path)
        sock.close()
        logger.info("Service detected at %s — starting in REMOTE mode", socket_path)
        return PipelineMode.REMOTE
    except (OSError, ConnectionRefusedError, FileNotFoundError):
        logger.info("No service detected — starting in EMBEDDED mode")
        return PipelineMode.EMBEDDED


def launch_gui() -> None:
    """Launch the Voice Changer GUI application."""
    from pathlib import Path

    import flet as ft

    from voicechanger.config import load_config
    from voicechanger.gui.app import VoiceChangerApp
    from voicechanger.gui.state import GuiState, PipelineMode
    from voicechanger.gui.views.control import ControlView
    from voicechanger.gui.views.editor import EditorView
    from voicechanger.gui.views.profiles import ProfilesView
    from voicechanger.gui.views.tools import ToolsView
    from voicechanger.registry import ProfileRegistry

    mode = _detect_mode()
    state = GuiState()
    state.mode = mode

    config = load_config(Path("voicechanger.toml"))
    registry = ProfileRegistry(
        builtin_dir=Path(config.profiles.builtin_dir),
        user_dir=Path(config.profiles.user_dir),
    )

    def _start(page: ft.Page) -> None:
        app = VoiceChangerApp(page, state=state)

        ipc_client = None
        if mode == PipelineMode.REMOTE:
            import asyncio
            import os

            from voicechanger.gui.ipc_client import IpcClient

            runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
            socket_path = os.path.join(runtime_dir, "voicechanger.sock")
            ipc_client = IpcClient()

            async def _connect_ipc() -> None:
                try:
                    await ipc_client.connect(socket_path)
                except Exception:
                    logger.warning("IPC connect failed", exc_info=True)

            asyncio.get_event_loop().run_until_complete(_connect_ipc())

        def _build_control() -> ControlView:
            view = ControlView(page, state, registry=registry)
            if ipc_client:
                view.set_ipc_client(ipc_client)
            return view

        def _build_profiles() -> ProfilesView:
            view = ProfilesView(
                state,
                registry,
                navigate_to_editor=lambda: app.navigate_to(2),
                show_snackbar=app.show_snackbar,
            )
            if ipc_client:
                view.set_ipc_client(ipc_client)
            return view

        def _build_editor() -> EditorView:
            view = EditorView(state, registry, show_snackbar=app.show_snackbar)
            view.load_editing_profile()
            return view

        def _build_tools() -> ToolsView:
            return ToolsView(state, registry=registry, show_snackbar=app.show_snackbar)

        app.register_view_builder(0, _build_control)
        app.register_view_builder(1, _build_profiles)
        app.register_view_builder(2, _build_editor)
        app.register_view_builder(3, _build_tools)

        # Trigger initial view load
        app._switch_view(0)

    ft.app(target=_start)
