# Tasks: Realtime Voice Changer

**Input**: Design documents from `/specs/001-realtime-voice-changer/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included per constitution principle VII (Test-First).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, packaging, and basic structure

- [X] T001 Create project directory structure per plan.md (`src/voicechanger/`, `src/voicechanger/gui/`, `tests/unit/`, `tests/contract/`, `tests/integration/`, `native/patches/`, `profiles/builtin/`, `profiles/user/`)
- [X] T002 Create `pyproject.toml` with package metadata, dependencies (numpy), optional dev dependencies (pytest, ruff, mypy), and `[tool.pytest]` / `[tool.ruff]` / `[tool.mypy]` configuration
- [X] T003 [P] Create `src/voicechanger/__init__.py` with package version constant
- [X] T004 [P] Create `src/voicechanger/__main__.py` as entry point (`python -m voicechanger`)
- [X] T005 [P] Create `tests/conftest.py` with shared fixtures (tmp profile dirs, sample profile dicts)
- [X] T006 [P] Create `.gitignore` with Python patterns (`__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `*.egg-info/`, `.mypy_cache/`)
- [X] T007 [P] Create `native/README.md` documenting LivePitchShift patch rationale and build instructions
- [X] T008 [P] Create built-in profile files: `profiles/builtin/clean.json`, `profiles/builtin/high-pitched.json`, `profiles/builtin/low-pitched.json` per data-model.md schemas
- [X] T009 [P] Create default `voicechanger.toml` config file per data-model.md system configuration schema

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T010 [P] Write unit tests for Profile model in `tests/unit/test_profile.py` — test load/save JSON, validation (name regex, reserved names, schema_version), effect chain parsing, malformed input handling
- [X] T011 [P] Write unit tests for effects registry in `tests/unit/test_effects.py` — test type lookup, unknown type handling (skip with warning), parameter validation and clamping
- [X] T012 [P] Write unit tests for system config in `tests/unit/test_config.py` — test TOML loading, defaults, missing file handling, invalid values
- [X] T013 [P] Write unit tests for ProfileRegistry in `tests/unit/test_registry.py` — test discovery, list, get, create, delete, builtin protection, name collision rejection
- [X] T014 Implement Profile model in `src/voicechanger/profile.py` — dataclass with `schema_version`, `name`, `author`, `description`, `effects`; `load()` / `save()` JSON serialization; name validation regex `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$`
- [X] T015 Implement Effect model and type registry in `src/voicechanger/effects.py` — Effect dataclass (`type`, `params`), `EFFECT_REGISTRY` dict mapping type strings to parameter schemas, `validate_effect()`, unknown type skip logic
- [X] T016 Implement system config loader in `src/voicechanger/config.py` — load TOML via `tomllib`, provide defaults for all fields, resolve paths (`builtin_dir`, `user_dir`, `socket_path`)
- [X] T017 Implement ProfileRegistry in `src/voicechanger/registry.py` — scan builtin/user dirs, `list()`, `get(name)`, `create(profile)`, `delete(name)`, `exists(name)`, `is_builtin(name)`, reject user profiles with builtin names
- [X] T018 Verify all foundational unit tests pass: `pytest tests/unit/`

**Checkpoint**: Foundation ready — Profile, Effects, Config, Registry all implemented and tested. User story implementation can begin.

---

## Phase 3: User Story 1 — Live Voice Transformation (Priority: P1) 🎯 MVP

**Goal**: Audio service captures mic input, applies active profile's effect chain via Pedalboard AudioStream, outputs to speaker in real time with ≤50 ms latency. Falls back to pass-through on profile load failure.

**Independent Test**: Start service with a known profile, verify AudioStream is opened with correct plugins, verify pass-through fallback on bad profile.

### Tests for User Story 1

- [X] T019 [P] [US1] Write unit tests for AudioPipeline in `tests/unit/test_audio_pipeline.py` — test state machine transitions (STOPPED→STARTING→RUNNING→STOPPING), plugin list construction from profile, pass-through fallback on bad profile, profile hot-switch
- [X] T020 [P] [US1] Write unit tests for device enumeration in `tests/unit/test_device.py` — test parsing `aplay -l` / `arecord -l` output, default device fallback, preferred device detection
- [X] T021 [P] [US1] Write integration test for audio pipeline in `tests/integration/test_audio_pipeline.py` — test full pipeline lifecycle with mock AudioStream (start, apply profile, switch profile, stop)

### Implementation for User Story 1

- [X] T022 [US1] Implement device enumeration in `src/voicechanger/device.py` — parse `aplay -l`/`arecord -l` subprocess output, list input/output devices, background polling thread for preferred device, `DeviceMonitor` class
- [X] T023 [US1] Implement AudioPipeline in `src/voicechanger/audio.py` — `AudioStream` lifecycle management, state machine (STOPPED/STARTING/RUNNING/DEGRADED/SWITCHING_PROFILE/STOPPING), build `Pedalboard` plugin list from Profile, `switch_profile()` via plugins list replacement, pass-through fallback (FR-003)
- [X] T024 [US1] Implement service daemon in `src/voicechanger/service.py` — Unix socket server using `selectors`, signal handling (SIGTERM/SIGINT), `threading.Event`-based shutdown, integrate AudioPipeline + ProfileRegistry + DeviceMonitor, IPC command dispatch
- [X] T025 [US1] Write contract tests for IPC protocol in `tests/contract/test_ipc.py` — test all 5 IPC commands (`switch_profile`, `list_profiles`, `get_profile`, `get_status`, `reload_profiles`), error codes, JSON-over-newline framing, 64 KB message size limit

**Checkpoint**: Service starts, opens audio stream, applies profile effects, accepts IPC commands, handles pass-through fallback — all testable without real audio hardware via mocked AudioStream.

---

## Phase 4: User Story 2 — Character Profile Management via CLI (Priority: P2)

**Goal**: CLI commands to list, show, switch, create, delete, and export profiles. CLI communicates with running service over Unix socket for runtime operations.

**Independent Test**: Run CLI commands against profile directories and a mock/running service, verify correct output, exit codes, and profile file creation/deletion.

### Tests for User Story 2

- [X] T026 [P] [US2] Write contract tests for CLI commands in `tests/contract/test_cli.py` — test all 9 CLI commands (serve, profile list/show/switch/create/delete/export, device list, status, process), argument parsing, exit codes, text + JSON output formats
- [X] T027 [P] [US2] Write integration test for CLI-to-service flow in `tests/integration/test_service.py` — test CLI profile switch reaching running service, profile create appearing in list, profile delete removing file

### Implementation for User Story 2

- [X] T028 [US2] Implement CLI framework in `src/voicechanger/cli.py` — argparse-based command routing, `serve` command (delegates to service.py), `profile list/show/create/delete/export` subcommands, `device list`, `status`, `process` commands
- [X] T029 [US2] Implement IPC client helper in `src/voicechanger/cli.py` — `_send_ipc_command()` for Unix socket communication with running service, JSON-over-newline framing, connection error handling
- [X] T030 [US2] Implement `profile create` logic in `src/voicechanger/cli.py` — parse `--effect TYPE KEY=VALUE` repeatable args, validate via effects registry, construct Profile, save via ProfileRegistry
- [X] T031 [US2] Implement `profile export` in `src/voicechanger/cli.py` — read profile from registry, write JSON to output path
- [X] T032 [US2] Wire `__main__.py` entry point to CLI in `src/voicechanger/__main__.py`

**Checkpoint**: Full CLI operational — all profile management commands work, IPC commands reach the service, text and JSON output modes function correctly.

---

## Phase 5: User Story 3 — Profile Authoring GUI (Priority: P3)

**Goal**: Desktop tkinter GUI on dev machine for real-time effect parameter adjustment with live audio feedback, saving results as portable profile files.

**Independent Test**: Launch GUI, adjust sliders, verify profile JSON file is saved with correct parameters. Verify saved profile loads in CLI mode.

### Tests for User Story 3

- [X] T033 [P] [US3] Write unit tests for GUI profile authoring logic in `tests/unit/test_gui.py` — test parameter-to-profile conversion, slider value mapping to effect params, profile save/load round-trip (NO tkinter dependency in tests — test the data logic only)

### Implementation for User Story 3

- [X] T034 [US3] Implement GUI application in `src/voicechanger/gui/app.py` — tkinter window with effect type dropdown, parameter sliders per effect type, add/remove/reorder effects, live audio preview via AudioPipeline, save as profile JSON, profile name/author/description fields
- [X] T035 [US3] Create `src/voicechanger/gui/__init__.py` with GUI entry point function

**Checkpoint**: GUI launches on dev machine, effects adjustable in real time with audio feedback, profiles saved are compatible with headless service.

---

## Phase 6: User Story 4 — Community Profile Distribution (Priority: P4)

**Goal**: Profiles are portable single-file JSON. Copying a profile file into the user profiles directory makes it immediately available. Cross-architecture compatibility verified.

**Independent Test**: Export a profile from one installation, copy to a fresh profiles directory, verify it appears in profile list and loads correctly.

### Tests for User Story 4

- [X] T036 [P] [US4] Write integration test for profile portability in `tests/integration/test_profile_portability.py` — test export/import round-trip, cross-directory copy, unknown effect type graceful skip with warning

### Implementation for User Story 4

- [X] T037 [US4] Implement `reload_profiles` IPC command handling in `src/voicechanger/service.py` — re-scan profile directories on demand, return updated profile count
- [X] T038 [US4] Verify profile portability — ensure Profile model serialization is architecture-independent (no platform-specific paths or binary data), add validation in `profile.py` for unknown schema_version forward compatibility

**Checkpoint**: Profile files are self-contained, portable, and work across x86_64 and aarch64 without modification.

---

## Phase 7: User Story 5 — Offline File Processing (Priority: P5)

**Goal**: Process pre-recorded audio files through a profile's effect chain without running the service or requiring audio hardware.

**Independent Test**: Process a known WAV file through a profile, verify output file exists with expected duration and channel count.

### Tests for User Story 5

- [X] T039 [P] [US5] Write integration test for offline processing in `tests/integration/test_offline_processing.py` — test WAV file processing through profile, output file creation, duration preservation, mono/stereo handling, use stock `PitchShift` (not `LivePitchShift`)

### Implementation for User Story 5

- [X] T040 [US5] Implement `process` command in `src/voicechanger/cli.py` — read input audio file via pedalboard `ReadableAudioFile`, build offline `Pedalboard` (map `LivePitchShift` → `PitchShift` for offline), process audio, write output via `WritableAudioFile`

**Checkpoint**: `voicechanger process input.wav output.wav --profile darth-vader` produces correct output file without requiring running service.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Quality, reliability, and deployment readiness

- [X] T041 [P] Add structured JSON logging throughout service in `src/voicechanger/service.py` — configure `logging` with JSON formatter, log profile changes, device events, errors, startup/shutdown (FR-012)
- [X] T042 [P] Create systemd service unit file in `deploy/voicechanger.service` — `Type=simple`, `Restart=on-failure`, `RestartSec=5`, `ExecStart=voicechanger serve --config /etc/voicechanger/voicechanger.toml` (FR-002, SC-007)
- [X] T043 [P] Create `src/py.typed` marker file for PEP 561 type checking support
- [X] T044 Run full test suite and fix any failures: `cd src && pytest && ruff check .`
- [X] T045 Run quickstart.md validation — verify all documented commands work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2)
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) + US1 (service.py needed for IPC)
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) + US1 (AudioPipeline needed for live preview)
- **User Story 4 (Phase 6)**: Depends on Foundational (Phase 2) + US1 (service reload command)
- **User Story 5 (Phase 7)**: Depends on Foundational (Phase 2) only (offline, no service needed)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P2)**: Depends on US1 (needs service.py for IPC client commands)
- **US3 (P3)**: Depends on US1 (needs AudioPipeline for live preview)
- **US4 (P4)**: Depends on US1 (needs service reload_profiles IPC command)
- **US5 (P5)**: Can start after Phase 2 — independent of service (offline only)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/data before services
- Services before endpoints/CLI
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks T003–T009 marked [P] can run in parallel
- All Foundational test tasks T010–T013 marked [P] can run in parallel
- US1 test tasks T019–T021 marked [P] can run in parallel
- US5 (Phase 7) can run in parallel with US2/US3/US4 since it has no service dependency
- All Polish tasks T041–T043 marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task T019: "Unit tests for AudioPipeline in tests/unit/test_audio_pipeline.py"
Task T020: "Unit tests for device enumeration in tests/unit/test_device.py"
Task T021: "Integration test for audio pipeline in tests/integration/test_audio_pipeline.py"

# Then sequential implementation:
Task T022: "Implement device enumeration in src/voicechanger/device.py"
Task T023: "Implement AudioPipeline in src/voicechanger/audio.py"
Task T024: "Implement service daemon in src/voicechanger/service.py"
Task T025: "Contract tests for IPC protocol in tests/contract/test_ipc.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 independently — service starts, audio processed, IPC works
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → CLI fully operational
4. Add User Story 5 → Test independently → Offline processing works (can run parallel with US3/US4)
5. Add User Story 3 → Test independently → GUI authoring works
6. Add User Story 4 → Test independently → Community distribution ready
7. Polish phase → All quality and deployment tasks

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (MVP — highest priority)
   - Developer B: User Story 5 (offline — no US1 dependency)
3. After US1 completes:
   - Developer A: User Story 2 (CLI — needs service from US1)
   - Developer B: User Story 3 (GUI — needs AudioPipeline from US1)
   - Developer C: User Story 4 (portability — needs reload from US1)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution principle VII (Test-First) requires test tasks in all phases
