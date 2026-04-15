# Implementation Plan: Pi CLI Boot + User Profile Service UX

**Branch**: `004-pi-cli-service-profile` | **Date**: 2026-04-15 | **Spec**: `/home/zac/repos/voicechanger/specs/004-pi-cli-service-profile/spec.md`
**Input**: Feature specification from `/home/zac/repos/voicechanger/specs/004-pi-cli-service-profile/spec.md`

**Note**: This document focuses planning on the production-mode UX slice: boot-to-CLI operation, per-user profile persistence, and service config/profile directory resolution.

## Summary

Define and document a production-friendly Raspberry Pi workflow where users design a character profile on a dev machine or local Pi GUI, save it into a user-owned profile directory, and have the headless service reliably load that profile at boot from a TOML configuration. The approach is documentation-first plus targeted service/config behavior alignment: standardize config path ownership, clarify profile directory precedence, and close CLI/service persistence gaps so a reboot reliably applies the selected character.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pedalboard (vendored patched build), numpy, tomllib, argparse, systemd service manager  
**Storage**: File-based TOML + JSON (`~/.config/voicechanger/voicechanger.toml`, `~/.voicechanger/profiles/*.json`)  
**Testing**: pytest (unit, contract, integration), ruff  
**Target Platform**: Raspberry Pi OS (aarch64 + armv7l), Linux x86_64 dev/CI  
**Project Type**: CLI/service + desktop companion GUI application  
**Performance Goals**: Live processing latency under 50 ms; boot-to-service reliability after reboot  
**Constraints**: Headless-first operation, no GUI requirement in production mode, user-owned config/profile directories must remain readable to service  
**Scale/Scope**: Single-node deployment per Pi; profile library in tens to low hundreds of JSON files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: Real-Time Audio First. No DSP algorithm changes; only config/profile discovery flow and UX documentation.
- PASS: Headless by Design. Planned UX explicitly ends in CLI/service + reboot verification path.
- PASS: Cross-Platform Build, Single Deploy Target. Docs include dev machine authoring and Pi deployment handoff.
- PASS: Test on Host, Deploy to Target. Plan includes host-executable contract tests for config/profile loading semantics.
- PASS: Minimal Dependencies & Footprint. No new runtime dependencies introduced.
- PASS: Reliability Over Features. Focus is deterministic startup and profile resolution reliability.
- PASS: Test-First. Gaps are framed as failing/needed contract tests before code changes.

## Project Structure

### Documentation (this feature)

```text
specs/004-pi-cli-service-profile/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── service-config-and-profile-loading.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── voicechanger/
    ├── cli.py
    ├── config.py
    ├── service.py
    ├── registry.py
    └── gui/

deploy/
├── voicechanger.service
└── production-mode-toggle.sh

profiles/
├── builtin/
└── user/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Single Python project with service/CLI core under `src/voicechanger`, deployment scripts under `deploy`, and behavior verification in `tests/{unit,contract,integration}`. This feature slice is documentation + contract definition, with expected implementation changes confined to config/service/cli modules.

## Complexity Tracking

No constitution violations identified; this section is intentionally empty.

## Phase 0 Output (Research Scope)

- Resolve boot-time config ownership model (system service vs user service) for per-user profile loading.
- Resolve path-resolution expectations for relative vs absolute profile directories in config.
- Resolve CLI persistence mismatch (`--config` aware writes and audio device key naming) that can prevent rebooted service from seeing intended settings.

## Phase 1 Output (Design Scope)

- Define data entities for user-owned profile lifecycle and startup configuration resolution.
- Define service/config contract for profile lookup precedence and startup behavior.
- Provide an operator quickstart for: author profile -> save to user dir -> update config -> reboot -> verify active character.

## Post-Design Constitution Check

- PASS: All principles remain satisfied after design artifacts.
- No constitutional violations or exception justifications required.
