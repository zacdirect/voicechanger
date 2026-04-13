# Quickstart: GUI–CLI Feature Parity

**Date**: 2026-04-13
**Feature**: 002-gui-cli-parity
**Branch**: `002-gui-cli-parity`

## What This Feature Does

Transforms the existing single-screen profile editor GUI into a full-featured desktop application with NavigationRail-based navigation between four views: Control (service/device/levels), Profiles (browse/manage), Editor (effect authoring with builtin auto-fork), and Tools (offline processing). Adds IPC remote-control mode so the GUI can connect to an already-running service.

## Key Files

### New Files
- `src/voicechanger/gui/state.py` — `GuiState`, `PipelineMode`, `EditingProfile`, `generate_draft_name()`
- `src/voicechanger/gui/ipc_client.py` — `IpcClient` async wrapper for Unix socket protocol
- `src/voicechanger/gui/views/control.py` — Control view: service start/stop, device selection, level meters, status
- `src/voicechanger/gui/views/profiles.py` — Profiles view: browser, activate, delete, export, import
- `src/voicechanger/gui/views/editor.py` — Editor view: refactored from current `app.py` functionality
- `src/voicechanger/gui/views/tools.py` — Tools view: offline file processing

### Modified Files
- `src/voicechanger/gui/app.py` — Rewritten as NavigationRail shell; existing editor code moves to `views/editor.py`
- `src/voicechanger/gui/__init__.py` — May update `launch_gui()` signature
- `src/voicechanger/audio.py` — Add optional `level_callback` to AudioPipeline
- `src/voicechanger/registry.py` — Add `update(profile)` method

### Reference (read-only context)
- `src/voicechanger/gui/logic.py` — `GuiEffectState`, `PreviewManager`, slider mapping (unchanged)
- `src/voicechanger/service.py` — IPC protocol server (reference for client implementation)
- `src/voicechanger/device.py` — `DeviceMonitor` (used by Control view)
- `src/voicechanger/config.py` — Config loading (used for socket path, device defaults)
- `src/voicechanger/effects.py` — `EFFECT_REGISTRY` (used by Editor view)

## Architecture Decisions

1. **NavigationRail** — Flet's Material Design 3 sidebar navigation for switching between 4 views.
2. **Shared state** — `GuiState` dataclass in `gui/state.py`, not Flet session storage.
3. **Embedded vs Remote** — `PipelineMode.EMBEDDED` (direct AudioPipeline) or `PipelineMode.REMOTE` (IPC to service).
4. **Level metering** — Audio callback pushes RMS to GuiState; Flet async loop reads at ~15fps, renders as ProgressBar.
5. **Builtin auto-fork** — First modification of a builtin profile generates `{name}-custom-{N}` name.

## Testing Strategy

- **Unit tests**: `GuiState`, `IpcClient`, `generate_draft_name()`, view construction.
- **Integration tests**: GUI ↔ service IPC round-trip, profile fork-and-save flow.
- **Contract tests**: Verify GUI views satisfy the contracts in `contracts/gui-views.md`.

## Constitution Constraints

- All audio effects must remain in pedalboard (Principle 1: Real-Time Audio First).
- GUI is a convenience layer; the service must remain fully headless-operable (Principle 2: Headless by Design).
- No new runtime dependencies beyond Flet, which is already in pyproject.toml (Principle 5: Minimal Dependencies).
- Tests run on host without audio hardware via mocked DeviceMonitor and AudioPipeline (Principle 4: Test on Host).

## Running

```bash
# Run tests
cd src && pytest && ruff check .

# Launch GUI
python -m voicechanger gui

# Launch service (for remote-control mode testing)
python -m voicechanger serve &
python -m voicechanger gui
```
