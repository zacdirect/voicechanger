"""Control view — service start/stop, device selection, monitor toggle, status display."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import flet as ft

from voicechanger.device import DeviceMonitor
from voicechanger.gui.ipc_client import IpcClient
from voicechanger.gui.state import GuiState
from voicechanger.meter import LevelMeter
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
    ipc_client: IpcClient,
    registry: ProfileRegistry | None = None,
    start_service: Callable[[], Awaitable[bool]] | None = None,
    stop_service: Callable[[], Awaitable[None]] | None = None,
) -> ft.Control:
    """Build and return the Control view layout."""
    return ControlView(
        page, state, ipc_client=ipc_client, registry=registry,
        start_service=start_service, stop_service=stop_service,
    )


class ControlView(ft.Column):
    """Service control — start/stop, devices, monitor, status."""

    def __init__(
        self,
        page: ft.Page,
        state: GuiState,
        *,
        ipc_client: IpcClient,
        registry: ProfileRegistry | None = None,
        persist_settings: Any | None = None,
        start_service: Callable[[], Awaitable[bool]] | None = None,
        stop_service: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        super().__init__(expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)
        self._page = page
        self._state = state
        self._ipc = ipc_client
        self._registry = registry
        self._persist_settings = persist_settings
        self._start_service = start_service
        self._stop_service = stop_service
        self._device_monitor = DeviceMonitor()
        self._input_tree: dict[str, list[tuple[str, str]]] = {}
        self._output_tree: dict[str, list[tuple[str, str]]] = {}
        self._status_polling = False
        self._level_polling = False
        self._level_meter = LevelMeter()

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
        self._input_card_dropdown = ft.Dropdown(
            label="Input Card",
            expand=True,
            on_select=lambda _e: self._on_card_change("input"),
        )
        self._input_sub_dropdown = ft.Dropdown(label="Input Device", expand=True, visible=False)
        self._output_card_dropdown = ft.Dropdown(
            label="Output Card",
            expand=True,
            on_select=lambda _e: self._on_card_change("output"),
        )
        self._output_sub_dropdown = ft.Dropdown(label="Output Device", expand=True, visible=False)
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
                            [
                                self._input_card_dropdown,
                                self._output_card_dropdown,
                                self._refresh_btn,
                            ],
                            spacing=8,
                        ),
                        ft.Row(
                            [self._input_sub_dropdown, self._output_sub_dropdown],
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

        # ── Level meter ──
        self._mic_meter = ft.ProgressBar(value=0, width=300, color=ft.Colors.GREEN)
        self._mic_db_label = ft.Text("-∞ dB", size=11, width=60)

        meter_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("MIC LEVEL", weight=ft.FontWeight.BOLD, size=16),
                        ft.Row([
                            self._mic_meter,
                            self._mic_db_label,
                        ]),
                    ],
                    spacing=8,
                ),
                padding=16,
            ),
        )

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
        self._input_tree = self._device_monitor.input_device_tree()
        self._output_tree = self._device_monitor.output_device_tree()

        default_label = self._device_monitor.DEFAULT_LABEL

        input_cards = [default_label, *self._input_tree.keys()]
        output_cards = [default_label, *self._output_tree.keys()]

        self._input_card_dropdown.options = [
            ft.dropdown.Option(key=card, text=card) for card in input_cards
        ]
        self._output_card_dropdown.options = [
            ft.dropdown.Option(key=card, text=card) for card in output_cards
        ]

        self._input_card_dropdown.value = default_label
        self._output_card_dropdown.value = default_label
        self._on_card_change("input")
        self._on_card_change("output")

        self._apply_saved_device_selection("input", self._state.selected_input_device)
        self._apply_saved_device_selection("output", self._state.selected_output_device)

    def _apply_saved_device_selection(self, direction: str, selected_device: str) -> None:
        default_label = self._device_monitor.DEFAULT_LABEL
        if not selected_device or selected_device == "default":
            return

        if direction == "input":
            card_dropdown = self._input_card_dropdown
            tree = self._input_tree
            default_name = self._device_monitor.default_input_name()
        else:
            card_dropdown = self._output_card_dropdown
            tree = self._output_tree
            default_name = self._device_monitor.default_output_name()

        if selected_device == default_name:
            card_dropdown.value = default_label
            self._on_card_change(direction)
            return

        for card_name, entries in tree.items():
            for _sub_label, raw_name in entries:
                if raw_name == selected_device:
                    card_dropdown.value = card_name
                    self._on_card_change(direction)
                    if direction == "input":
                        self._input_sub_dropdown.value = raw_name
                    else:
                        self._output_sub_dropdown.value = raw_name
                    return

    def _on_card_change(self, direction: str) -> None:
        default_label = self._device_monitor.DEFAULT_LABEL

        if direction == "input":
            card_dropdown = self._input_card_dropdown
            sub_dropdown = self._input_sub_dropdown
            tree = self._input_tree
        else:
            card_dropdown = self._output_card_dropdown
            sub_dropdown = self._output_sub_dropdown
            tree = self._output_tree

        card_value = card_dropdown.value or default_label
        if card_value == default_label or card_value not in tree:
            sub_dropdown.options = []
            sub_dropdown.value = None
            sub_dropdown.visible = False
            if self._page:
                self._page.update()
            return

        entries = tree[card_value]
        sub_dropdown.options = [
            ft.dropdown.Option(key=raw_name, text=sub_label)
            for sub_label, raw_name in entries
        ]
        sub_dropdown.value = entries[0][1] if entries else None
        sub_dropdown.visible = True
        if self._page:
            self._page.update()

    def _resolve_device(self, direction: str) -> str:
        default_label = self._device_monitor.DEFAULT_LABEL

        if direction == "input":
            card_value = self._input_card_dropdown.value or default_label
            sub_value = self._input_sub_dropdown.value
        else:
            card_value = self._output_card_dropdown.value or default_label
            sub_value = self._output_sub_dropdown.value

        if card_value == default_label:
            return "default"

        return sub_value or "default"

    def _on_refresh_devices(self, _e: ft.ControlEvent | None = None) -> None:
        self._refresh_device_lists()
        self._page.update()

    # ── Start / Stop ──

    def _on_start(self, _e: ft.ControlEvent | None = None) -> None:
        """Spawn the service subprocess and connect IPC."""
        if self._start_service is None:
            return

        self._start_btn.disabled = True
        self._state.pipeline_state = "STARTING"
        self._update_status_display()
        self._page.update()

        async def _do_start() -> None:
            ok = await self._start_service()
            if ok:
                self._state.pipeline_running = True
                self._state.pipeline_state = "RUNNING"
                self._stop_btn.disabled = False
                self._start_status_polling()
                self.start_level_polling()
            else:
                self._state.pipeline_state = "ERROR"
                self._start_btn.disabled = False
            self._update_status_display()
            self._page.update()

        self._page.run_task(_do_start)

    def _on_stop(self, _e: ft.ControlEvent | None = None) -> None:
        self._stop_btn.disabled = True
        self._page.update()

        async def _do_stop() -> None:
            if self._stop_service is not None:
                await self._stop_service()
            self._status_polling = False
            self.stop_level_polling()
            self._state.pipeline_running = False
            self._state.pipeline_state = "STOPPED"
            self._start_btn.disabled = False
            self._update_status_display()
            self._page.update()

        self._page.run_task(_do_stop)

    # ── Monitor toggle ──

    def _on_monitor_toggle(self, e: ft.ControlEvent) -> None:
        enabled = e.control.value
        self._state.monitor_enabled = enabled

        async def _set() -> None:
            await self._ipc.set_monitor(enabled)

        self._page.run_task(_set)

    # ── Status polling ──

    def _start_status_polling(self) -> None:
        if self._status_polling:
            return
        self._status_polling = True

        async def _poll() -> None:
            while self._status_polling:
                try:
                    result = await self._ipc.get_status()
                    if result.get("ok"):
                        data = result["data"]
                        self._state.pipeline_state = data.get("state", "UNKNOWN")
                        self._state.active_profile_name = data.get("active_profile", "")
                        self._state.uptime_seconds = data.get("uptime_seconds", 0)
                        self._state.monitor_enabled = data.get("monitor_enabled", True)
                        self._state.pipeline_running = data.get("state") == "RUNNING"

                        self._stop_btn.disabled = not self._state.pipeline_running
                        self._update_status_display()
                        self._page.update()
                except Exception:
                    logger.debug("Status poll failed", exc_info=True)
                await asyncio.sleep(STATUS_POLL_INTERVAL)

        self._page.run_task(_poll)

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
        """Start OS-level metering and async UI updates at ~60ms."""
        if self._level_polling:
            return
        self._level_meter.start()
        self._level_polling = True

        async def _poll_levels() -> None:
            while self._level_polling:
                lvl = self._level_meter.input_level

                self._mic_meter.value = lvl
                self._mic_meter.color = _level_color(lvl)
                self._mic_db_label.value = _level_to_db(lvl)

                import contextlib

                with contextlib.suppress(Exception):
                    self._page.update()
                await asyncio.sleep(0.06)

        self._page.run_task(_poll_levels)

    def stop_level_polling(self) -> None:
        self._level_polling = False
        self._level_meter.stop()

    def shutdown(self) -> None:
        """Stop background polling during GUI shutdown."""
        self._status_polling = False
        self.stop_level_polling()
        self._level_meter.stop()
