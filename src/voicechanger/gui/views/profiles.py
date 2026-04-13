"""Profiles view — browse, activate, delete, export, import profiles."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import flet as ft

from voicechanger.gui.logic import GuiEffectState
from voicechanger.gui.state import EditingProfile, GuiState, PipelineMode, generate_draft_name
from voicechanger.profile import Profile
from voicechanger.registry import ProfileRegistry

if TYPE_CHECKING:
    from voicechanger.gui.ipc_client import IpcClient

logger = logging.getLogger(__name__)


class ProfilesView(ft.Column):
    """Profile browser and manager — grouped list, actions, detail panel."""

    def __init__(
        self,
        state: GuiState,
        registry: ProfileRegistry,
        *,
        navigate_to_editor: Any | None = None,
        show_snackbar: Any | None = None,
    ) -> None:
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self._state = state
        self._registry = registry
        self._ipc_client: IpcClient | None = None
        self._navigate_to_editor = navigate_to_editor
        self._show_snackbar = show_snackbar

        self._selected_name: str | None = None
        self._file_picker = ft.FilePicker()

        self._build_ui()
        self._refresh_list()

    def set_ipc_client(self, client: IpcClient) -> None:
        self._ipc_client = client

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._profile_list = ft.ListView(expand=True, spacing=2, padding=10)

        self._detail_name = ft.Text("", size=18, weight=ft.FontWeight.BOLD)
        self._detail_type = ft.Text("", size=12, italic=True)
        self._detail_author = ft.Text("")
        self._detail_description = ft.Text("")
        self._detail_effects = ft.Text("", size=12)

        self._btn_activate = ft.ElevatedButton(
            "Activate", icon=ft.Icons.PLAY_ARROW, on_click=self._on_activate, disabled=True,
        )
        self._btn_edit = ft.ElevatedButton(
            "Edit", icon=ft.Icons.EDIT, on_click=self._on_edit, disabled=True,
        )
        self._btn_delete = ft.ElevatedButton(
            "Delete", icon=ft.Icons.DELETE, on_click=self._on_delete, disabled=True,
        )
        self._btn_export = ft.ElevatedButton(
            "Export", icon=ft.Icons.DOWNLOAD, on_click=self._on_export, disabled=True,
        )
        self._btn_import = ft.ElevatedButton(
            "Import", icon=ft.Icons.UPLOAD, on_click=self._on_import,
        )
        self._btn_refresh = ft.IconButton(
            icon=ft.Icons.REFRESH, tooltip="Reload profiles", on_click=self._on_refresh,
        )

        detail_panel = ft.Column(
            [
                self._detail_name,
                self._detail_type,
                self._detail_author,
                self._detail_description,
                ft.Divider(),
                self._detail_effects,
                ft.Divider(),
                ft.Row(
                    [self._btn_activate, self._btn_edit, self._btn_delete],
                    spacing=8,
                ),
                ft.Row([self._btn_export, self._btn_import], spacing=8),
            ],
            expand=True,
            spacing=8,
        )

        toolbar = ft.Row(
            [ft.Text("Profiles", size=20, weight=ft.FontWeight.BOLD), self._btn_refresh],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.controls = [
            toolbar,
            ft.Row(
                [
                    ft.Container(content=self._profile_list, width=250, expand=False),
                    ft.VerticalDivider(width=1),
                    ft.Container(content=detail_panel, expand=True, padding=10),
                ],
                expand=True,
            ),
            self._file_picker,
        ]

    # ── List management ──────────────────────────────────────────────

    def _refresh_list(self) -> None:
        self._profile_list.controls.clear()

        builtin_names = [n for n in self._registry.list() if self._registry.is_builtin(n)]
        user_names = [n for n in self._registry.list() if not self._registry.is_builtin(n)]

        if builtin_names:
            self._profile_list.controls.append(
                ft.Text("Built-in", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_500)
            )
            for name in builtin_names:
                self._profile_list.controls.append(self._make_list_tile(name, "builtin"))

        if user_names:
            self._profile_list.controls.append(
                ft.Text("User", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_500)
            )
            for name in user_names:
                self._profile_list.controls.append(self._make_list_tile(name, "user"))

    def _make_list_tile(self, name: str, ptype: str) -> ft.ListTile:
        is_active = name == self._state.active_profile_name
        return ft.ListTile(
            title=ft.Text(name, weight=ft.FontWeight.BOLD if is_active else None),
            subtitle=ft.Text(ptype, size=10),
            leading=ft.Icon(
                ft.Icons.LOCK if ptype == "builtin" else ft.Icons.PERSON,
                size=16,
            ),
            trailing=ft.Icon(ft.Icons.CHECK_CIRCLE, size=16) if is_active else None,
            selected=name == self._selected_name,
            on_click=lambda e, n=name: self._on_select(n),
        )

    def _on_select(self, name: str) -> None:
        self._selected_name = name
        profile = self._registry.get(name)
        if profile is None:
            return

        self._detail_name.value = profile.name
        self._detail_type.value = self._registry.get_type(name)
        self._detail_author.value = f"Author: {profile.author}" if profile.author else ""
        self._detail_description.value = profile.description or "(no description)"
        self._detail_effects.value = (
            f"Effects: {len(profile.effects)}\n"
            + "\n".join(f"  • {e['type']}" for e in profile.effects)
        )
        is_builtin = self._registry.is_builtin(name)

        self._btn_activate.disabled = False
        self._btn_edit.disabled = False
        self._btn_delete.disabled = is_builtin
        self._btn_export.disabled = False

        self._refresh_list()
        if self.page:
            self.page.update()

    # ── Actions ──────────────────────────────────────────────────────

    def _on_activate(self, _e: ft.ControlEvent) -> None:
        if self._selected_name is None:
            return

        profile = self._registry.get(self._selected_name)
        if profile is None:
            return

        if self._state.mode == PipelineMode.REMOTE and self._ipc_client:
            async def _activate() -> None:
                try:
                    await self._ipc_client.switch_profile(self._selected_name)
                    self._state.active_profile_name = self._selected_name
                    self._refresh_list()
                    if self._show_snackbar:
                        self._show_snackbar(f"Activated: {self._selected_name}")
                    if self.page:
                        self.page.update()
                except Exception as exc:
                    logger.error("Failed to activate profile via IPC: %s", exc)
                    if self._show_snackbar:
                        self._show_snackbar(f"Error: {exc}", error=True)

            if self.page:
                self.page.run_task(_activate)
        else:
            # Embedded mode — pipeline switch handled by control view
            self._state.active_profile_name = self._selected_name
            self._refresh_list()
            if self._show_snackbar:
                self._show_snackbar(f"Activated: {self._selected_name}")
            if self.page:
                self.page.update()

    def _on_edit(self, _e: ft.ControlEvent) -> None:
        if self._selected_name is None:
            return

        profile = self._registry.get(self._selected_name)
        if profile is None:
            return

        is_builtin = self._registry.is_builtin(self._selected_name)

        if is_builtin:
            draft_name = generate_draft_name(
                self._selected_name, self._registry.list()
            )
            editing = EditingProfile(
                name=draft_name,
                original_name=self._selected_name,
                is_builtin_fork=True,
                effects=[
                    GuiEffectState(type=e["type"], params=dict(e.get("params", {})))
                    for e in profile.effects
                ],
                author=profile.author,
                description=profile.description,
            )
        else:
            editing = EditingProfile(
                name=self._selected_name,
                original_name=self._selected_name,
                effects=[
                    GuiEffectState(type=e["type"], params=dict(e.get("params", {})))
                    for e in profile.effects
                ],
                author=profile.author,
                description=profile.description,
            )

        self._state.editing_profile = editing
        if self._navigate_to_editor:
            self._navigate_to_editor()

    def _on_delete(self, _e: ft.ControlEvent) -> None:
        if self._selected_name is None:
            return
        if self._registry.is_builtin(self._selected_name):
            return

        name = self._selected_name

        def _confirm_delete(e: ft.ControlEvent) -> None:
            try:
                self._registry.delete(name)
                self._selected_name = None
                self._refresh_list()
                if self._show_snackbar:
                    self._show_snackbar(f"Deleted: {name}")
            except Exception as exc:
                logger.error("Delete failed: %s", exc)
                if self._show_snackbar:
                    self._show_snackbar(f"Error: {exc}", error=True)
            if self.page:
                self.page.close(dialog)
                self.page.update()

        def _cancel(e: ft.ControlEvent) -> None:
            if self.page:
                self.page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Delete '{name}'?"),
            content=ft.Text("This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.TextButton("Delete", on_click=_confirm_delete),
            ],
        )
        if self.page:
            self.page.open(dialog)

    def _on_export(self, _e: ft.ControlEvent) -> None:
        if self._selected_name is None:
            return
        if not self.page:
            return
        path = self._file_picker.save_file(
            dialog_title="Export profile",
            file_name=f"{self._selected_name}.json",
            allowed_extensions=["json"],
        )
        if path:
            profile = self._registry.get(self._selected_name)
            if profile:
                try:
                    profile.save(Path(path))
                    if self._show_snackbar:
                        self._show_snackbar(f"Exported: {self._selected_name}")
                except Exception as exc:
                    logger.error("Export failed: %s", exc)
                    if self._show_snackbar:
                        self._show_snackbar(f"Export error: {exc}", error=True)

    def _on_import(self, _e: ft.ControlEvent) -> None:
        if not self.page:
            return
        files = self._file_picker.pick_files(
            dialog_title="Import profile",
            allowed_extensions=["json"],
            allow_multiple=False,
        )
        if files:
            try:
                fpath = Path(files[0].path)
                profile = Profile.load(fpath)
                if self._registry.exists(profile.name):
                    if self._show_snackbar:
                        self._show_snackbar(
                            f"Profile '{profile.name}' already exists", error=True
                        )
                    return
                self._registry.create(profile)
                self._refresh_list()
                if self._show_snackbar:
                    self._show_snackbar(f"Imported: {profile.name}")
                if self.page:
                    self.page.update()
            except Exception as exc:
                logger.error("Import failed: %s", exc)
                if self._show_snackbar:
                    self._show_snackbar(f"Import error: {exc}", error=True)

    def _on_refresh(self, _e: ft.ControlEvent) -> None:
        self._registry.reload()
        self._refresh_list()
        if self.page:
            self.page.update()
