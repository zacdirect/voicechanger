"""GUI package — controls a service subprocess via IPC."""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import subprocess
import sys
import time

logger = logging.getLogger(__name__)


def _find_python() -> str:
    """Return the path to the current Python interpreter."""
    return sys.executable


def _wait_for_socket(socket_path: str, timeout: float = 5.0) -> bool:
    """Block until the service socket appears, or timeout."""
    import socket as _socket

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect(socket_path)
            sock.close()
            return True
        except (OSError, ConnectionRefusedError, FileNotFoundError):
            time.sleep(0.1)
    return False


def launch_gui() -> None:
    """Launch the Voice Changer GUI application.

    The GUI opens immediately.  The user clicks **Start** to spawn
    ``voicechanger serve`` as a child process and connect via IPC.
    **Stop** sends an IPC shutdown and terminates the subprocess.
    On window close any running subprocess is cleaned up automatically.
    """
    from pathlib import Path

    import flet as ft

    from voicechanger.config import load_config, save_config
    from voicechanger.gui.app import VoiceChangerApp
    from voicechanger.gui.ipc_client import IpcClient
    from voicechanger.gui.state import GuiState
    from voicechanger.gui.views.control import ControlView
    from voicechanger.gui.views.editor import EditorView
    from voicechanger.gui.views.profiles import ProfilesView
    from voicechanger.gui.views.tools import ToolsView
    from voicechanger.registry import ProfileRegistry

    config_path = Path("voicechanger.toml")
    config = load_config(config_path)
    registry = ProfileRegistry(
        builtin_dir=Path(config.profiles.builtin_dir),
        user_dir=Path(config.profiles.user_dir),
    )

    state = GuiState()
    state.active_profile_name = config.profiles.active_profile
    state.selected_input_device = config.audio.input_device
    state.selected_output_device = config.audio.output_device
    state.sample_rate = config.audio.sample_rate
    state.buffer_size = config.audio.buffer_size

    # ── Resolve socket path ──
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    socket_path = os.path.join(runtime_dir, "voicechanger.sock")

    serve_cmd = [_find_python(), "-m", "voicechanger", "serve", "--config", str(config_path)]

    # ── Service subprocess handle (None until user clicks Start) ──
    service_proc: list[subprocess.Popen[bytes] | None] = [None]
    ipc_client = IpcClient()
    app_ref: VoiceChangerApp | None = None

    def _persist_runtime_settings(
        *,
        profile_name: str | None = None,
        input_device: str | None = None,
        output_device: str | None = None,
    ) -> None:
        if profile_name:
            config.profiles.active_profile = profile_name
        if input_device:
            config.audio.input_device = input_device
        if output_device:
            config.audio.output_device = output_device
        save_config(config_path, config)

    async def start_service() -> bool:
        """Spawn the service subprocess and connect IPC.  Returns True on success."""
        import asyncio

        proc = subprocess.Popen(serve_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Launched service subprocess pid=%d", proc.pid)

        ok = await asyncio.to_thread(_wait_for_socket, socket_path)
        if not ok:
            logger.error("Service did not start in time")
            proc.kill()
            proc.wait()
            return False

        service_proc[0] = proc

        try:
            await ipc_client.connect(socket_path)
        except Exception:
            logger.warning("IPC connect failed after service start", exc_info=True)
            return False

        return True

    async def stop_service() -> None:
        """Send IPC shutdown, then terminate the subprocess."""
        try:
            await ipc_client.shutdown()
        except Exception:
            logger.debug("IPC shutdown failed", exc_info=True)

        try:
            await ipc_client.close()
        except Exception:
            logger.debug("IPC close failed", exc_info=True)

        _kill_proc()

    def _kill_proc() -> None:
        """Terminate / kill the subprocess if it's still alive."""
        proc = service_proc[0]
        if proc is None or proc.poll() is not None:
            return
        logger.info("Terminating service subprocess pid=%d", proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            logger.warning("Service did not exit cleanly, killing")
            proc.kill()
            proc.wait()
        service_proc[0] = None

    async def _start(page: ft.Page) -> None:
        nonlocal app_ref

        app = VoiceChangerApp(page, state=state)
        app_ref = app

        def _build_control() -> ControlView:
            view = ControlView(
                page,
                state,
                ipc_client=ipc_client,
                registry=registry,
                persist_settings=_persist_runtime_settings,
                start_service=start_service,
                stop_service=stop_service,
            )
            app.register_cleanup(view.shutdown)
            return view

        def _navigate_to_editor() -> None:
            app.navigate_to(2)
            editor_view = app._views.get(2)
            if editor_view is not None and hasattr(editor_view, 'load_editing_profile'):
                editor_view.load_editing_profile()

        def _on_profile_activated() -> None:
            """Refresh control view dropdown after profile activation."""
            control_view = app._views.get(0)
            if control_view is not None and hasattr(control_view, '_refresh_profile_list'):
                control_view._refresh_profile_list()
            import contextlib
            with contextlib.suppress(Exception):
                page.update()

        def _build_profiles() -> ProfilesView:
            view = ProfilesView(
                state,
                registry,
                navigate_to_editor=_navigate_to_editor,
                show_snackbar=app.show_snackbar,
                persist_settings=_persist_runtime_settings,
                on_activate=_on_profile_activated,
            )
            view.set_ipc_client(ipc_client)
            return view

        def _on_profile_saved() -> None:
            """Refresh profile lists in Control and Profiles views after a save."""
            control_view = app._views.get(0)
            if control_view is not None and hasattr(control_view, '_refresh_profile_list'):
                control_view._refresh_profile_list()
            profiles_view = app._views.get(1)
            if profiles_view is not None and hasattr(profiles_view, '_refresh_list'):
                profiles_view._refresh_list()
            import contextlib
            with contextlib.suppress(Exception):
                page.update()

        def _build_editor() -> EditorView:
            view = EditorView(
                state, registry,
                show_snackbar=app.show_snackbar,
                on_save=_on_profile_saved,
            )
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

    def _handle_signal(signum: int, _frame: object) -> None:
        logger.info("Received signal %s, shutting down GUI", signum)
        _kill_proc()
        os._exit(128 + signum)

    previous_sigint = None
    previous_sigterm = None
    try:
        previous_sigint = signal.getsignal(signal.SIGINT)
        previous_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
    except ValueError:
        logger.debug("Signal handlers unavailable in current thread")

    try:
        # Raspberry Pi's VideoCore GPU lacks Vulkan support for Flutter's
        # Impeller renderer, so fall back to the browser-based UI.
        _is_pi = False
        with contextlib.suppress(OSError), open("/proc/device-tree/model") as _f:
            _is_pi = "Raspberry Pi" in _f.read()
        if _is_pi:
            logger.info("Raspberry Pi detected — launching GUI in web browser")
            ft.app(target=_start, view=ft.AppView.WEB_BROWSER)
        else:
            ft.app(target=_start)
    finally:
        _kill_proc()
        if app_ref is not None:
            app_ref.shutdown()
        if previous_sigint is not None:
            signal.signal(signal.SIGINT, previous_sigint)
        if previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)
