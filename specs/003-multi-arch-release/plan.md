# Implementation Plan: Multi-Architecture Release Automation

**Branch**: `003-multi-arch-release` | **Date**: 2026-04-13 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/003-multi-arch-release/spec.md`

## Summary

Establish a formal release mechanism for voicechanger using GitHub Actions to handle cross-architecture builds (x86_64, aarch64, armv7l), apply pedalboard patches, generate system packages (deb), auto-increment versions, and publish artifacts to GitHub releases. This is a **packaging and distribution feature** with **minimal code changes**—reusing existing GUI and CLI, adding systemd integration, production mode toggle script, and deployment documentation.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase)  
**Primary Dependencies**: GitHub Actions, setuptools, pedalboard (patched, vendored via submodule), Flea (vendored FFI for audio), sounddevice 0.5.5+  
**Storage**: Version metadata in `pyproject.toml`, `src/voicechanger/__init__.py`; config in `~/.config/voicechanger/config.toml` (existing)  
**Testing**: pytest (unit + integration), GitHub Actions job output verification, manual Pi testing  
**Target Platform**: Linux x86_64, aarch64 (Raspberry Pi OS 64-bit), armv7l (Raspberry Pi OS 32-bit); Ubuntu 22.04+, Debian 11+  
**Project Type**: CLI/GUI desktop app with daemon support  
**Performance Goals**: Release build completes within 30 minutes; production mode toggle under 10 seconds; device enumeration under 1 second  
**Constraints**: Headless mode must not load GUI/X11; daemon must auto-start in systemd; device selection must persist across restarts  
**Scale/Scope**: 3 target architectures, 2 CLI commands (`list-devices`, `set-device`), 1 production mode toggle script, ~5 documentation pages (Deployment Guide, Bluetooth setup, Production Mode, Emergency Fallback, Release Notes template)

## Constitution Check

**Status**: ✅ No violations  

This feature:
- ✅ Stays within Python 3.11+ (no new language/framework intro)
- ✅ Leverages existing pedalboard, Flet GUI, CLI framework (no architectural divergence)
- ✅ Adds no new major UI components (resuses existing GUI/CLI)
- ✅ Focused on packaging infrastructure, not core audio processing changes
- ✅ Uses standard tooling: GitHub Actions, setuptools, systemd (industry standard for Linux daemons)

## Project Structure

### Documentation (this feature)

```text
specs/003-multi-arch-release/
├── spec.md                  # Feature specification (completed)
├── plan.md                  # This file
├── data-model.md            # (optional) Configuration entities
├── quickstart.md            # (optional) Setup scenarios for testers
├── research.md              # (optional) Decision rationale
├── contracts/               # (optional) Interface contracts (CLI stubs)
└── checklists/
    └── requirements.md      # Validation checklist (deployed)
```

### Source Code (repository root)

```text
src/voicechanger/
├── __init__.py              # Version metadata [MODIFIED]
├── __main__.py              # CLI entry point (existing CLI)
├── cli.py                   # CLI commands [EXTENDED: add list-devices, set-device]
├── service.py               # Daemon wrapper (existing, may add systemd integration)
├── gui/
│   └── app.py               # Flet GUI (reused; no changes needed)
├── config.py                # Config file handling (existing, verify device persist)
└── device.py                # Device detection [REUSED] (use for CLI commands)

tests/
├── unit/
│   ├── test_cli.py          # [NEW] CLI command tests (list-devices, set-device)
│   └── [existing unit tests] # (unchanged)
├── integration/
│   ├── test_device_persist.py # [NEW] Device selection persistence across restart
│   └── [existing integration tests]
└── contract/
    └── test_cli_commands.py # [NEW] Contract tests for CLI interface

scripts/
├── release/
│   ├── build-matrix.yml     # [NEW] GitHub Actions build matrix config
│   ├── version-bump.py      # [NEW] Semantic version updater (helper to avoid inline shell in workflows)
│   └── build-deb.sh         # [NEW] Debian package builder
└── [existing build scripts]

deploy/
├── voicechanger.service     # [UPDATED] systemd service file (existing)
├── production-mode-toggle.sh # [NEW] Enable/disable headless mode
└── boot-services/           # [NEW] systemd target configurations

.github/workflows/
├── multi-arch-release.yml   # [NEW] Main release workflow (build matrix, version bump, publish)
├── build-linux.yml          # [NEW] Per-architecture build steps
└── publish-release.yml      # [NEW] GitHub release publication

docs/
├── DEPLOYMENT.md            # [NEW] Multi-page deployment guide
├── SETUP_PI.md              # [NEW] Fresh Raspberry Pi OS setup (CLI + GUI)
├── BLUETOOTH_SETUP.md       # [NEW] Bluetooth device pairing guide
├── PRODUCTION_MODE.md       # [NEW] Headless mode workflow
├── EMERGENCY_FALLBACK.md    # [NEW] Troubleshooting & recovery
└── BUILDING_FROM_SOURCE.md  # [NEW] Local build instructions

.gitignore
├── profiles/user/           # [UPDATED] Already added (user profiles excluded)
└── [existing patterns]

native/patches/
├── pedalboard.patch         # [EXISTING] Applied during build; verified in CI
└── [existing patches]
```

**Structure Decision**: Single repository with GitHub Actions workflows defining the CI/CD pipeline. Code changes are minimal and localized to:
- CLI extension (`cli.py`: add `list-devices`, `set-device`)
- Device persistence (ensure `config.py` stores selection)
- Production mode toggle script (simple systemd target switcher)
- Version automation (Python helper to avoid shell complexity in workflows)
- Systemd service updates (enable daemon auto-start in production mode)

All build complexity lives in GitHub Actions workflows, not in source code.

## Complexity Tracking

| Item | Scope | Rationale |
|------|-------|-----------|
| Cross-arch builds (3 targets) | Required; GitHub Actions job matrix | Essential for Pi deployment; existing pedalboard patch already supports all archs; minimal CI cost |
| System package generation (.deb) | Required; FPM or setuptools bdist_deb | Linux standard; enables `apt install`; reduces user friction vs. wheels alone |
| Version auto-bump | Recommended; thin Python helper | Avoids error-prone inline shell scripts in workflows; semantic versioning enforces consistency |
| CLI device commands | Required for headless workflow | Necessary for Pi headless operation; complements existing device.py detection logic |
| Systemd integration | Required; use existing service file | Enable daemon auto-start in production mode; standard for Linux services |
| Production mode toggle | Required; ~50-line shell script | Switches between runlevel 3 (headless) and runlevel 5 (graphical); critical for live performers |
| Deployment documentation | Required; 5 guides (~30 pages total) | Reduce support burden; enable self-service for heterogeneous user technical backgrounds |

---

## Implementation Phases (Dependency Order)

### Phase 1: Setup & Infrastructure
- [ ] Initialize GitHub Actions workflows directory and version automation
- [ ] Create build matrix configuration for x86_64, aarch64, armv7l
- [ ] Set up systemd service file and production mode toggle script

### Phase 2: Core Release Pipeline (P1 User Story)
- [ ] Implement multi-architecture build workflow
- [ ] Add pedalboard patch verification step
- [ ] Create release publication automation
- [ ] Test on all three architectures (local simulation or CI)

### Phase 3: Packaging & System Integration (P2 User Stories)
- [ ] Implement .deb package generation
- [ ] Add CLI device commands (`list-devices`, `set-device`)
- [ ] Verify device selection persistence across restarts
- [ ] Integration tests for CLI commands

### Phase 4: Production Mode & Documentation (P3 User Stories)
- [ ] Implement production mode toggle script and systemd targets
- [ ] Create comprehensive deployment guide
- [ ] Create scenario-specific guides (Bluetooth, Emergency Fallback, etc.)
- [ ] Manual Pi testing and documentation validation

### Phase 5: Auto-Versioning (P4 User Story)
- [ ] Implement semantic version bumper
- [ ] Integrate with release workflow
- [ ] Create version increment rules (commit message hints, branch prefix detection, etc.)
- [ ] End-to-end release test (merge → version bump → build → release)

### Phase 6: Polish & Cross-Cutting
- [ ] Verify all architecture wheels have correct entry points
- [ ] Audit release artifact checksums and integrity
- [ ] Documentation review and user feedback integration
- [ ] Post-release runbooks and troubleshooting

---

## Dependencies & Prerequisites

**Before Implementation**:
1. ✅ Feature spec validated (complete; see [spec.md](spec.md))
2. ✅ Existing codebase stable (205 tests passing; GUI/CLI functional)
3. ✅ Pedalboard patch confirmed applicable to all three architectures
4. ✅ GitHub Actions access verified (user has repo admin permissions)

**External Tools Required**:
- GitHub Actions (free tier sufficient for this scope)
- FPM or setuptools `bdist_deb` (for package generation)
- Linux build environments for aarch64 and armv7l (can use emulation or physical boards)
- Manual Pi hardware testing (at least one aarch64 RPi 4/5 for validation)

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Pedalboard patch fails on armv7l | Release incomplete; user blocked | Pre-test patch on armv7l before merging; CI gate failure blocks release |
| Version conflict (duplicate tag) | Release fails; manual recovery required | CI detects existing tag, logs error, requires manual intervention and retry |
| Systemd service fails on headless boot | Production mode unusable | Test production mode toggle locally; add systemd failure notifications to runbook |
| Device persistence fails across restart | config persists but not restored on boot | Integration test validates read-back; verify config path is writable in headless mode |
| Documentation drift after release | Users confused by outdated instructions | Add version anchors in docs; link from release notes to snapshot docs (not main branch) |

---

## Success Metrics

Upon completion, verify:
1. ✅ **SC-001**: GitHub release created within 30 min of merge to `main`
2. ✅ **SC-002**: All three arch wheels present with correct checksums
3. ✅ **SC-003**: `apt install voicechanger` succeeds on Ubuntu 22.04+ and Pi OS
4. ✅ **SC-004**: `voicechanger list-devices` works on fresh Pi OS within 2 min setup
5. ✅ **SC-005**: Production mode toggle completes in <10 sec; headless boot <30 sec
6. ✅ **SC-006**: User can follow Deployment.md and have working Pi in <30 min
7. ✅ **SC-007**: All release artifacts downloadable and installation succeeds without post-install config errors

---

## Notes for Implementation

- **CLI commands** reuse existing `src/voicechanger/device.py` (discovery logic already present)
- **Systemd integration** uses existing `deploy/voicechanger.service`; no major restructuring needed
- **Production mode** is a simple systemd target switch; no kernel/bootloader changes
- **Pedalboard patch** already vendored; CI just applies it during build
- **Deployment docs** should be narrative, not procedural TODOs; include screenshots of GUI and example CLI output
