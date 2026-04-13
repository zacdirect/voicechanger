"""Desktop GUI for real-time effect authoring (Flet / Material Design 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import flet as ft

from voicechanger.effects import EFFECT_REGISTRY
from voicechanger.gui.logic import (
    GuiEffectState,
    PreviewManager,
    build_profile_from_gui_state,
    param_to_slider,
    slider_to_param,
)
from voicechanger.profile import Profile, ProfileValidationError


class VoiceChangerApp:
    """Desktop profile authoring application."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "Voice Changer — Profile Editor"
        self.page.window.width = 850
        self.page.window.height = 650
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        self.page.on_disconnect = lambda _: self._on_close()

        self._preview = PreviewManager()
        self._preview_active = False

        self._effect_widgets: list[dict[str, Any]] = []

        self._file_picker = ft.FilePicker()
        self.page.services.append(self._file_picker)

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Profile metadata
        self.name_field = ft.TextField(label="Name", expand=True)
        self.author_field = ft.TextField(label="Author", expand=True)
        self.desc_field = ft.TextField(label="Description", expand=True)

        meta_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Profile Info", weight=ft.FontWeight.BOLD, size=16),
                        ft.Row([self.name_field]),
                        ft.Row([self.author_field, self.desc_field]),
                    ],
                    spacing=8,
                ),
                padding=16,
            ),
        )

        # Effect type selector
        effect_types = sorted(EFFECT_REGISTRY.keys())
        self.effect_dropdown = ft.Dropdown(
            label="Add Effect",
            options=[ft.dropdown.Option(t) for t in effect_types],
            width=220,
        )
        add_btn = ft.ElevatedButton("Add", icon=ft.Icons.ADD, on_click=self._add_effect)
        remove_btn = ft.OutlinedButton(
            "Remove Last", icon=ft.Icons.REMOVE, on_click=self._remove_last_effect
        )

        # Scrollable effects list
        self.effects_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        effects_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Effects Chain", weight=ft.FontWeight.BOLD, size=16),
                                self.effect_dropdown,
                                add_btn,
                                remove_btn,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            spacing=12,
                        ),
                        self.effects_column,
                    ],
                    spacing=8,
                ),
                padding=16,
            ),
            expand=True,
        )

        # Bottom action bar
        self._preview_btn = ft.ElevatedButton(
            "Start Preview",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._toggle_preview,
        )
        self._preview_status = ft.Text("", italic=True)

        action_row = ft.Row(
            [
                ft.ElevatedButton(
                    "Save Profile", icon=ft.Icons.SAVE, on_click=self._save_profile
                ),
                ft.OutlinedButton(
                    "Load Profile", icon=ft.Icons.FOLDER_OPEN, on_click=self._load_profile
                ),
                ft.Container(expand=True),
                self._preview_status,
                self._preview_btn,
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        self.page.add(meta_card, effects_card, action_row)

    # ── Effects ──────────────────────────────────────────────────────

    def _add_effect(self, _e: ft.ControlEvent | None = None) -> None:
        effect_type = self.effect_dropdown.value
        if not effect_type:
            return

        schema = EFFECT_REGISTRY.get(effect_type, {})
        params = schema.get("params", {})

        sliders: dict[str, ft.Slider] = {}
        slider_labels: dict[str, ft.Text] = {}
        slider_rows: list[ft.Control] = []

        for param_name, pschema in params.items():
            default_slider = param_to_slider(effect_type, param_name, pschema.get("default", 0.0))
            label = ft.Text(f"{param_name}: {pschema.get('default', 0.0):.2f}", size=13)
            slider_labels[param_name] = label

            slider = ft.Slider(
                min=0,
                max=100,
                value=default_slider,
                divisions=200,
                label="{value}",
                expand=True,
                on_change_end=lambda e, et=effect_type, pn=param_name: self._on_slider_change(
                    et, pn, e
                ),
            )
            sliders[param_name] = slider
            slider_rows.append(ft.Row([ft.Text(param_name, width=120), slider, label]))

        container = ft.Container(
            content=ft.Column(
                [ft.Text(effect_type, weight=ft.FontWeight.W_600, size=14)] + slider_rows,
                spacing=4,
            ),
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
            border_radius=8,
            padding=12,
        )

        self._effect_widgets.append(
            {
                "type": effect_type,
                "container": container,
                "sliders": sliders,
                "labels": slider_labels,
            }
        )
        self.effects_column.controls.append(container)
        self.page.update()

    def _remove_last_effect(self, _e: ft.ControlEvent | None = None) -> None:
        if self._effect_widgets:
            self._effect_widgets.pop()
            self.effects_column.controls.pop()
            self.page.update()

    def _get_gui_effects(self) -> list[GuiEffectState]:
        result: list[GuiEffectState] = []
        for widget_info in self._effect_widgets:
            effect_type = widget_info["type"]
            params: dict[str, float] = {}
            for param_name, slider in widget_info["sliders"].items():
                params[param_name] = slider_to_param(
                    effect_type, param_name, int(slider.value or 0)
                )
            result.append(GuiEffectState(type=effect_type, params=params))
        return result

    # ── Save / Load ──────────────────────────────────────────────────

    async def _save_profile(self, _e: ft.ControlEvent | None = None) -> None:
        name = (self.name_field.value or "").strip()
        if not name:
            self._show_snackbar("Profile name is required", error=True)
            return

        try:
            effects = self._get_gui_effects()
            profile = build_profile_from_gui_state(
                name=name,
                author=(self.author_field.value or "").strip(),
                description=(self.desc_field.value or "").strip(),
                effects=effects,
            )
        except ProfileValidationError as e:
            self._show_snackbar(f"Validation Error: {e}", error=True)
            return

        result = await self._file_picker.save_file(
            dialog_title="Save Profile",
            file_name=f"{name}.json",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["json"],
        )
        if result:
            profile.save(Path(result))
            self._show_snackbar(f"Profile saved to {result}")

    async def _load_profile(self, _e: ft.ControlEvent | None = None) -> None:
        files = await self._file_picker.pick_files(
            dialog_title="Load Profile",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["json"],
            allow_multiple=False,
        )
        if not files:
            return

        path = files[0].path
        try:
            profile = Profile.load(Path(path))
        except (ProfileValidationError, Exception) as e:
            self._show_snackbar(f"Failed to load profile: {e}", error=True)
            return

        # Populate metadata
        self.name_field.value = profile.name
        self.author_field.value = profile.author
        self.desc_field.value = profile.description

        # Clear existing effects
        self._effect_widgets.clear()
        self.effects_column.controls.clear()

        # Re-add loaded effects
        for effect in profile.effects:
            self.effect_dropdown.value = effect["type"]
            self._add_effect()
            if self._effect_widgets:
                widget = self._effect_widgets[-1]
                for param_name, value in effect.get("params", {}).items():
                    slider = widget["sliders"].get(param_name)
                    if slider:
                        slider.value = param_to_slider(
                            effect["type"], param_name, float(value)
                        )
        self.page.update()

    # ── Preview ──────────────────────────────────────────────────────

    def _toggle_preview(self, _e: ft.ControlEvent | None = None) -> None:
        if self._preview_active:
            self._preview.stop_preview()
            self._preview_active = False
            self._preview_btn.text = "Start Preview"
            self._preview_btn.icon = ft.Icons.PLAY_ARROW
            self._preview_status.value = ""
        else:
            effects = self._get_gui_effects()
            self._preview.start_preview(effects)
            if self._preview.is_active:
                self._preview_active = True
                self._preview_btn.text = "Stop Preview"
                self._preview_btn.icon = ft.Icons.STOP
                self._preview_status.value = "Preview active"
            else:
                self._preview_status.value = "Preview failed — no audio device"
        self.page.update()

    def _on_slider_change(
        self, effect_type: str, param_name: str, e: ft.ControlEvent
    ) -> None:
        # Update the value label
        for widget in self._effect_widgets:
            if widget["type"] == effect_type and param_name in widget["sliders"]:
                real_value = slider_to_param(effect_type, param_name, int(float(e.data)))
                widget["labels"][param_name].value = f"{param_name}: {real_value:.2f}"
                break

        if self._preview_active:
            effects = self._get_gui_effects()
            self._preview.update_preview(effects)
        self.page.update()

    def _on_close(self) -> None:
        self._preview.stop_preview()

    # ── Helpers ───────────────────────────────────────────────────────

    def _show_snackbar(self, message: str, *, error: bool = False) -> None:
        self.page.open(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.ERROR if error else None,
            )
        )
