"""Desktop GUI — NavigationRail shell with 4-view routing (Flet / Material Design 3)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import flet as ft

from voicechanger.gui.state import GuiState

logger = logging.getLogger(__name__)


class VoiceChangerApp:
    """Desktop application shell — NavigationRail with lazy view loading."""

    VIEW_LABELS = ("Control", "Profiles", "Editor", "Tools")
    VIEW_ICONS = (ft.Icons.TUNE, ft.Icons.LIBRARY_MUSIC, ft.Icons.EDIT, ft.Icons.BUILD)
    VIEW_ICONS_SELECTED = (
        ft.Icons.TUNE,
        ft.Icons.LIBRARY_MUSIC,
        ft.Icons.EDIT,
        ft.Icons.BUILD,
    )

    def __init__(self, page: ft.Page, *, state: GuiState) -> None:
        self.page = page
        self.state = state
        self._cleanup_callbacks: list[Any] = []
        self._closed = False
        self._closing = False

        self.page.title = "Voice Changer"
        self.page.window.width = 900
        self.page.window.height = 650
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.on_disconnect = lambda _: self._on_close()
        self.page.window.prevent_close = True
        self.page.window.on_event = self._on_window_event

        self._views: dict[int, ft.Control] = {}
        self._view_builders: dict[int, Any] = {}
        self._view_content = ft.Column(expand=True)

        self._build_ui()

    def register_view_builder(self, index: int, builder: Any) -> None:
        """Register a callable that returns a ft.Control for a view index."""
        self._view_builders[index] = builder

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        destinations = [
            ft.NavigationRailDestination(
                icon=icon,
                selected_icon=sel_icon,
                label=label,
            )
            for icon, sel_icon, label in zip(
                self.VIEW_ICONS, self.VIEW_ICONS_SELECTED, self.VIEW_LABELS,
                strict=True,
            )
        ]

        self._rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            destinations=destinations,
            on_change=self._on_nav_change,
            min_width=80,
            group_alignment=-0.9,
            expand=True,
        )

        self.page.add(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [self._rail],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        width=100,
                        expand=False,
                    ),
                    ft.VerticalDivider(width=1),
                    ft.Container(content=self._view_content, expand=True, padding=20),
                ],
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )

    # ── Navigation ───────────────────────────────────────────────────

    def _on_nav_change(self, e: ft.ControlEvent) -> None:
        index = int(e.data) if e.data is not None else 0
        self._switch_view(index)

    def _switch_view(self, index: int) -> None:
        if index not in self._views:
            builder = self._view_builders.get(index)
            if builder is not None:
                self._views[index] = builder()
            else:
                self._views[index] = ft.Text(
                    f"{self.VIEW_LABELS[index]} — coming soon",
                    size=18,
                    italic=True,
                )

        self._view_content.controls = [self._views[index]]
        self.page.update()

    def navigate_to(self, index: int) -> None:
        """Programmatically navigate to a view (used by cross-view interactions)."""
        self._rail.selected_index = index
        self._switch_view(index)

    def register_cleanup(self, callback: Any) -> None:
        """Register a callback to run when the GUI is closing."""
        self._cleanup_callbacks.append(callback)

    def _on_window_event(self, e: ft.WindowEvent) -> None:
        if e.type in (ft.WindowEventType.CLOSE, "close"):
            if self._closing:
                return
            self._closing = True

            def _fallback_exit() -> None:
                # If toolkit teardown hangs, force-exit after brief grace period.
                time.sleep(2.0)
                import os
                os._exit(0)

            threading.Thread(target=_fallback_exit, daemon=True).start()

            async def _graceful_close() -> None:
                self._on_close()
                try:
                    await self.page.window.destroy()
                except Exception:
                    logger.warning("Window destroy failed during close", exc_info=True)

            self.page.run_task(_graceful_close)

    # ── Lifecycle ────────────────────────────────────────────────────

    def _on_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception:
                logger.warning("GUI cleanup callback failed", exc_info=True)

    def shutdown(self) -> None:
        """Public shutdown entrypoint for external lifecycle handlers."""
        self._on_close()

    # ── Helpers ───────────────────────────────────────────────────────

    def show_snackbar(self, message: str, *, error: bool = False) -> None:
        if error:
            logger.error("UI error notification: %s", message)
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ERROR if error else None,
            )
        )
