"""GUI entry point."""

from __future__ import annotations


def launch_gui() -> None:
    """Launch the profile authoring GUI."""
    import flet as ft

    from voicechanger.gui.app import VoiceChangerApp

    ft.run(lambda page: VoiceChangerApp(page))
