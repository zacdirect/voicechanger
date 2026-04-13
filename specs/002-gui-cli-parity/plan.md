# Implementation Plan: GUI–CLI Feature Parity

**Branch**: `002-gui-cli-parity` | **Date**: 2026-04-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-gui-cli-parity/spec.md`

## Summary

Extend the Flet-based GUI from a profile-editor-only tool to a full-parity interface matching every CLI capability: service start/stop (with IPC remote control when a service is already running), audio device selection, complete profile CRUD via the registry, real-time audio level meters, status dashboard, offline file processing, and monitor/mute toggle. The GUI adopts Flet-idiomatic navigation (tabbed/multi-view layout) while keeping all business logic in the existing custom Python modules.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Flet ≥0.84 (GUI), pedalboard (audio, patched/vendored), numpy
**Storage**: JSON profile files on filesystem (`profiles/builtin/`, `profiles/user/`)
**Testing**: pytest (unit, contract, integration)
**Target Platform**: Linux x86_64 (dev workstation — primary for GUI), Raspberry Pi OS aarch64 (primary for CLI)
**Project Type**: Desktop application + CLI + systemd service
**Performance Goals**: Level meters ≥15 fps update rate; profile switch <100ms audible gap; offline processing of 60s file in <30s on Pi 3
**Constraints**: Single audio pipeline per host (IPC when service already running); <500 MB installed footprint
**Scale/Scope**: ~20 functional requirements; 4 GUI views; ~50 profiles max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Real-Time Audio First | **PASS** | GUI controls the existing AudioPipeline; no new audio processing code. Level meters read from pipeline, do not affect audio thread. |
| II. Headless by Design | **PASS** | CLI retains full standalone operation. GUI is additive — no feature requires GUI. All config remains file-driven. |
| III. Cross-Platform Build, Single Deploy Target | **PASS** | Flet is pure Python, runs on both x86_64 and aarch64. No new native dependencies. |
| IV. Test on Host, Deploy to Target | **PASS** | GUI logic modules are testable without display. Audio hardware abstracted behind existing interfaces. |
| V. Minimal Dependencies & Footprint | **PASS** | Flet already in `pyproject.toml`. No new dependencies added. |
| VI. Reliability Over Features | **PASS** | GUI connects via IPC to existing service — cannot crash the audio pipeline. Embedded pipeline mode uses same AudioPipeline. |
| VII. Test-First | **PASS** | Plan includes test structure for all new GUI logic modules. |

All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-gui-cli-parity/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── gui-views.md     # GUI view contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/voicechanger/
├── __init__.py
├── __main__.py
├── audio.py              # AudioPipeline — add level metering callback
├── cli.py                # CLI entry point (unchanged)
├── config.py             # Config loader (unchanged)
├── device.py             # DeviceMonitor (unchanged)
├── effects.py            # Effect registry (unchanged)
├── offline.py            # Offline processing (unchanged)
├── profile.py            # Profile model (unchanged)
├── registry.py           # ProfileRegistry — add update() method
├── service.py            # Service daemon (unchanged IPC protocol)
└── gui/
    ├── __init__.py        # launch_gui() entry point (updated)
    ├── app.py             # Main app shell — Flet NavigationRail + view routing
    ├── logic.py           # Existing slider/preview logic (retained, extended)
    ├── ipc_client.py      # NEW: async IPC client for remote-control mode
    ├── views/
    │   ├── __init__.py
    │   ├── control.py     # NEW: Service control view (start/stop, device select, meters, status)
    │   ├── profiles.py    # NEW: Profile browser/manager view (list, switch, delete, export, import)
    │   ├── editor.py      # REFACTORED from current app.py: effect chain editor + preview
    │   └── tools.py       # NEW: Offline processing view
    └── state.py           # NEW: shared GUI state (selected profile, pipeline mode, device choices)

tests/
├── unit/
│   ├── test_gui.py         # Existing (updated with new view logic tests)
│   ├── test_gui_state.py   # NEW: GUI state management tests
│   └── test_ipc_client.py  # NEW: IPC client unit tests
├── contract/
│   └── test_gui_views.py   # NEW: View contract tests
└── integration/
    └── test_gui_ipc.py     # NEW: GUI↔Service IPC integration tests
```

**Structure Decision**: Extends the existing single-project layout. The `gui/` package gains a `views/` subpackage for the tabbed navigation model, a shared `state.py` for cross-view state, and an `ipc_client.py` for service remote-control. Business logic modules (`audio.py`, `registry.py`, etc.) receive minimal additions; the GUI views compose them.

## Phase 0: Research — Complete

Output: [research.md](research.md)

6 research items resolved:
- **R1**: NavigationRail selected over Tabs for multi-view layout (Material Design 3 sidebar)
- **R2**: Async IPC client with auto-detect (probe socket on startup)
- **R3**: RMS level metering via AudioPipeline callback + ProgressBar at 15fps
- **R4**: Builtin auto-fork naming: `{name}-custom-{N}` with collision scan
- **R5**: Central `GuiState` dataclass for cross-view state
- **R6**: `ProfileRegistry.update()` for atomic in-place saves

## Phase 1: Design & Contracts — Complete

Outputs:
- [data-model.md](data-model.md) — `GuiState`, `PipelineMode`, `EditingProfile`, `IpcClient` entities
- [contracts/gui-views.md](contracts/gui-views.md) — Navigation shell + 4 view contracts
- [quickstart.md](quickstart.md) — Developer quickstart with file map and architecture decisions

## Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Real-Time Audio First | **PASS** | Level metering reads from audio callback but does not block it. RMS computed in-callback is lightweight (numpy). |
| II. Headless by Design | **PASS** | All GUI additions are in `gui/` package. No CLI or service code depends on GUI. `IpcClient` is a consumer of the existing protocol, not a new server. |
| III. Cross-Platform Build, Single Deploy Target | **PASS** | `gui/views/` and `gui/state.py` are pure Python. `IpcClient` uses stdlib `asyncio` + `socket`. No platform-specific additions. |
| IV. Test on Host, Deploy to Target | **PASS** | `GuiState`, `IpcClient`, `generate_draft_name()` are all testable without display or audio hardware. View tests verify construction against mocks. |
| V. Minimal Dependencies & Footprint | **PASS** | Zero new dependencies. Flet was already present. |
| VI. Reliability Over Features | **PASS** | Remote mode uses existing IPC with error handling. Embedded mode uses existing AudioPipeline. Auto-fork naming is deterministic. |
| VII. Test-First | **PASS** | Test plan covers unit tests for all new modules, contract tests for views, integration tests for IPC round-trip. |

All gates pass post-design. No violations.
