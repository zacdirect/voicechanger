"""Control view — service start/stop, device selection, monitor toggle, status display."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

import flet as ft

from voicechanger.audio import AudioPipeline
from voicechanger.device import DeviceMonitor
from voicechanger.gui.state import GuiState, PipelineMode
from voicechanger.profile import Profile
from voicechanger.registry import ProfileRegistry

logger = logging.getLogger(__name__)

STATUS_POLL_INTERVAL = 2.0  # seconds


def _level_color(level: float) -> str:
    """Return meter color based on level: green < 0.7, yellow < 0.9, red >= 0.9."""
    if level >= 0.9:
        return ft.Colors.RED
    if level >= 0.7:
        return ft.Colors.YELLOW
    return ft.Colors.GREEN


def _level_to_db(level: float) -> str:
    """Convert a 0.0–1.0 RMS level to a dB string."""
    import math

    if level <= 0.0:
        return "-∞ dB"
    db = 20.0 * math.log10(level)
    return f"{db:.1f} dB"


def build_control_view(
    page: ft.Page,
    state: GuiState,
    *,
    pipeline: AudioPipeline | None = None,
    registry: ProfileRegistry | None = None,
) -> ft.Control:
    """Build and return the Control view layout."""
    return ControlView(page, state, pipeline=pipeline, registry=registry)


class ControlView(ft.Column):
    """Service control — start/stop, devices, monitor, status."""

    def __init__(
        self,
        page: ft.Page,
        state: GuiState,
        *,
        pipeline: AudioPipeline | None = None,
        registry: ProfileRegistry | None = None,
    ) -> None:
        super().__init__(expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)
        self._page = page
        self._state = state
        self._pipeline = pipeline or AudioPipeline()
        self._registry = registry
        self._device_monitor = DeviceMonitor()
        self._status_polling = False
        self._level_polling = False
        self._ipc_client: Any = None

        self._build_ui()

    def _build_ui(self) -> None:
        # ── Start / Stop buttons ──
        self._start_btn = ft.ElevatedButton(
            "Start", icon=ft.Icons.PLAY_ARROW, on_click=self._on_start
        )
        self._stop_btn = ft.OutlinedButton(
            "Stop", icon=ft.Icons.STOP, on_click=self._on_stop, disabled=True
        )

        # ── Profile dropdown ──
        self._profile_dropdown = ft.Dropdown(label="Profile", width=250)
        self._refresh_profile_list()

        # ── Monitor toggle ──
        self._monitor_switch = ft.Switch(
            label="Monitor",
            value=self._state.monitor_enabled,
            on_change=self._on_monitor_toggle,
        )

        service_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("SERVICE CONTROL", weight=ft.FontWeight.BOLD, size=16),
                        ft.Row(
                            [self._start_btn, self._stop_btn, self._profile_dropdown],
                            spacing=12,
                        ),
                        self._monitor_switch,
                    ],
                    spacing=10,
                ),
                padding=16,
            ),
        )

        # ── Device selection ──
        self._input_dropdown = ft.Dropdown(label="Input Device", expand=True)
        self._output_dropdown = ft.Dropdown(label="Output Device", expand=True)
        self._refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH, tooltip="Refresh devices", on_click=self._on_refresh_devices
        )
        self._refresh_device_lists()

        device_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("AUDIO DEVICES", weight=ft.FontWeight.BOLD, size=16),
                        ft.Row(
                            [self._input_dropdown, self._output_dropdown, self._refresh_btn],
                            spacing=8,
                        ),
                    ],
                    spacing=10,
                ),
                padding=16,
            ),
        )

        # ── Status area ──
        self._status_text = ft.Text("Status: STOPPED", size=14)
        self._uptime_text = ft.Text("Uptime: —", size=13)
        self._rate_text = ft.Text(f"Rate: {self._state.sample_rate} Hz", size=13)
        self._buffer_text = ft.Text(f"Buffer: {self._state.buffer_size} frames", size=13)

        status_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("STATUS", weight=ft.FontWeight.BOLD, size=16),
                        self._status_text,
                        self._uptime_text,
                        self._rate_text,
                        self._buffer_text,
                    ],
                    spacing=6,
                ),
                padding=16,
            ),
        )

        # ── Level meters ──
        self._input_meter = ft.ProgressBar(value=0, width=300, color=ft.Colors.GREEN)
        self._output_meter = ft.ProgressBar(value=0, width=300, color=ft.Colors.GREEN)
        self._input_db_label = ft.Text("-∞ dB", size=11, width=60)
        self._output_db_label = ft.Text("-∞ dB", size=11, width=60)

        meter_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("LEVEL METERS", weight=ft.FontWeight.BOLD, size=16),
                        ft.Row([
                            ft.Text("Input:", width=60),
                            self._input_meter,
                            self._input_db_label,
                        ]),
                        ft.Row([
                            ft.Text("Output:", width=60),
                            self._output_meter,
                            self._output_db_label,
                        ]),
                    ],
                    spacing=8,
                ),
                padding=16,
            ),
        )

        # ── Adapt for remote mode ──
        if self._state.mode == PipelineMode.REMOTE:
            self._start_btn.disabled = True
            self._start_btn.tooltip = "Service is running externally"
            self._stop_btn.disabled = True
            self._stop_btn.tooltip = "Stop the service via CLI or systemd"
            self._start_status_polling()

        self.controls = [service_card, device_card, ft.Row([status_card, meter_card], spacing=16)]

    # ── Profile list ──

    def _refresh_profile_list(self) -> None:
        if self._registry:
            names = self._registry.list()
            self._profile_dropdown.options = [ft.dropdown.Option(n) for n in sorted(names)]
            if self._state.active_profile_name:
                self._profile_dropdown.value = self._state.active_profile_name

    # ── Device list ──

    def _refresh_device_lists(self) -> None:
        inputs = self._device_monitor.list_input_devices()
        outputs = self._device_monitor.list_output_devices()

        self._input_dropdown.options = [ft.dropdown.Option("default")] + [
            ft.dropdown.Option(f"hw:{d['card']},{d['device']}") for d in inputs
        ]
        self._output_dropdown.options = [ft.dropdown.Option("default")] + [
            ft.dropdown.Option(f"hw:{d['card']},{d['device']}") for d in outputs
        ]
        self._input_dropdown.value = self._state.selected_input_device
        self._output_dropdown.value = self._state.selected_output_device

    def _on_refresh_devices(self, _e: ft.ControlEvent | None = None) -> None:
        self._refresh_device_lists()
        self._page.update()

    # ── Start / Stop ──

    def _on_start(self, _e: ft.ControlEvent | None = None) -> None:
        if self._state.mode == PipelineMode.REMOTE:
            return

        profile_name = self._profile_dropdown.value or "clean"
        profile: Profile | None = None
        if self._registry:
            profile = self._registry.get(profile_name)
        if profile is None:
            profile = Profile(name="clean", effects=[])

        input_dev = self._input_dropdown.value or "default"
        output_dev = self._output_dropdown.value or "default"

        try:
            self._pipeline.start(
                profile,
                sample_rate=self._state.sample_rate,
                buffer_size=self._state.buffer_size,
                input_device=input_dev,
                output_device=output_dev,
            )
            self._state.pipeline_running = True
            self._state.pipeline_state = self._pipeline.state.value
            self._state.active_profile_name = profile_name
            self._start_btn.disabled = True
            self._stop_btn.disabled = False
            self._update_status_display()
            self.start_level_polling()
        except Exception:
            logger.error("Failed to start pipeline", exc_info=True)

        self._page.update()

    def _on_stop(self, _e: ft.ControlEvent | None = None) -> None:
        if self._state.mode == PipelineMode.REMOTE:
            return

        self._pipeline.stop()
        self._state.pipeline_running = False
        self._state.pipeline_state = "STOPPED"
        self._start_btn.disabled = False
        self._stop_btn.disabled = True
        self.stop_level_polling()
        self._update_status_display()
        self._page.update()

    # ── Monitor toggle ──

    def _on_monitor_toggle(self, e: ft.ControlEvent) -> None:
        enabled = e.control.value
        self._state.monitor_enabled = enabled

        if self._state.mode == PipelineMode.EMBEDDED:
            self._pipeline.set_monitor_enabled(enabled)
        elif self._state.mode == PipelineMode.REMOTE and self._ipc_client:

            async def _set() -> None:
                await self._ipc_client.set_monitor(enabled)

            asyncio.ensure_future(_set())

    # ── Status polling (remote mode) ──

    def _start_status_polling(self) -> None:
        if self._status_polling:
            return
        self._status_polling = True

        def _poll() -> None:
            while self._status_polling:
                if self._ipc_client:

                    async def _fetch() -> None:
                        result = await self._ipc_client.get_status()
                        if result.get("ok"):
                            data = result["data"]
                            self._state.pipeline_state = data.get("state", "UNKNOWN")
                            self._state.active_profile_name = data.get("active_profile", "")
                            self._state.uptime_seconds = data.get("uptime_seconds", 0)
                            self._state.monitor_enabled = data.get("monitor_enabled", True)
                            self._state.pipeline_running = data.get("state") == "RUNNING"
                            self._update_status_display()
                            self._page.update()

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(_fetch())
                        else:
                            loop.run_until_complete(_fetch())
                    except Exception:
                        logger.debug("Status poll failed", exc_info=True)
                time.sleep(STATUS_POLL_INTERVAL)

        thread = threading.Thread(target=_poll, daemon=True)
        thread.start()

    # ── Status display ──

    def _update_status_display(self) -> None:
        self._status_text.value = f"Status: {self._state.pipeline_state}"
        if self._state.uptime_seconds > 0:
            mins, secs = divmod(self._state.uptime_seconds, 60)
            hours, mins = divmod(mins, 60)
            self._uptime_text.value = f"Uptime: {hours}h {mins:02d}m"
        else:
            self._uptime_text.value = "Uptime: —"
        self._monitor_switch.value = self._state.monitor_enabled

    # ── Level meter polling ──

    def start_level_polling(self) -> None:
        """Start async level meter polling at ~60ms interval (≥15fps)."""
        if self._level_polling:
            return
        self._level_polling = True

        async def _poll_levels() -> None:
            while self._level_polling:
                if self._state.mode == PipelineMode.EMBEDDED:
                    in_lvl = self._pipeline.input_level
                    out_lvl = self._pipeline.output_level
                else:
                    in_lvl = self._state.input_level
                    out_lvl = self._state.output_level

                self._input_meter.value = in_lvl
                self._output_meter.value = out_lvl
                self._input_meter.color = _level_color(in_lvl)
                self._output_meter.color = _level_color(out_lvl)
                self._input_db_label.value = _level_to_db(in_lvl)
                self._output_db_label.value = _level_to_db(out_lvl)

                import contextlib

                with contextlib.suppress(Exception):
                    self._page.update()
                await asyncio.sleep(0.06)

        self._page.run_task(_poll_levels)

    def stop_level_polling(self) -> None:
        self._level_polling = False

    def set_ipc_client(self, client: Any) -> None:
        """Set the IPC client for remote mode operations."""
        self._ipc_client = client
