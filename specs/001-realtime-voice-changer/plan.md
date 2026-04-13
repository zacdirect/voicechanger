# Implementation Plan: Realtime Voice Changer

**Branch**: `001-realtime-voice-changer` | **Date**: 2026-04-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-realtime-voice-changer/spec.md`

## Summary

Build a headless, real-time voice changer for Raspberry Pi 3+ using Spotify's Pedalboard library. The system captures mic audio, applies a configurable chain of effects (pitch shift, gain, reverb, etc.) from character profiles, and plays transformed audio to a speaker — all within a 50 ms latency budget. A systemd-managed service runs headless on the Pi; a CLI communicates over a Unix domain socket for profile management; and a desktop GUI on the dev machine enables interactive profile authoring. Pedalboard's `AudioStream` provides real-time I/O, but its built-in `PitchShift` plugin introduces ~1–2s latency due to the `PrimeWithSilence` delay line (confirmed by upstream issue [#350](https://github.com/spotify/pedalboard/issues/350), still open). A `LivePitchShift` C++ patch that bypasses this delay is required

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pedalboard (patched, vendored as submodule), numpy  
**Storage**: JSON profile files on filesystem, TOML/INI for system configuration  
**Testing**: pytest (unit, contract, integration); ruff (lint); mypy (types)  
**Target Platform**: Raspberry Pi OS 64-bit (aarch64) deploy; Linux x86_64 dev/CI  
**Project Type**: CLI service + desktop GUI authoring tool  
**Performance Goals**: ≤50 ms end-to-end audio latency; profile switch ≤2 s  
**Constraints**: <500 MB installed footprint; 8-hour unattended operation without dropouts; <50 MB memory growth  
**Scale/Scope**: Single-user headless device; ~3 built-in profiles + community profiles; ~10 supported effect types

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Real-Time Audio First | PASS | AudioStream with 256-frame buffer @ 48 kHz (~5 ms); LivePitchShift patch for <100 ms pitch shift latency; ≤50 ms budget in SC-001 |
| II | Headless by Design | PASS | systemd service, file-driven config, CLI-over-Unix-socket, structured logging; no GUI on Pi (FR-002, FR-012) |
| III | Cross-Platform Build | PASS | Python code runs on x86_64 CI; C++ patch cross-compiled for aarch64 via GitHub Actions; submodule in `vendor/` (FR-015) |
| IV | Test on Host, Deploy to Target | PASS | Audio device abstracted behind interfaces for mocks; hardware tests are optional manual gates only |
| V | Minimal Dependencies | PASS | pedalboard (vendored), numpy, standard library; footprint target <500 MB |
| VI | Reliability Over Features | PASS | Pass-through fallback (FR-003), systemd auto-restart (SC-007), graceful profile degradation |
| VII | Test-First | PASS | pytest TDD workflow; contract tests for IPC, unit tests for profiles/pipeline, integration tests for audio chain |

## Project Structure

### Documentation (this feature)

```text
specs/001-realtime-voice-changer/
├── plan.md              # This file
├── research.md          # Phase 0: Technical research findings
├── data-model.md        # Phase 1: Entity definitions & schemas
├── quickstart.md        # Phase 1: Developer quickstart guide
├── contracts/           # Phase 1: API & IPC contracts
│   ├── cli.md           # CLI command interface
│   └── ipc.md           # Unix domain socket protocol
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── voicechanger/
│   ├── __init__.py
│   ├── __main__.py       # Entry point
│   ├── audio.py          # AudioPipeline: AudioStream lifecycle, effect chain
│   ├── effects.py        # Effect type registry, parameter validation
│   ├── profile.py        # Profile model, serialization/deserialization
│   ├── registry.py       # ProfileRegistry: discovery, built-in vs user
│   ├── service.py        # Service daemon: Unix socket server, signal handling
│   ├── cli.py            # CLI commands (click or argparse)
│   ├── config.py         # System config loading (audio devices, paths)
│   ├── device.py         # Audio device enumeration, polling, hot-switch
│   └── gui/
│       ├── __init__.py
│       └── app.py        # Desktop authoring GUI (tkinter)
└── py.typed

native/
├── README.md             # Patch rationale & build instructions
└── patches/
    └── 0001-add-LivePitchShift.patch

vendor/
└── pedalboard/           # Git submodule (Spotify pedalboard, patched)

tests/
├── conftest.py
├── unit/
│   ├── test_profile.py
│   ├── test_registry.py
│   ├── test_effects.py
│   └── test_config.py
├── contract/
│   ├── test_cli.py
│   └── test_ipc.py
└── integration/
    ├── test_audio_pipeline.py
    └── test_service.py

profiles/
├── builtin/
│   ├── clean.json
│   ├── high-pitched.json
│   └── low-pitched.json
└── user/                 # User-created profiles go here

.github/
└── workflows/
    ├── ci.yml            # Lint, type-check, pytest on x86_64
    └── build-native.yml  # Cross-compile patched pedalboard for aarch64
```

**Structure Decision**: Single-project layout per constitution Development Workflow section (`src/`, `tests/`, `native/`, `vendor/`). The `src/voicechanger/` package contains all Python source. Desktop GUI is a subpackage (`gui/`) rather than a separate project since it shares the same profile model and audio pipeline code. Profiles are stored outside `src/` as runtime data.

## Complexity Tracking

No constitution violations. All design choices align with the 7 principles.
