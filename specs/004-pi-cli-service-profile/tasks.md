# Tasks: Pi CLI Service Profile Ownership

**Input**: Design documents from `/specs/004-pi-cli-service-profile/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/service-config-and-profile-loading.md`, `quickstart.md`

**Tests**: Tests are included because the specification and constitution require explicit, verifiable startup and profile-resolution behavior.

**Organization**: Tasks are grouped by user story for independent implementation and validation.

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare focused test/doc scaffolding for the feature.

- [ ] T001 Create feature contract test module scaffold in `tests/contract/test_profile_ownership_contract.py`
- [ ] T002 Create feature integration test module scaffold in `tests/integration/test_profile_startup_resolution.py`
- [ ] T003 [P] Create feature unit test module scaffold in `tests/unit/test_profile_resolution_policy.py`
- [ ] T004 [P] Create operator workflow documentation stub in `docs/DEPLOYMENT.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement cross-story runtime policy primitives before story work.

**⚠️ CRITICAL**: No user story implementation starts until this phase is complete.

- [ ] T005 Implement authoritative user-config resolution helper in `src/voicechanger/config.py`
- [ ] T006 Implement effective-config provenance metadata model in `src/voicechanger/config.py`
- [ ] T007 [P] Implement system-authoritative built-in profile guard logic in `src/voicechanger/registry.py`
- [ ] T008 [P] Implement profile source tagging and override warning hooks in `src/voicechanger/registry.py`
- [ ] T009 Implement startup diagnostic payload structure (config path, dirs, source) in `src/voicechanger/service.py`
- [ ] T010 Implement shared diagnostics formatter for CLI/GUI consumption in `src/voicechanger/service.py`
- [ ] T011 [P] Implement user-overrides-builtin hardware hint precedence in `src/voicechanger/hardware.py`

**Checkpoint**: Foundational config/profile resolution policy is available to all stories.

---

## Phase 3: User Story 1 - Reliable CLI-Boot Startup for User-Owned Service (Priority: P1) 🎯 MVP

**Goal**: Service starts reliably in CLI boot using user-owned config/profile context.

**Independent Test**: Boot/start with user context and verify active profile load, fallback-to-clean behavior, and non-fatal unreadable-user-dir behavior.

### Tests for User Story 1

- [ ] T012 [P] [US1] Add startup resolution contract tests in `tests/contract/test_profile_ownership_contract.py`
- [ ] T013 [P] [US1] Add startup fallback integration tests in `tests/integration/test_profile_startup_resolution.py`
- [ ] T014 [P] [US1] Add unreadable-user-dir fallback unit tests in `tests/unit/test_profile_resolution_policy.py`

### Implementation for User Story 1

- [ ] T015 [US1] Enforce user-config-only runtime resolution in `src/voicechanger/service.py`
- [ ] T016 [US1] Implement fallback-to-clean startup path with warning logs in `src/voicechanger/service.py`
- [ ] T017 [US1] Implement shipped-default plus clean/pass-through and known-good hardware polling fallback for unreadable user dirs in `src/voicechanger/service.py`
- [ ] T018 [US1] Wire startup status fields (resolved config and profile dirs) into IPC status response in `src/voicechanger/service.py`
- [ ] T019 [US1] Ensure service unit guidance targets user-owned config path in `deploy/voicechanger.service`

**Checkpoint**: CLI-boot startup is reliable and independently testable.

---

## Phase 4: User Story 2 - Profile Authoring and Deployment Loop Across Devices (Priority: P1)

**Goal**: Profile authoring/save/activation works predictably with user-owned profiles and last-save-wins semantics.

**Independent Test**: Save/update profile, set active profile, reboot/start service, confirm selected profile is loaded.

### Tests for User Story 2

- [ ] T020 [P] [US2] Add CLI active-profile validation contract tests in `tests/contract/test_cli.py`
- [ ] T021 [P] [US2] Add profile save overwrite semantics integration tests in `tests/integration/test_profile_portability.py`
- [ ] T022 [P] [US2] Add built-in override denial unit tests in `tests/unit/test_registry.py`

### Implementation for User Story 2

- [ ] T023 [US2] Enforce profile existence validation before config persistence in `src/voicechanger/cli.py`
- [ ] T024 [US2] Fix profile switch persistence to active config path in `src/voicechanger/cli.py`
- [ ] T025 [US2] Implement deterministic last-save-wins for user profile saves in `src/voicechanger/registry.py`
- [ ] T026 [US2] Deny/ignore user local `built-in` overrides with warning diagnostics in `src/voicechanger/registry.py`
- [ ] T027 [US2] Align GUI profile save/update flow with last-save-wins and built-in protection in `src/voicechanger/gui/logic.py`
- [ ] T028 [US2] Expose actionable save/switch validation errors in GUI profile views in `src/voicechanger/gui/views/profiles.py`

**Checkpoint**: Authoring/deploy loop is independently functional across CLI/GUI.

---

## Phase 5: User Story 3 - Path Resolution and Gap Visibility for Operators (Priority: P2)

**Goal**: Operators can quickly identify effective config/profile paths and source decisions.

**Independent Test**: Query status/logs and identify resolved paths, profile source, and mismatch warnings within 30 seconds.

### Tests for User Story 3

- [ ] T029 [P] [US3] Add diagnostics contract tests for status payload fields in `tests/contract/test_ipc.py`
- [ ] T030 [P] [US3] Add CLI status output integration tests for resolved-path visibility in `tests/integration/test_service.py`
- [ ] T031 [P] [US3] Add unit tests for profile and hardware source classification in `tests/unit/test_service.py`

### Implementation for User Story 3

- [ ] T032 [US3] Add effective config/profile/hardware source fields to service status response in `src/voicechanger/service.py`
- [ ] T033 [US3] Render resolved path and profile/hardware source details in CLI status output in `src/voicechanger/cli.py`
- [ ] T034 [US3] Surface source and warning metadata in GUI control state in `src/voicechanger/gui/state.py`
- [ ] T035 [US3] Display diagnostics warnings in GUI control view in `src/voicechanger/gui/views/control.py`

**Checkpoint**: Diagnostics are independently visible and actionable.

---

## Phase 6: User Story 4 - Canonical Ownership Model Documentation and Enforcement (Priority: P3)

**Goal**: Canonical setup guidance is explicit and non-canonical setups are warned clearly.

**Independent Test**: Follow documented canonical flow end-to-end; verify non-canonical setup emits warnings and corrective guidance.

### Tests for User Story 4

- [ ] T036 [P] [US4] Add canonical/non-canonical ownership warning integration tests in `tests/integration/test_service.py`
- [ ] T037 [P] [US4] Add docs quickstart validation checklist covering missing config, missing profile, permission denied, and mismatched runtime user in `specs/004-pi-cli-service-profile/quickstart.md`

### Implementation for User Story 4

- [ ] T038 [US4] Implement explicit ownership mismatch warning messaging at startup in `src/voicechanger/service.py`
- [ ] T039 [US4] Document canonical single-user deployment flow plus recovery guidance for missing config, missing profile, permission denied, unreadable dirs, and hardware-hint override behavior in `docs/DEPLOYMENT.md`
- [ ] T040 [US4] Document user-config-only policy, built-in profile authority, and hardware-hint override rule in `README.md`
- [ ] T041 [US4] Update feature quickstart for final policy wording, unreadable-dir fallback, built-in profile authority, and advisory hardware-hint rules in `specs/004-pi-cli-service-profile/quickstart.md`

**Checkpoint**: Canonical model is documented and enforcement signals are independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, regression coverage, and release readiness.

- [ ] T042 [P] Run full contract/integration/unit regression for touched areas in `tests/contract/`, `tests/integration/`, `tests/unit/`
- [ ] T043 [P] Update changelog/release notes for config/profile/hardware policy changes in `README.md`
- [ ] T044 Validate quickstart flow end-to-end against implementation, including timed first-attempt workflow evidence for SC-005, in `specs/004-pi-cli-service-profile/quickstart.md`
- [ ] T045 Verify no stale merge-config or hardware-precedence guidance remains in docs/spec artifacts in `specs/004-pi-cli-service-profile/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3-6 (User Stories)**: Depend on Phase 2; run in priority order or parallel by staffing.
- **Phase 7 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories.
- **US2 (P1)**: Starts after Foundational; can run in parallel with US1.
- **US3 (P2)**: Starts after Foundational; depends on US1 status payload fields for full value.
- **US4 (P3)**: Starts after Foundational; depends on implemented warning behavior from US1/US3.

### Within Each User Story

- Test tasks first, confirm failing behavior where applicable.
- Core runtime logic before CLI/GUI presentation layers.
- Documentation updates after implementation behavior is stable.

### Parallel Opportunities

- T003 and T004 can run in parallel during Setup.
- T007 and T008 can run in parallel during Foundational.
- US1 and US2 can be implemented in parallel after Foundational.
- Most test tasks marked `[P]` can be executed in parallel.

---

## Parallel Example: User Story 2

```bash
# Parallel tests
Task: "Add CLI active-profile validation contract tests in tests/contract/test_cli.py"
Task: "Add profile save overwrite semantics integration tests in tests/integration/test_profile_portability.py"
Task: "Add built-in override denial unit tests in tests/unit/test_registry.py"

# Parallel implementation where file boundaries allow
Task: "Implement deterministic last-save-wins for user profile saves in src/voicechanger/registry.py"
Task: "Align GUI profile save/update flow with last-save-wins and built-in protection in src/voicechanger/gui/logic.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2.
2. Complete US1 (Phase 3).
3. Validate CLI-boot startup reliability and fallback behavior before expanding scope.

### Incremental Delivery

1. Deliver US1 for startup reliability.
2. Deliver US2 for authoring/deployment loop and save semantics.
3. Deliver US3 for diagnostics visibility.
4. Deliver US4 for canonical guidance and enforcement messaging.
5. Finish with Phase 7 polish and regression.

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. After checkpoint:
   - Engineer A: US1 runtime startup behavior.
   - Engineer B: US2 CLI/GUI save and validation behavior.
   - Engineer C: US3 diagnostics and status surfacing.
3. Converge on US4 docs/enforcement and final polish.

---

## Notes

- All story tasks include `[US#]` labels for traceability.
- Every task includes a concrete file path.
- `[P]` indicates safe parallel execution with minimal file contention.
- Tasks intentionally avoid multi-architecture release scope per feature boundary.
