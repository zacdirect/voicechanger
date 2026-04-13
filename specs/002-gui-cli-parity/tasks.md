# Tasks: GUI–CLI Feature Parity

**Input**: Design documents from `/specs/002-gui-cli-parity/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/gui-views.md, contracts/ipc.md, quickstart.md

**Tests**: Included per Constitution VII (Test-First). Red-Green-Refactor: write tests first, verify they fail, then implement.

**Organization**: Tasks grouped by user story. 7 stories from spec.md (P1→P3 priority order).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to user story (US1–US7) — present only in user-story phases

---

## Phase 1: Setup

**Purpose**: Create package structure for the new GUI views subpackage

- [ ] T001 Create gui/views/ package with __init__.py in src/voicechanger/gui/views/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story: shared state, IPC client, app shell

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T002 [P] Write unit tests for PipelineMode, GuiState, EditingProfile, and generate_draft_name() in tests/unit/test_gui_state.py
- [ ] T003 [P] Write unit tests for IpcClient (connect, send_command, 5 base commands, error handling, close) in tests/unit/test_ipc_client.py

### Implementation for Foundation

- [ ] T004 [P] Implement PipelineMode enum, EditingProfile dataclass, GuiState dataclass, and generate_draft_name() in src/voicechanger/gui/state.py
- [ ] T005 [P] Implement IpcClient async wrapper (connect, send_command, switch_profile, list_profiles, get_profile, get_status, reload_profiles, close) in src/voicechanger/gui/ipc_client.py
- [ ] T006 Rewrite app.py as NavigationRail shell with 4-destination view routing (Control, Profiles, Editor, Tools) in src/voicechanger/gui/app.py
- [ ] T007 Update launch_gui() with embedded/remote mode detection (probe socket on startup) in src/voicechanger/gui/__init__.py

**Checkpoint**: Foundation ready — GuiState, IpcClient, and NavigationRail shell are functional. User story implementation can begin.

---

## Phase 3: User Story 1 — Service Control from the GUI (Priority: P1) 🎯 MVP

**Goal**: Start/stop pipeline, monitor toggle, IPC remote control detection, basic status display

**Independent Test**: Launch GUI → press Start → verify audio runs → toggle monitor → press Stop → confirm pipeline halts. In remote mode: launch while service is running → verify GUI detects and connects via IPC.

### Tests for User Story 1

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Write unit tests for AudioPipeline.set_monitor_enabled() in tests/unit/test_audio_pipeline.py
- [ ] T009 [P] [US1] Write unit tests for _cmd_set_monitor IPC handler in tests/unit/test_service.py (new file)
- [ ] T010 [P] [US1] Write contract test for set_monitor IPC command round-trip in tests/contract/test_ipc.py
- [ ] T011 [P] [US1] Write integration test for GUI↔Service remote control flow (connect, get_status, set_monitor) in tests/integration/test_gui_ipc.py (new file)

### Implementation for User Story 1

- [ ] T012 [P] [US1] Add set_monitor_enabled(enabled: bool) method to AudioPipeline (output mute gain toggle) in src/voicechanger/audio.py
- [ ] T013 [US1] Implement _cmd_set_monitor IPC handler and add monitor_enabled field to _cmd_get_status response in src/voicechanger/service.py
- [ ] T014 [US1] Add set_monitor() method to IpcClient in src/voicechanger/gui/ipc_client.py
- [ ] T015 [US1] Implement Control view layout (start/stop buttons, profile dropdown, monitor toggle, status area placeholder) in src/voicechanger/gui/views/control.py
- [ ] T016 [US1] Implement start/stop pipeline actions (embedded: AudioPipeline.start/stop; remote: display "Service already running" info) in src/voicechanger/gui/views/control.py
- [ ] T017 [US1] Implement monitor toggle action (embedded: pipeline.set_monitor_enabled; remote: IpcClient.set_monitor) in src/voicechanger/gui/views/control.py
- [ ] T018 [US1] Implement status polling loop (remote: IpcClient.get_status every 2s; embedded: pipeline.get_status periodic read) in src/voicechanger/gui/views/control.py

**Checkpoint**: User can start/stop pipeline from GUI, toggle monitor, and GUI auto-detects a running service via IPC.

---

## Phase 4: User Story 2 — Audio Device Selection in the GUI (Priority: P1)

**Goal**: Device enumeration dropdowns, device change during operation, IPC set_device for remote mode

**Independent Test**: Launch GUI → verify device dropdowns populated → select non-default device → start pipeline → confirm audio routes through selected device. In remote mode: change device → verify IPC round-trip and pipeline restarts.

### Tests for User Story 2

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T019 [P] [US2] Write unit tests for _cmd_set_device IPC handler (validate, restart, fallback) in tests/unit/test_service.py
- [ ] T020 [P] [US2] Write contract test for set_device IPC command round-trip in tests/contract/test_ipc.py
- [ ] T021 [P] [US2] Write unit tests for device dropdown rendering and device-unavailable fallback logic in tests/unit/test_gui.py

### Implementation for User Story 2

- [ ] T022 [US2] Implement _cmd_set_device IPC handler (validate device, stop pipeline, restart with new device, fallback on failure) in src/voicechanger/service.py
- [ ] T023 [US2] Add set_device() method to IpcClient in src/voicechanger/gui/ipc_client.py
- [ ] T024 [US2] Implement device enumeration dropdowns (input/output) with refresh button using DeviceMonitor in src/voicechanger/gui/views/control.py
- [ ] T025 [US2] Implement device change action (embedded: store in GuiState, apply on start; remote: IpcClient.set_device) in src/voicechanger/gui/views/control.py
- [ ] T026 [US2] Implement device-unavailable fallback (fall back to system default, show notification) in src/voicechanger/gui/views/control.py

**Checkpoint**: User can select input/output devices from dropdowns and change devices during operation in both embedded and remote modes.

---

## Phase 5: User Story 3 — Profile Management in the GUI (Priority: P2)

**Goal**: Full profile CRUD via Profiles view + Editor view (browse, activate, create, edit, delete, export, import, builtin auto-fork)

**Independent Test**: Launch GUI → open Profiles view → verify grouped list → activate a profile → create new → delete user profile → export → import. Open Editor → modify builtin → verify auto-fork → save.

### Tests for User Story 3

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T027 [P] [US3] Write unit tests for ProfileRegistry.update() in tests/unit/test_registry.py
- [ ] T028 [P] [US3] Write unit tests for Profiles view actions (activate, delete, export, import) in tests/unit/test_gui.py
- [ ] T029 [P] [US3] Write unit tests for Editor view save logic and builtin auto-fork behavior in tests/unit/test_gui.py
- [ ] T030 [P] [US3] Write contract test for Profiles view layout and actions in tests/contract/test_gui_views.py (new file)
- [ ] T031 [P] [US3] Write contract test for Editor view layout and actions in tests/contract/test_gui_views.py

### Implementation for User Story 3

- [ ] T032 [US3] Implement ProfileRegistry.update(profile) method (atomic overwrite of user profile) in src/voicechanger/registry.py
- [ ] T033 [US3] Implement Profiles view layout (grouped list by builtin/user, detail panel, action buttons) in src/voicechanger/gui/views/profiles.py
- [ ] T034 [US3] Implement activate action (embedded: pipeline.switch_profile; remote: IpcClient.switch_profile) in src/voicechanger/gui/views/profiles.py
- [ ] T035 [US3] Implement delete action with ft.AlertDialog confirmation (disable for builtins) in src/voicechanger/gui/views/profiles.py
- [ ] T036 [P] [US3] Implement export and import actions using ft.FilePicker (save_file / pick_files → registry) in src/voicechanger/gui/views/profiles.py
- [ ] T037 [US3] Refactor existing editor logic from app.py into Editor view (effect chain, sliders, preview) in src/voicechanger/gui/views/editor.py
- [ ] T038 [US3] Implement builtin auto-fork (detect builtin → generate_draft_name → update name field → info banner) in src/voicechanger/gui/views/editor.py
- [ ] T039 [US3] Implement save actions (Save: registry.update for user / registry.create for forked; Save As: name prompt + create) in src/voicechanger/gui/views/editor.py
- [ ] T040 [US3] Implement "Edit" cross-view navigation (Profiles → Editor tab, load into EditingProfile state) in src/voicechanger/gui/views/profiles.py

**Checkpoint**: Full profile lifecycle works — browse, activate, create, edit in-place, auto-fork builtins, delete, export, import.

---

## Phase 6: User Story 4 — Real-Time Audio Level Monitoring (Priority: P2)

**Goal**: Input and output level meters updating ≥15fps during pipeline operation

**Independent Test**: Start pipeline with known audio source → verify input meter responds to mic input → verify output meter reflects processed signal → verify meters idle on silence.

### Tests for User Story 4

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T041 [P] [US4] Write unit tests for AudioPipeline level_callback (RMS computation, thread-safety) in tests/unit/test_audio_pipeline.py
- [ ] T042 [P] [US4] Write unit tests for level meter rendering and color threshold logic in tests/unit/test_gui.py

### Implementation for User Story 4

- [ ] T043 [US4] Add level_callback to AudioPipeline (compute RMS in audio loop, store in thread-safe values) in src/voicechanger/audio.py
- [ ] T044 [US4] Implement level meter UI (dual ft.ProgressBar with green/yellow/red thresholds, dB labels) in src/voicechanger/gui/views/control.py
- [ ] T045 [US4] Implement level polling async loop (page.run_task, ~60ms interval, ≥15fps update rate) in src/voicechanger/gui/views/control.py

**Checkpoint**: Level meters visually respond to audio input and output in real time at ≥15fps.

---

## Phase 7: User Story 5 — Service Status Dashboard (Priority: P3)

**Goal**: Status panel showing active profile, pipeline state, uptime, devices, sample rate, buffer size

**Independent Test**: Start pipeline → verify each status field matches `voicechanger status --json` output → switch profile → verify status updates within 1s.

### Tests for User Story 5

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T046 [P] [US5] Write unit tests for status panel field rendering and update logic in tests/unit/test_gui.py

### Implementation for User Story 5

- [ ] T047 [US5] Implement status panel layout (profile, state, uptime, input/output device, sample rate, buffer size) in src/voicechanger/gui/views/control.py
- [ ] T048 [US5] Wire status panel updates to polling loop (refresh within 1s on profile/device/state change) in src/voicechanger/gui/views/control.py

**Checkpoint**: Status dashboard shows all operational fields and updates promptly on state changes.

---

## Phase 8: User Story 6 — Offline File Processing in the GUI (Priority: P3)

**Goal**: Select input file, choose profile, process to output file with progress indicator

**Independent Test**: Select WAV file → choose profile with pitch shift → process → verify output file has expected transformation. Verify error on invalid file.

### Tests for User Story 6

> **Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T049 [P] [US6] Write unit tests for Tools view processing actions and error handling in tests/unit/test_gui.py
- [ ] T050 [P] [US6] Write contract test for Tools view layout in tests/contract/test_gui_views.py

### Implementation for User Story 6

- [ ] T051 [US6] Implement Tools view layout (input/output file pickers, profile dropdown, process button, progress bar) in src/voicechanger/gui/views/tools.py
- [ ] T052 [US6] Implement offline processing action (page.run_thread → offline.process_file, progress updates) in src/voicechanger/gui/views/tools.py
- [ ] T053 [US6] Implement error handling for missing/unreadable files and processing failures in src/voicechanger/gui/views/tools.py

**Checkpoint**: Offline file processing works end-to-end with progress display and error feedback.

---

## Phase 9: User Story 7 — Desktop-First GUI with Cross-Platform Layout (Priority: P3)

**Goal**: GUI optimized for 1080p+ desktop with graceful degradation on Pi HDMI

**Independent Test**: Launch on desktop → verify full-space layout → optionally launch on Pi → verify core controls accessible.

- [ ] T054 [US7] Set default window dimensions and add responsive expand/min_width constraints to NavigationRail shell in src/voicechanger/gui/app.py
- [ ] T055 [US7] Add ft.ListView scroll wrappers to all 4 view modules for low-resolution display fallback in src/voicechanger/gui/views/

**Checkpoint**: GUI makes effective use of desktop space and remains functional at lower resolutions.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Validation, cleanup, and documentation

- [ ] T056 [P] Update GUI usage instructions (launch, remote mode, views overview) in README.md
- [ ] T057 Run quickstart.md validation (launch GUI, test all views, verify IPC remote control flow) in specs/002-gui-cli-parity/quickstart.md
- [ ] T058 Run full test suite and linter to validate all tests pass and code quality in src/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational — first story, establishes Control view
- **US2 (Phase 4)**: Depends on Foundational — extends Control view (can parallel with US1 if careful about control.py)
- **US3 (Phase 5)**: Depends on Foundational — independent Profiles + Editor views
- **US4 (Phase 6)**: Depends on US1 (Control view must exist) — extends Control view with meters
- **US5 (Phase 7)**: Depends on US1 (status polling loop must exist) — extends Control view status panel
- **US6 (Phase 8)**: Depends on Foundational — independent Tools view
- **US7 (Phase 9)**: Depends on all view phases (3–8) — layout polish pass
- **Polish (Phase 10)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational → no story dependencies → **MVP target**
- **US2 (P1)**: After Foundational → can start in parallel with US1 (both extend control.py — coordinate)
- **US3 (P2)**: After Foundational → independent (Profiles + Editor views) → can parallel with US1/US2
- **US4 (P2)**: After US1 → extends Control view with level meters
- **US5 (P3)**: After US1 → extends Control view status panel
- **US6 (P3)**: After Foundational → independent (Tools view) → can parallel with all stories
- **US7 (P3)**: After all views exist → layout polish

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Infrastructure changes (audio.py, service.py, registry.py) before GUI views
3. View layout before view actions
4. Core actions before edge case handling
5. Story complete before moving to next priority

### Parallel Opportunities

**Phase 2** (after Setup):
- T002 ∥ T003 (tests — different files)
- T004 ∥ T005 (impl — state.py ∥ ipc_client.py)

**Phase 3** (after Foundational):
- T008 ∥ T009 ∥ T010 ∥ T011 (all test tasks — different files)
- T012 ∥ T014 (audio.py ∥ ipc_client.py)

**Phase 4** (after Foundational):
- T019 ∥ T020 ∥ T021 (all test tasks — different files)
- T022 ∥ T023 (service.py ∥ ipc_client.py)

**Phase 5** (after Foundational):
- T027 ∥ T028 ∥ T029 ∥ T030 ∥ T031 (all test tasks)
- T036 is [P] within the phase (export/import — no deps on other US3 tasks)

**Cross-story parallelism** (after Foundational):
- US3 (Profiles + Editor) ∥ US6 (Tools) — entirely different views and files
- US1 + US2 can be interleaved (both touch control.py but different sections)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (write first, must fail):
T008: "Unit tests for AudioPipeline.set_monitor_enabled() in tests/unit/test_audio_pipeline.py"
T009: "Unit tests for _cmd_set_monitor handler in tests/unit/test_service.py"
T010: "Contract test for set_monitor IPC in tests/contract/test_ipc.py"
T011: "Integration test for GUI↔Service in tests/integration/test_gui_ipc.py"

# Then launch parallel impl:
T012: "AudioPipeline.set_monitor_enabled() in src/voicechanger/audio.py"
T014: "IpcClient.set_monitor() in src/voicechanger/gui/ipc_client.py"

# Then sequential (depends on T012):
T013 → T015 → T016 → T017 → T018
```

## Parallel Example: Cross-Story

```bash
# After Foundational completes, these stories can proceed in parallel:
Developer A: US1 (Phase 3) — Control view core
Developer B: US3 (Phase 5) — Profiles + Editor views
Developer C: US6 (Phase 8) — Tools view

# US4 and US5 wait for US1's Control view to exist, then extend it.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 — Service Control
4. **STOP and VALIDATE**: Can start/stop pipeline, toggle monitor, remote-control via IPC
5. Deploy/demo if ready — this is the minimum viable GUI

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Test independently → **MVP!** (start/stop, monitor, IPC)
3. US2 → Test independently → Device selection works
4. US3 → Test independently → Full profile management
5. US4 → Test independently → Level meters live
6. US5 → Test independently → Status dashboard complete
7. US6 → Test independently → Offline processing available
8. US7 + Polish → Layout refined, all tests green

Each story adds value without breaking previous stories.

---

## Notes

- [P] marks tasks that can run in parallel (different files, no incomplete dependencies)
- [US*] labels map tasks to user stories from spec.md for traceability
- Each user story should be independently completable and testable
- Constitution VII: Write tests first, verify they fail, then implement
- IPC extension (set_device, set_monitor) is defined in contracts/ipc.md — extends feature 001 protocol
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently