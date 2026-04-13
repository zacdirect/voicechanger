# Tasks: Multi-Architecture Release Automation

**Input**: Design documents from `/specs/003-multi-arch-release/`  
**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required for user stories)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. MVP scope includes US1 (Cross-Architecture Builds) and US3 (CLI Device Commands).

## Format: `- [ ] [ID] [P?] [Story] Description with file path`

- **[P]**: Task is parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, etc.)
- All tasks include exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: GitHub Actions workflows, build infrastructure, and version automation foundation

**Checkpoint**: All builds can run on three architectures; version management is automated

- [X] T001 Create GitHub Actions workflows directory structure in `.github/workflows/`
- [X] T002 [P] Create systemd service file with ExecStart entry point in `deploy/voicechanger.service`
- [X] T003 [P] Create production mode toggle script in `deploy/production-mode-toggle.sh` (systemd target switcher)
- [X] T004 [P] Initialize version automation helper script in `scripts/release/version-bump.py` (semantic versioning updater)
- [X] T005 Create build matrix configuration stub in `.github/workflows/build-matrix.yml`
- [X] T006 [P] Initialize .gitignore entry for `profiles/user/` (user profiles excluded from version control)

---

## Phase 2: Foundational (Blocking Prerequisites for All User Stories)

**Purpose**: Core CI/CD infrastructure and device detection mechanisms

**⚠️ CRITICAL**: No user story work can begin until this phase is complete (especially US1 and US3)

- [X] T007 Implement multi-architecture build matrix workflow in `.github/workflows/multi-arch-release.yml` (define x86_64, aarch64, armv7l targets)
- [X] T008 Create pedalboard patch verification step in build workflow (verify LivePitchShift present after patch apply)
- [X] T009 Implement install entry points in `pyproject.toml` (ensure `voicechanger` and `voicechanger-gui` CLI commands are defined)
- [X] T010 [P] Update systemd service file in `deploy/voicechanger.service` to use correct entry points
- [X] T011 Create Debian package builder script in `scripts/release/build-deb.sh` (FPM or setuptools-based)
- [X] T012 Add version string extraction to `src/voicechanger/__init__.py` (make version readable by build scripts)

**Checkpoint**: Build infrastructure ready; all three architectures can be targeted; pedalboard patch validation works

---

## Phase 3: User Story 1 - Cross-Architecture Binary Distribution (Priority: P1) 🎯 MVP

**Goal**: GitHub Actions automatically builds and publishes wheels for x86_64, aarch64, armv7l on merge to `main`

**Independent Test**: Merge commit to `main` with version bump; verify GitHub release created with three wheels and pedalboard patch artifact within 30 minutes; download and verify entry points match across architectures

### Tests for User Story 1

- [X] T013 [US1] Create contract test for build artifacts in `tests/contract/test_build_artifacts.py` (verify wheels have correct entry points, pedalboard patch applied)
- [X] T014 [US1] Create integration test for multi-arch build in `tests/integration/test_release_pipeline.py` (simulate build completion, verify artifact integrity)

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement build steps for x86_64 in `.github/workflows/build-linux.yml` (clone, install deps, build wheel, verify entry points)
- [X] T016 [P] [US1] Implement build steps for aarch64 in `.github/workflows/build-linux.yml` (native or emulated; apply pedalboard patch)
- [X] T017 [P] [US1] Implement build steps for armv7l in `.github/workflows/build-linux.yml` (native or emulated; apply pedalboard patch)
- [X] T018 [US1] Implement GitHub release publication workflow in `.github/workflows/publish-release.yml` (create release, upload wheels, add pedalboard patch artifact)
- [X] T019 [US1] Add SHA256 checksum generation and publication in `.github/workflows/publish-release.yml` (verify artifact integrity post-download)
- [ ] T020 [US1] Test release workflow with dry-run on feature branch before PR merge

**Checkpoint**: User Story 1 Complete. Developers can merge to `main` and releases are automatically published with all three architecture wheels.

---

## Phase 4: User Story 2 - System Packages for Ubuntu and Raspberry Pi OS (Priority: P2)

**Goal**: Enable one-command package manager installation via `apt install voicechanger` on Ubuntu 22.04+ and Raspberry Pi OS

**Independent Test**: Fresh Ubuntu 22.04 or Pi OS system; run `sudo apt install voicechanger`; verify daemon, CLI, GUI launcher installed; run `systemctl status voicechanger` and `which voicechanger`

### Tests for User Story 2

- [ ] T021 [P] [US2] Create contract test for .deb package structure in `tests/contract/test_deb_package.py` (verify systemd file present, entry points valid)
- [ ] T022 [US2] Create integration test for package installation in `tests/integration/test_package_install.py` (if feasible; may be manual on Pi hardware)

### Implementation for User Story 2

- [ ] T023 [P] [US2] Implement Debian package metadata (`depends`, `description`, `maintainer`) in `setup.cfg` or `pyproject.toml`
- [ ] T024 [US2] Generate .deb artifacts in build workflow via `scripts/release/build-deb.sh` for x86_64 in `.github/workflows/build-linux.yml`
- [ ] T025 [US2] Generate .deb artifacts for aarch64 in `.github/workflows/build-linux.yml`
- [ ] T026 [US2] Generate .deb artifacts for armv7l in `.github/workflows/build-linux.yml`
- [ ] T027 [US2] Publish .deb files to GitHub release in `.github/workflows/publish-release.yml` alongside wheels
- [ ] T028 [P] [US2] Create package installation documentation in `docs/INSTALLATION_DEB.md` (apt-get commands, repo setup, troubleshooting)
- [ ] T029 [US2] Manual testing on one Pi hardware target (aarch64 or armv7l); document blockers

**Checkpoint**: User Story 2 Complete. Users can install voicechanger via system package manager on all supported distributions.

---

## Phase 5: User Story 3 - Hardware Discovery via CLI or GUI (Priority: P2)

**Goal**: CLI commands `list-devices` and `set-device` enable headless Pi configuration; existing GUI Control tab reused

**Independent Test**: Fresh Pi with USB microphone; run `voicechanger list-devices`; output shows all devices with human-readable names; run `voicechanger set-device input <id>`; reboot and verify device persists

### Tests for User Story 3

- [ ] T030 [P] [US3] Create unit test for device enumeration in `tests/unit/test_cli_device_commands.py` (test `list-devices` output format, verify device properties present)
- [ ] T031 [P] [US3] Create unit test for device selection persistence in `tests/unit/test_device_persistence.py` (write device ID to config, read back, verify correctness)
- [X] T032 [US3] Create contract test for CLI interface in `tests/contract/test_cli_commands.py` (verify `list-devices` and `set-device` signatures, exit codes)
- [ ] T033 [US3] Create integration test for device selection across restarts in `tests/integration/test_device_persist_restart.py` (mock restart or use tmpdir persistence trick)

### Implementation for User Story 3

- [X] T034 [P] [US3] Implement `voicechanger list-devices` CLI command in `src/voicechanger/cli.py` (calls `device.py` enumeration; formats human-readable output)
- [X] T035 [P] [US3] Implement `voicechanger set-device input <id>` and `set-device output <id>` CLI commands in `src/voicechanger/cli.py`
- [X] T036 [US3] Verify device persistence logic in `src/voicechanger/config.py` (ensure selected device ID is written to config file)
- [ ] T037 [US3] Verify device restoration logic in `src/voicechanger/service.py` or `src/voicechanger/audio.py` (read device ID from config at startup)
- [X] T038 [US3] Add CLI help documentation and examples in `src/voicechanger/cli.py` docstrings
- [ ] T039 [US3] Create CLI reference documentation in `docs/CLI_DEVICE_COMMANDS.md` (list-devices output format, set-device examples, error cases)
- [ ] T040 [US3] Manual Pi testing for CLI device commands with USB audio hardware (note: may require Pi hardware access)

**Checkpoint**: User Story 3 Complete. CLI device commands work on headless Pi; device selection persists across reboots.

---

## Phase 6: User Story 4 - Production Headless Boot Mode (Priority: P3)

**Goal**: Toggle between desktop and headless modes via `voicechanger production-mode enable|disable`; systemd service auto-starts in headless mode

**Independent Test**: Configure system via GUI; run `voicechanger production-mode enable`; reboot and verify no desktop, service running; verify `systemctl status voicechanger` shows active; run `startx` and GUI launches; switch back via `disable` command

### Tests for User Story 4

- [ ] T041 [US4] Create unit test for production mode toggle script in `tests/unit/test_production_mode.sh` (verify systemd target switch, runlevel change)
- [ ] T042 [US4] Create integration test for headless boot simulation in `tests/integration/test_headless_boot.py` (mock systemd environment, verify service starts)

### Implementation for User Story 4

- [ ] T043 [P] [US4] Create systemd target files in `deploy/` for graphical and headless modes (e.g., `voicechanger-graphical.target`, `voicechanger-headless.target`)
- [X] T044 [US4] Implement production mode toggle CLI command in `src/voicechanger/cli.py` (calls `deploy/production-mode-toggle.sh` with enable/disable argument)
- [X] T045 [US4] Update systemd service file in `deploy/voicechanger.service` to respect headless/graphical target (use `PartOf` and `After` directives)
- [X] T046 [US4] Implement production mode toggle script in `deploy/production-mode-toggle.sh` (~50 lines; switches systemd target, updates default runlevel)
- [ ] T047 [US4] Add production mode documentation in `docs/PRODUCTION_MODE.md` (enable/disable commands, effects, rollback procedure, testing on Pi)
- [ ] T048 [US4] Manual Pi hardware testing for production mode toggle (requires Pi with X11; verify no desktop loads in headless mode, service runs)

**Checkpoint**: User Story 4 Complete. Production mode toggle works; headless boot is reliable; systemd service auto-starts.

---

## Phase 7: User Story 5 - Example Startup Files and Configuration Documentation (Priority: P3)

**Goal**: Comprehensive deployment guides for fresh Pi setup, Bluetooth pairing, production mode, emergency fallback; users can self-serve without support

**Independent Test**: First-time Pi OS user follows setup guide end-to-end (step-by-step); completes device config, test audio, within 30 minutes; no errors or undefined terms

### Tests for User Story 5

- [ ] T049 [US5] User journey test for setup guide documentation (external review: ask Beta user to follow DEPLOYMENT.md, collect feedback, iterate)

### Implementation for User Story 5

- [ ] T050 [P] [US5] Create deployment overview in `docs/DEPLOYMENT.md` (links to sub-guides, hardware requirements, estimated time per path)
- [ ] T051 [P] [US5] Create fresh Pi setup guide in `docs/SETUP_PI.md` (from Raspberry Pi OS install → voicechanger running; includes device selection, first audio test)
- [ ] T052 [P] [US5] Create Bluetooth setup guide in `docs/BLUETOOTH_SETUP.md` (pair Bluetooth mic, verify in device list, troubleshoot common issues)
- [ ] T053 [P] [US5] Create production mode workflow guide in `docs/PRODUCTION_MODE_WORKFLOW.md` (enable/disable, boot sequence, verify steps, rollback)
- [ ] T054 [P] [US5] Create emergency fallback guide in `docs/EMERGENCY_FALLBACK.md` (service won't start, reset config, reinstall, manual device selection)
- [ ] T055 [US5] Create building-from-source guide in `docs/BUILDING_FROM_SOURCE.md` (for developers; clone repo, build pedalboard, install locally, run tests)
- [ ] T056 [US5] Add screenshots and diagrams to guides (GUI screenshots, CLI output examples, boot sequence diagram for headless mode)
- [ ] T057 [US5] Create release notes template in `docs/RELEASE_NOTES_TEMPLATE.md` (version, download links, breaking changes, migration steps if any)
- [ ] T058 [US5] Documentation review and style consistency pass across all guides

**Checkpoint**: User Story 5 Complete. Comprehensive deployment documentation available; users can self-serve setup and troubleshooting.

---

## Phase 8: User Story 6 - Auto-Versioning on Merge to Main (Priority: P4)

**Goal**: Semantic versioning auto-bumped on merge; Git tag created; version strings updated in code

**Independent Test**: Merge PR to `main`; within 5 minutes, verify new Git tag exists with bumped version; verify `pyproject.toml` and `src/voicechanger/__init__.py` updated; GitHub Actions logs show version bump reason (major/minor/patch)

### Tests for User Story 6

- [ ] T059 [US6] Create unit test for version bumper script in `tests/unit/test_version_bump.py` (test major/minor/patch increment, file updates, tag creation)
- [ ] T060 [US6] Create contract test for version metadata in `tests/contract/test_version_metadata.py` (verify `__version__` present in `__init__.py`, matches `pyproject.toml`)

### Implementation for User Story 6

- [ ] T061 [US6] Implement version bumper script in `scripts/release/version-bump.py` (reads current version, detects bump type from commit message or branch prefix, updates files, creates Git tag)
- [ ] T062 [US6] Add version bump step to release workflow in `.github/workflows/multi-arch-release.yml` (calls `version-bump.py` with detected version increment)
- [ ] T063 [US6] Implement commit message parsing in `version-bump.py` to detect `[major]`, `[minor]`, or `[patch]` hints
- [ ] T064 [US6] Implement Git tag creation and push in `version-bump.py` (annotated tag with version as description)
- [ ] T065 [US6] Add rollback documentation in `docs/RELEASE_MANAGEMENT.md` (how to handle version conflicts, manual tag deletion if needed, retry steps)
- [ ] T066 [US6] Test version bumper on feature branch dry-run (simulate merge, verify version incremented correctly, tag created)

**Checkpoint**: User Story 6 Complete. Auto-versioning works; version is consistent across all files; Git tags created and pushed.

---

## Phase 9: User Story 7 - GitHub Release Publishing (Priority: P4)

**Goal**: Centralized GitHub release page with all artifacts, checksums, installation instructions

**Independent Test**: Navigate to GitHub releases; verify latest release includes wheels (3 arch), .deb packages (3 arch), pedalboard patch, checksums; click release notes link; verify instructions are current and downloadable links work

### Tests for User Story 7

- [ ] T067 [US7] Create integration test for release artifact publishing in `tests/integration/test_github_release.py` (mock GitHub API, verify all artifacts present, checksums valid)

### Implementation for User Story 7

- [X] T068 [P] [US7] Create release publication workflow in `.github/workflows/publish-release.yml` (uploads wheels, deb packages, patch, checksums to GitHub release)
- [X] T069 [US7] Implement GitHub release body template in `.github/workflows/publish-release.yml` (includes installation instructions, download links, breaking changes section, thanks)
- [X] T070 [US7] Add SHA256 checksum verification documentation in release notes (how to verify artifact integrity post-download)
- [ ] T071 [P] [US7] Create release notes snippets in `docs/RELEASE_ANNOUNCEMENT_TEMPLATE.md` (version highlight, new features, known issues, contact info)
- [ ] T072 [US7] Manual release test: publish release, verify GitHub release page shows all artifacts, download one wheel and one deb, verify checksums match
- [ ] T073 [US7] Create release management runbook in `docs/RELEASE_MANAGEMENT.md` (checklist for releases, how to patch hot-fix, rollback if needed)

**Checkpoint**: User Story 7 Complete. GitHub release page is the single source of truth for all voicechanger artifacts and installation instructions.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, testing, and operational readiness

**Checkpoint**: Feature complete and ready for production

- [ ] T074 [P] Audit entry points across all three architecture wheels; ensure CLI and GUI commands match
- [ ] T075 [P] Verify pedalboard patch applied correctly on all architectures; test LivePitchShift functionality on Pi hardware
- [ ] T076 [P] Validate README and main docs updated to reference new CLI device commands and production mode
- [ ] T077 Comprehensive end-to-end test on Raspberry Pi hardware (aarch64 if possible; bootstrap from GitHub release, complete setup, test device selection, production mode toggle)
- [ ] T078 Review and document any manual testing blockers or Pi-specific workarounds discovered during hardware testing
- [ ] T079 [P] Create troubleshooting FAQ in `docs/FAQ.md` (common errors, Pi device issues, systemd service debugging, logs location)
- [ ] T080 [P] Update project README with release info, installation methods (wheels, deb, source), link to deployment guide
- [ ] T081 Final documentation pass: consistency check, typos, link validation, version number consistency
- [ ] T082 Merge feature branch; create post-release ticket for ongoing support (monitor GitHub Issues for user feedback)

**Checkpoint**: Feature complete, documented, tested on hardware, ready for announcement.

---

## Implementation Strategy

### MVP Scope (Recommended for Initial Release)

For fastest time-to-value, deliver **User Stories 1 & 3 first**:
1. **US1** (P1): Cross-Architecture Binary Distribution — enables automated builds, foundation for everything else
2. **US3** (P2): CLI Device Commands — enables headless Pi setup, complements existing GUI

**Estimated effort**: US1 (~40 hours) + US3 (~20 hours) = ~60 hours / 2 weeks if 20 hrs/week available

**Post-MVP** (Week 3+): US2 (Packaging) → US4 (Production Mode) → US5 (Documentation) → US6 & US7 (Version Management & Release Publishing)

### Parallel Execution Opportunities

**Within US1 Builds** (Phase 3):
- T015, T016, T017 can run in parallel (three architecture build jobs)
- T013, T014 can start immediately (contract tests don't block builds)

**Between User Stories**:
- US2 (packaging) can start once US1 workflows are tested (T007–T012 complete)
- US3 (CLI commands) is independent; can start after T009 (entry points defined)
- US4 (production mode) depends on US3 CLI commands being stable
- US6 & US7 (versioning & release) depend on US1 build pipeline being solid

### Risk Mitigations

1. **Pedalboard patch fails on armv7l** → Pre-test patch on emulated armv7l before merging; have build step retry or alert if patch fails
2. **Device persistence across restart fails** → Integration test with config file mock to catch early; manual Pi testing required
3. **Documentation drift** → Use timestamp-based release snapshots in docs (e.g., `/docs/v0.3.0/DEPLOYMENT.md`); link from release notes to versioned docs, not main branch
4. **Systemd service conflicts in headless mode** → Test production mode toggle locally with systemd-run mock; have fallback runbook for manual recovery

---

## Success Criteria Checklist

Upon completion, **all** success criteria from spec.md must be verified:

- [ ] SC-001: GitHub release created within 30 min of merge to `main`
- [ ] SC-002: All three architecture wheels in release with correct checksums
- [ ] SC-003: `apt install voicechanger` succeeds on Ubuntu 22.04+ and Pi OS  
- [ ] SC-004: `voicechanger list-devices` works on fresh Pi within 2 min setup
- [ ] SC-005: Production mode toggle <10 sec; headless boot <30 sec
- [ ] SC-006: User follows Deployment.md and has working Pi in <30 min
- [ ] SC-007: All release artifacts downloadable and installable without post-install errors
