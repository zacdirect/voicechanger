"""GUI entry point."""

from __future__ import annotations


def launch_gui() -> None:
    """Launch the profile authoring GUI."""
    from voicechanger.gui.app import VoiceChangerApp

    app = VoiceChangerApp()
    app.run()
