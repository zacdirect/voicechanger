"""Tools view — offline file processing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import flet as ft

from voicechanger.gui.state import GuiState

if TYPE_CHECKING:
    from voicechanger.registry import ProfileRegistry

logger = logging.getLogger(__name__)


class ToolsView(ft.Column):
    """Offline processing view — batch file conversion with selected profile."""

    def __init__(
        self,
        state: GuiState,
        *,
        registry: ProfileRegistry | None = None,
        show_snackbar: Any | None = None,
    ) -> None:
        super().__init__(expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)
        self._state = state
        self._registry = registry
        self._show_snackbar = show_snackbar
        self._input_path: str | None = None
        self._output_path: str | None = None

        self._input_picker = ft.FilePicker()
        self._output_picker = ft.FilePicker()

        self._build_ui()

    def _build_ui(self) -> None:
        self._input_label = ft.Text("No input file selected", italic=True)
        self._output_label = ft.Text("No output file selected", italic=True)

        self._btn_pick_input = ft.ElevatedButton(
            "Select Input File", icon=ft.Icons.FOLDER_OPEN,
            on_click=self._on_pick_input,
        )
        self._btn_pick_output = ft.ElevatedButton(
            "Select Output File", icon=ft.Icons.SAVE,
            on_click=self._on_pick_output,
        )

        self._profile_dropdown = ft.Dropdown(label="Profile", width=250)
        if self._registry:
            names = self._registry.list()
            self._profile_dropdown.options = [ft.dropdown.Option(n) for n in sorted(names)]

        self._btn_process = ft.ElevatedButton(
            "Process", icon=ft.Icons.PLAY_ARROW, on_click=self._on_process,
        )
        self._progress = ft.ProgressBar(value=0, visible=False, width=400)
        self._status_text = ft.Text("")

        self.controls = [
            ft.Text("Offline Processing", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([self._btn_pick_input, self._input_label], spacing=8),
            ft.Row([self._btn_pick_output, self._output_label], spacing=8),
            self._profile_dropdown,
            ft.Divider(),
            ft.Row([self._btn_process, self._progress], spacing=8),
            self._status_text,
            self._input_picker,
            self._output_picker,
        ]

    def _on_pick_input(self, _e: ft.ControlEvent) -> None:
        if self.page:
            files = self._input_picker.pick_files(
                dialog_title="Select input audio file",
                allowed_extensions=["wav"],
                allow_multiple=False,
            )
            if files:
                self._input_path = files[0].path
                self._input_label.value = Path(self._input_path).name
                self.page.update()

    def _on_pick_output(self, _e: ft.ControlEvent) -> None:
        if self.page:
            path = self._output_picker.save_file(
                dialog_title="Select output file",
                file_name="output.wav",
                allowed_extensions=["wav"],
            )
            if path:
                self._output_path = path
                self._output_label.value = Path(self._output_path).name
                self.page.update()

    def _on_process(self, _e: ft.ControlEvent) -> None:
        if not self._input_path:
            if self._show_snackbar:
                self._show_snackbar("Select an input file first", error=True)
            return
        if not self._output_path:
            if self._show_snackbar:
                self._show_snackbar("Select an output file first", error=True)
            return

        profile_name = self._profile_dropdown.value
        if not profile_name or not self._registry:
            if self._show_snackbar:
                self._show_snackbar("Select a profile first", error=True)
            return

        profile = self._registry.get(profile_name)
        if profile is None:
            if self._show_snackbar:
                self._show_snackbar(f"Profile '{profile_name}' not found", error=True)
            return

        self._btn_process.disabled = True
        self._progress.visible = True
        self._progress.value = None  # indeterminate
        self._status_text.value = "Processing…"
        if self.page:
            self.page.update()

        def _do_process() -> None:
            from voicechanger.offline import process_file

            try:
                process_file(
                    profile, Path(self._input_path), Path(self._output_path)  # type: ignore[arg-type]
                )
                self._status_text.value = "Done!"
                self._progress.value = 1.0
                if self._show_snackbar:
                    self._show_snackbar(f"Processed: {Path(self._output_path).name}")  # type: ignore[arg-type]
            except FileNotFoundError:
                self._status_text.value = "Error: Input file not found"
                self._progress.value = 0
                if self._show_snackbar:
                    self._show_snackbar("Input file not found", error=True)
            except Exception as exc:
                logger.error("Offline processing failed: %s", exc)
                self._status_text.value = f"Error: {exc}"
                self._progress.value = 0
                if self._show_snackbar:
                    self._show_snackbar(f"Processing error: {exc}", error=True)
            finally:
                self._btn_process.disabled = False
                self._progress.visible = False
                if self.page:
                    self.page.update()

        if self.page:
            self.page.run_thread(_do_process)
