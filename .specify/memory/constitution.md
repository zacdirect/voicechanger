<!--
Sync Impact Report
  Version change: N/A → 1.0.0 (initial ratification)
  Added principles:
    - I. Real-Time Audio First
    - II. Headless by Design
    - III. Cross-Platform Build, Single Deploy Target
    - IV. Test on Host, Deploy to Target
    - V. Minimal Dependencies & Footprint
    - VI. Reliability Over Features
    - VII. Test-First
  Added sections:
    - Platform & Hardware Constraints
    - Development Workflow
    - Governance
  Removed sections: none
  Templates requiring updates:
    - .specify/templates/plan-template.md — ✅ reviewed, no updates needed
    - .specify/templates/spec-template.md — ✅ reviewed, no updates needed
    - .specify/templates/tasks-template.md — ✅ reviewed, no updates needed
  Follow-up TODOs: none
-->
# VoiceChanger Constitution

## Core Principles

### I. Real-Time Audio First

All audio processing MUST operate within a real-time budget
suitable for live voice transformation. Latency from microphone
input to speaker output MUST NOT exceed 50 ms under normal
operating conditions on the target hardware (Raspberry Pi 3 or
newer). Every design decision—algorithm selection, buffer sizing,
thread scheduling—MUST be evaluated against this latency ceiling.
Blocking operations on the audio thread are forbidden.

### II. Headless by Design

The system MUST operate without a display, keyboard, or mouse.
All configuration MUST be file-driven (config files on the
filesystem) or controllable via CLI arguments at startup. Runtime
status MUST be observable through structured logging to stdout/
stderr and optionally a lightweight network endpoint. No feature
may depend on a graphical interface.

### III. Cross-Platform Build, Single Deploy Target

The canonical deployment target is Raspberry Pi OS (64-bit / x64)
on a Raspberry Pi 3 or newer. However, all Python code MUST
build and pass tests on Linux x86_64 (CI) and the developer's
host OS. C/C++ components (patches, native extensions) MUST be
buildable for both the host architecture and aarch64 via GitHub
Actions runners or cross-compilation toolchains. Git submodules
are the approved mechanism for vendoring C/C++ dependencies that
require patching.

### IV. Test on Host, Deploy to Target

Development and automated testing MUST run on commodity hardware
(developer laptops and CI runners). Hardware-dependent behavior
(audio device access, GPIO) MUST be abstracted behind interfaces
so that tests can substitute fakes or mocks. Integration tests
that exercise real audio hardware are permitted as optional
manual gates but MUST NOT block CI.

### V. Minimal Dependencies & Footprint

Every third-party dependency MUST justify its inclusion. Prefer
the Python standard library and well-maintained, Pi-compatible
packages. Native (C/C++) dependencies MUST provide pre-built
wheels for aarch64 or include build instructions that work in
CI. Total installed footprint (excluding OS packages) SHOULD
remain under 500 MB to respect the constrained storage of
SD-card-based Pi deployments.

### VI. Reliability Over Features

The device operates unattended as part of a costume. Crash
recovery MUST be automatic (systemd restart, watchdog, or
equivalent). Graceful degradation is required: if an effect
fails to load, the system MUST fall back to pass-through audio
rather than silence or crash. Feature additions MUST NOT
compromise the stability of the existing audio pipeline.

### VII. Test-First

Tests MUST be written before implementation. The Red-Green-
Refactor cycle is enforced: write a failing test, implement the
minimum code to pass, then refactor. Unit tests use pytest.
Contract and integration tests are required for audio pipeline
stages, configuration parsing, and any network endpoints.

## Platform & Hardware Constraints

- **Target SBC**: Raspberry Pi 3 Model B or newer (Pi 4, Pi 5).
- **Target OS**: Raspberry Pi OS (64-bit, Debian-based).
- **CPU architecture (deploy)**: aarch64 (ARM 64-bit).
- **CPU architecture (dev/CI)**: x86_64 (Linux).
- **Audio interface**: USB audio adapter or HAT DAC with ALSA
  support. Mic input and speaker output MUST be configurable
  via ALSA device names in the project config file.
- **Python version**: 3.11 or newer (matching Raspberry Pi OS
  system Python).
- **C/C++ toolchain**: GCC or Clang with aarch64 cross-compile
  support available in CI.
- **Boot behavior**: The application MUST start automatically on
  boot via a systemd service unit and run until power-off.

## Development Workflow

- **Repository layout**: Mono-repo. Python source in `src/`,
  tests in `tests/`, C/C++ patches in `native/`, submodules in
  `vendor/`, CI workflows in `.github/workflows/`.
- **Submodules**: Any vendored C/C++ library that requires local
  patches MUST be tracked as a git submodule under `vendor/`.
  Patches MUST be documented in `native/README.md`.
- **CI (GitHub Actions)**: Every push and pull request MUST run
  lint (ruff), type check (mypy), and the full pytest suite on
  an x86_64 Linux runner. A separate workflow MUST cross-compile
  native components for aarch64 and verify linkage.
- **Branching**: Feature branches off `main`. PRs require passing
  CI before merge.
- **Release**: Tagged releases produce a deployable artifact
  (sdist, wheel, or tarball) that can be installed on the Pi
  via pip or a single script.

## Governance

This constitution is the highest-authority document for the
VoiceChanger project. All pull requests and code reviews MUST
verify compliance with these principles. Deviations require an
explicit exception documented in the PR description with
rationale and a plan to return to compliance.

**Amendment procedure**: Any change to this constitution MUST be
proposed as a PR modifying this file, reviewed, and merged. The
version number MUST be incremented per semantic versioning:
MAJOR for principle removals or incompatible redefinitions,
MINOR for new principles or material expansions, PATCH for
wording and clarification fixes.

**Compliance review**: At least once per release cycle, the
maintainer MUST audit open specs and plans against the current
constitution and file issues for any drift.

**Version**: 1.0.0 | **Ratified**: 2026-04-12 | **Last Amended**: 2026-04-12
