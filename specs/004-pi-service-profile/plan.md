# Implementation Plan: Pi CLI Service Profile

**Branch**: `004-pi-service-profile` | **Date**: 2026-04-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-pi-service-profile/spec.md`

## Summary

Refactor the voicechanger daemon into a system service that persists its own operational state to `/var/lib/voicechanger/`, resumes from that state at boot, and accepts profile/device changes exclusively via IPC. The CLI/GUI runs in user context, reads `~/.voicechanger/`, bootstraps it on first use, and pushes desired state to the daemon. A non-interactive `apply` command enables login-time profile loading. The daemon never reads user home directories.

## Technical Context

**Language/Version**: Python 3.11+ (matching Raspberry Pi OS system Python)
**Primary Dependencies**: pedalboard (audio effects), sounddevice (audio I/O), tomllib/tomli (TOML parsing)
**Storage**: JSON state file (`/var/lib/voicechanger/state.json`), TOML user config, JSON profile files
**Testing**: pytest (unit, contract, integration layers)
**Target Platform**: Raspberry Pi OS 64-bit (aarch64), dev/CI on Linux x86_64
**Project Type**: CLI + system daemon
**Performance Goals**: <50ms audio latency (per constitution Principle I)
**Constraints**: <500MB installed footprint, SD-card storage, headless operation
**Scale/Scope**: Single-user embedded device, single daemon instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Real-Time Audio First | Pass | No changes to audio pipeline; profile switching is control-plane only |
| II. Headless by Design | Pass | Daemon is headless system service; CLI is the control interface; `apply` supports non-interactive login |
| III. Cross-Platform Build, Single Deploy Target | Pass | All changes are Python; no new native dependencies |
| IV. Test on Host, Deploy to Target | Pass | State persistence and IPC are testable with tmpdir fixtures; no hardware dependency |
| V. Minimal Dependencies & Footprint | Pass | No new dependencies; state file is small JSON |
| VI. Reliability Over Features | Pass | Daemon resumes from persisted state; fresh install defaults to `clean`; last-push-wins avoids conflict complexity |
| VII. Test-First | Pass | Contract/integration/unit tests required before implementation per spec |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-pi-service-profile/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── ipc-state-protocol.md
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/voicechanger/
├── cli.py               # CLI command router — add `apply`, update `switch` to push via IPC
├── config.py            # User config loading — add bootstrap, remove daemon config resolution
├── service.py           # Daemon — add state persistence, state-based startup, IPC state commands
├── registry.py          # Profile registry — daemon uses for built-ins only; CLI uses for user profiles
├── hardware.py          # Hardware hints — daemon built-ins; user overrides pushed via IPC
├── profile.py           # Profile schema (existing, extended for origin metadata)
├── state.py             # NEW: Daemon operational state model and persistence
├── audio.py             # Audio pipeline (unchanged)
├── effects.py           # Effect registry (unchanged)
├── device.py            # Device management (unchanged)
├── gui/                 # GUI views — update to push via IPC, add reconciliation display
│   ├── logic.py
│   ├── state.py
│   └── views/
└── ...

deploy/
└── voicechanger.service # Systemd unit — change to system service (not user service)

scripts/release/
└── post-install.sh      # Deb post-install — create /var/lib/voicechanger/, skel setup

tests/
├── contract/
│   ├── test_ipc.py      # IPC protocol contract tests — add state push/resume commands
│   └── test_cli.py      # CLI contract tests — add apply, update switch
├── integration/
│   ├── test_service.py  # Service integration — add state persistence round-trip
│   └── test_reconciliation.py  # NEW: CLI/daemon state reconciliation tests
└── unit/
    ├── test_state.py    # NEW: State model serialization, schema compat
    ├── test_config.py   # Config tests — add bootstrap behavior
    └── test_service.py  # Service unit tests — add state-based startup
```

**Structure Decision**: Existing mono-repo layout. New `state.py` module for daemon operational state model. All other changes are modifications to existing files. Test structure follows established contract/integration/unit layers.
