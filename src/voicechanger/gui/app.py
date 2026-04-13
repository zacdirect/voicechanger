"""Desktop GUI — NavigationRail shell with 4-view routing (Flet / Material Design 3)."""

from __future__ import annotations

import logging
from typing import Any

import flet as ft

from voicechanger.gui.state import GuiState, PipelineMode

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

        self.page.title = "Voice Changer"
        self.page.window.width = 900
        self.page.window.height = 650
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.on_disconnect = lambda _: self._on_close()

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

        mode_label = (
            "Remote" if self.state.mode == PipelineMode.REMOTE else "Embedded"
        )
        mode_chip = ft.Chip(
            label=ft.Text(mode_label, size=11),
            bgcolor=(
                ft.Colors.AMBER_900
                if self.state.mode == PipelineMode.REMOTE
                else ft.Colors.GREEN_900
            ),
        )

        self.page.add(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [self._rail, ft.Container(content=mode_chip, padding=8)],
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

    # ── Lifecycle ────────────────────────────────────────────────────

    def _on_close(self) -> None:
        pass

    # ── Helpers ───────────────────────────────────────────────────────

    def show_snackbar(self, message: str, *, error: bool = False) -> None:
        self.page.open(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ERROR if error else None,
            )
        )
