"""Editor view — effect chain editor with sliders, preview, save, builtin auto-fork."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import flet as ft

from voicechanger.effects import EFFECT_REGISTRY
from voicechanger.gui.logic import (
    GuiEffectState,
    PreviewManager,
    build_profile_from_gui_state,
    param_to_slider,
    slider_to_param,
)
from voicechanger.gui.state import EditingProfile, GuiState, generate_draft_name
from voicechanger.profile import NAME_REGEX

if TYPE_CHECKING:
    from voicechanger.registry import ProfileRegistry

logger = logging.getLogger(__name__)


class EditorView(ft.Column):
    """Effect chain editor with sliders, live preview, and save actions."""

    def __init__(
        self,
        state: GuiState,
        registry: ProfileRegistry,
        *,
        show_snackbar: Any | None = None,
        on_save: Any | None = None,
    ) -> None:
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self._state = state
        self._registry = registry
        self._show_snackbar = show_snackbar
        self._on_save_callback = on_save
        self._preview = PreviewManager()

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._name_field = ft.TextField(
            label="Profile name", width=300, on_change=self._on_name_change,
        )
        self._author_field = ft.TextField(label="Author", width=200)
        self._desc_field = ft.TextField(label="Description", width=400)
        self._fork_banner = ft.Banner(
            content=ft.Text("Editing a built-in profile. Changes will be saved as a new profile."),
            leading=ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE),
            bgcolor=ft.Colors.BLUE_900,
            actions=[ft.TextButton("OK", on_click=lambda _: self._dismiss_banner())],
            open=False,
        )

        effect_types = sorted(EFFECT_REGISTRY.keys())
        self._effect_dropdown = ft.Dropdown(
            label="Add effect",
            options=[ft.dropdown.Option(t) for t in effect_types],
            width=200,
        )
        self._btn_add_effect = ft.ElevatedButton(
            "Add", icon=ft.Icons.ADD, on_click=self._on_add_effect,
        )

        self._effect_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        self._btn_preview = ft.ElevatedButton(
            "Preview", icon=ft.Icons.PLAY_ARROW, on_click=self._on_preview_toggle,
        )
        self._btn_save = ft.ElevatedButton(
            "Save", icon=ft.Icons.SAVE, on_click=self._on_save,
        )
        self._btn_save_as = ft.ElevatedButton(
            "Save As…", icon=ft.Icons.SAVE_AS, on_click=self._on_save_as,
        )

        header = ft.Row(
            [
                self._name_field,
                self._author_field,
                self._desc_field,
            ],
            spacing=8,
        )

        add_row = ft.Row([self._effect_dropdown, self._btn_add_effect], spacing=8)

        actions = ft.Row(
            [self._btn_preview, self._btn_save, self._btn_save_as], spacing=8
        )

        self.controls = [
            ft.Text("Effect Editor", size=20, weight=ft.FontWeight.BOLD),
            self._fork_banner,
            header,
            ft.Divider(),
            add_row,
            self._effect_list,
            ft.Divider(),
            actions,
        ]

    # ── State sync ───────────────────────────────────────────────────

    def load_editing_profile(self) -> None:
        """Load the current editing profile from GuiState into the UI."""
        ep = self._state.editing_profile
        if ep is None:
            self._name_field.value = ""
            self._author_field.value = ""
            self._desc_field.value = ""
            self._effect_list.controls.clear()
            self._fork_banner.open = False
            return

        self._name_field.value = ep.name
        self._author_field.value = ep.author
        self._desc_field.value = ep.description
        self._fork_banner.open = ep.is_builtin_fork

        self._effect_list.controls.clear()
        for effect in ep.effects:
            self._effect_list.controls.append(
                self._build_effect_card(effect)
            )

        try:
            if self.page:
                self.page.update()
        except RuntimeError:
            pass  # Not yet mounted — update will happen on attach

    def _sync_effects_to_state(self) -> None:
        """Sync current slider values back to editing_profile."""
        ep = self._state.editing_profile
        if ep is None:
            return
        ep.name = self._name_field.value or ""
        ep.author = self._author_field.value or ""
        ep.description = self._desc_field.value or ""
        ep.is_dirty = True

    # ── Effect card builder ──────────────────────────────────────────

    def _build_effect_card(self, effect: GuiEffectState) -> ft.Card:
        schema = EFFECT_REGISTRY.get(effect.type, {}).get("params", {})
        sliders: list[ft.Control] = []

        for param_name, param_schema in schema.items():
            current = effect.params.get(param_name, param_schema.get("default", 0.0))
            slider_val = param_to_slider(effect.type, param_name, current)

            label = ft.Text(f"{param_name}: {current:.2f}", size=12, width=180)
            slider = ft.Slider(
                min=0, max=100, value=slider_val, label=f"{param_name}",
                expand=True,
                on_change=lambda e, eff=effect, pn=param_name, lbl=label: (
                    self._on_slider_change(e, eff, pn, lbl)
                ),
            )
            sliders.append(ft.Row([label, slider]))

        def _remove(e: ft.ControlEvent, eff: GuiEffectState = effect) -> None:
            ep = self._state.editing_profile
            if ep and eff in ep.effects:
                ep.effects.remove(eff)
                self._rebuild_effect_list()

        header = ft.Row(
            [
                ft.Text(effect.type, weight=ft.FontWeight.BOLD),
                ft.IconButton(icon=ft.Icons.DELETE, on_click=_remove, icon_size=16),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        return ft.Card(
            content=ft.Container(
                content=ft.Column([header, *sliders], spacing=4),
                padding=10,
            ),
        )

    def _on_slider_change(
        self,
        e: ft.ControlEvent,
        effect: GuiEffectState,
        param_name: str,
        label: ft.Text,
    ) -> None:
        slider_val = int(float(e.data))
        new_val = slider_to_param(effect.type, param_name, slider_val)
        effect.params[param_name] = new_val
        label.value = f"{param_name}: {new_val:.2f}"
        self._sync_effects_to_state()
        self._notify_preview()
        if self.page:
            self.page.update()

    def _notify_preview(self) -> None:
        """If preview is active, restart it with current effects."""
        if self._preview.is_active:
            ep = self._state.editing_profile
            if ep:
                self._preview.update_preview(ep.effects)

    def _rebuild_effect_list(self) -> None:
        ep = self._state.editing_profile
        self._effect_list.controls.clear()
        if ep:
            for effect in ep.effects:
                self._effect_list.controls.append(self._build_effect_card(effect))
        self._notify_preview()
        if self.page:
            self.page.update()

    # ── Actions ──────────────────────────────────────────────────────

    def _dismiss_banner(self) -> None:
        self._fork_banner.open = False
        if self.page:
            self.page.update()

    def _on_name_change(self, _e: ft.ControlEvent) -> None:
        raw = self._name_field.value or ""
        slugified = raw.lower().replace(" ", "-").replace("_", "-")
        if slugified != raw:
            self._name_field.value = slugified
        self._validate_name()
        self._sync_effects_to_state()

    def _validate_name(self) -> None:
        """Check profile name and show inline error / disable Save."""
        name = self._name_field.value or ""
        if not name:
            self._name_field.error_text = None
            self._btn_save.disabled = True
        elif NAME_REGEX.match(name):
            self._name_field.error_text = None
            self._btn_save.disabled = False
        else:
            self._name_field.error_text = "Lowercase a-z, 0-9, hyphens; 2-64 chars"
            self._btn_save.disabled = True
        try:
            if self.page:
                self.page.update()
        except RuntimeError:
            pass

    def _on_add_effect(self, _e: ft.ControlEvent) -> None:
        if not self._effect_dropdown.value:
            return
        ep = self._state.editing_profile
        if ep is None:
            ep = EditingProfile(name="untitled", original_name="", effects=[])
            self._state.editing_profile = ep

        effect_type = self._effect_dropdown.value
        schema = EFFECT_REGISTRY.get(effect_type, {}).get("params", {})
        defaults = {k: v.get("default", 0.0) for k, v in schema.items()}
        new_effect = GuiEffectState(type=effect_type, params=defaults)
        ep.effects.append(new_effect)
        self._effect_list.controls.append(self._build_effect_card(new_effect))
        ep.is_dirty = True
        self._notify_preview()
        if self.page:
            self.page.update()

    def _on_preview_toggle(self, _e: ft.ControlEvent) -> None:
        if self._preview.is_active:
            self._preview.stop_preview()
            self._btn_preview.text = "Preview"
            self._btn_preview.icon = ft.Icons.PLAY_ARROW
        else:
            ep = self._state.editing_profile
            if ep:
                self._preview.start_preview(ep.effects)
            self._btn_preview.text = "Stop Preview"
            self._btn_preview.icon = ft.Icons.STOP
        if self.page:
            self.page.update()

    def _on_save(self, _e: ft.ControlEvent) -> None:
        ep = self._state.editing_profile
        if ep is None:
            return

        self._sync_effects_to_state()
        profile = build_profile_from_gui_state(
            name=ep.name,
            author=ep.author,
            description=ep.description,
            effects=ep.effects,
        )

        try:
            if ep.is_builtin_fork or not self._registry.exists(ep.name):
                self._registry.create(profile)
                ep.is_builtin_fork = False
                ep.original_name = ep.name
            else:
                self._registry.update(profile)
            ep.is_dirty = False
            if self._show_snackbar:
                self._show_snackbar(f"Saved: {ep.name}")
            if self._on_save_callback:
                self._on_save_callback()
        except Exception as exc:
            logger.error("Save failed: %s", exc)
            if self._show_snackbar:
                self._show_snackbar(f"Error: {exc}", error=True)

    def _on_save_as(self, _e: ft.ControlEvent) -> None:
        ep = self._state.editing_profile
        if ep is None:
            return

        self._sync_effects_to_state()
        existing = self._registry.list()

        def _do_save_as(e: ft.ControlEvent) -> None:
            new_name = name_field.value
            if not new_name:
                return
            profile = build_profile_from_gui_state(
                name=new_name,
                author=ep.author,
                description=ep.description,
                effects=ep.effects,
            )
            try:
                self._registry.create(profile)
                ep.name = new_name
                ep.original_name = new_name
                ep.is_builtin_fork = False
                ep.is_dirty = False
                self._name_field.value = new_name
                if self._show_snackbar:
                    self._show_snackbar(f"Saved as: {new_name}")
                if self._on_save_callback:
                    self._on_save_callback()
            except Exception as exc:
                logger.error("Save As failed: %s", exc)
                if self._show_snackbar:
                    self._show_snackbar(f"Error: {exc}", error=True)
            if self.page:
                self.page.pop_dialog()
                self.page.update()

        def _cancel(e: ft.ControlEvent) -> None:
            if self.page:
                self.page.pop_dialog()

        suggested = generate_draft_name(ep.name, existing) if ep.is_builtin_fork else ep.name
        name_field = ft.TextField(label="Profile name", value=suggested, autofocus=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Save As"),
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=_cancel),
                ft.TextButton("Save", on_click=_do_save_as),
            ],
        )
        if self.page:
            self.page.show_dialog(dlg)
