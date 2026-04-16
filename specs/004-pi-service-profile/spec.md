# Feature Specification: Pi CLI Service Profile

**Feature Branch**: `004-pi-service-profile`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "Single deb install sets up the voicechanger daemon on Raspberry Pi. The daemon is a system service that boots with the device, resumes its last-known operational state, and exposes an IPC control plane. Users run CLI or GUI in their own context, save preferences to their local folder (~/.voicechanger/), and push desired state into the daemon. The daemon persists its operational state to a system directory. At login, a user-level CLI command applies the user's saved profile to the running daemon."

## Clarifications

### Session 2026-04-15

- Q: What is the daemon/CLI ownership boundary? -> A: The daemon is a system service that owns built-in profiles and persists its own operational state to a system directory (e.g., `/var/lib/voicechanger/`). It never reads user home directories. The CLI/GUI runs as the logged-in user, reads `~/.voicechanger/`, and pushes desired state into the daemon via IPC.
- Q: What should the daemon do at boot? -> A: Resume from its last persisted operational state. On a fresh install (no state file yet), start with `clean` — this is just the default, not an error.
- Q: How does a user's profile reach the daemon? -> A: The CLI reads the user's local profile and pushes the full profile definition (effects chain, settings) into the daemon via IPC. The daemon validates and applies it, then persists the new state.
- Q: How should profile name collisions between user and built-in profiles be handled? -> A: Built-in characters are system-authoritative. The daemon rejects IPC requests to override a built-in profile name. Users can create profiles with different names using last-save-wins semantics locally.
- Q: What reconciliation happens when CLI/GUI connects? -> A: The CLI reads daemon state ("running darth-vader with these settings") and compares it to the user's local profiles. It can surface differences: profile not saved locally, local version differs from running version, user config says a different profile should be active.
- Q: What is the security and profile-write model for this device? -> A: Treat as single-user embedded system; security controls are out of scope. IPC socket permissions handle access control. Profile saves use last-save-wins behavior.
- Q: How should built-in hardware hints behave compared to built-in sound profiles? -> A: Built-in sound profiles are system-authoritative; built-in hardware hints are best guesses and user hardware config overrides them.
- Q: Should users need to manually manage files under `~/.voicechanger/`? -> A: No. The CLI/GUI is the primary interface for all user workflows — first run, profile creation, configuration. The CLI bootstraps `~/.voicechanger/` on first use. Manually placed files should be tolerated and discovered, but the designed workflow is always through CLI/GUI commands.
- Q: What should `apply` do when the daemon is already running a different profile? -> A: `apply` always pushes the user's preferred state to the daemon without prompting. It is designed for non-interactive use (e.g., shell profile at login). Reconciliation and interactive decisions are the job of `status`, not `apply`.
- Q: What schema should daemon operational state use? -> A: Extend the existing profile schema (schema_version, name, effects, author, description) with origin metadata (pushing user, timestamp) and device config. Use the same schema_version convention and forward-compatible loading pattern established in `profile.py` and `hardware.py`.
- Q: What should the daemon log during steady-state operation? -> A: State changes only — profile switches, device changes, IPC connections, plus startup/shutdown and errors. No continuous/periodic logging. Appropriate for embedded Pi with limited SD card storage.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable CLI-Boot Startup with Last-Known State (Priority: P1)

A Raspberry Pi operator configures their device to boot to CLI mode (no desktop) and still wants voice changing to start reliably. The daemon starts as a system service, resumes its last-known operational state, and is ready for audio processing without user login.

**Why this priority**: Boot-to-CLI operation is the deployment baseline for Raspberry Pi use. The daemon must start reliably and resume operation regardless of whether any user has logged in.

**Independent Test**: Can be fully tested by pushing a profile via CLI, rebooting, and verifying the daemon resumes with the same profile and device config without user intervention.

**Acceptance Scenarios**:

1. **Given** the Pi is configured to boot to CLI and the daemon is enabled as a system service, **When** the Pi boots, **Then** the daemon starts and resumes from its persisted operational state in `/var/lib/voicechanger/`.
2. **Given** the daemon's persisted state includes an active profile with a full effects chain, **When** the daemon starts, **Then** that profile is loaded without requiring user login or CLI interaction.

---

### User Story 2 - Profile Authoring and Deployment via CLI/GUI (Priority: P1)

A profile author creates a character voice using the CLI (`voicechanger profile create`) or the GUI, iterates on it, and pushes it to the running daemon. The CLI/GUI handles all file management — the user never needs to manually copy files or know about directory paths. Power users who do place files manually should be tolerated, but that is not the designed workflow.

**Why this priority**: This is the primary content creation and deployment journey. If it is inconsistent, users cannot confidently iterate on custom voices.

**Independent Test**: Can be fully tested by creating a new profile via CLI, pushing it to the daemon, and confirming the daemon applies the effects chain and persists the state.

**Acceptance Scenarios**:

1. **Given** a user creates a profile via `voicechanger profile create <name>`, **When** the profile is created, **Then** the CLI saves it to the user's local profile directory and it is available for pushing to the daemon.
2. **Given** the user pushes a profile to the daemon via `voicechanger profile switch <name>`, **When** the daemon accepts it, **Then** the daemon persists the full profile definition (effects, settings, origin metadata) to its system state file.
3. **Given** the user pushes a profile name that matches a built-in, **When** the daemon receives the request, **Then** the daemon rejects the override and returns an error explaining that built-in profiles are system-authoritative.
4. **Given** a power user has manually placed a valid profile JSON in `~/.voicechanger/profiles/`, **When** the CLI lists or switches profiles, **Then** the manually placed profile is discovered and usable like any other user profile.

---

### User Story 3 - Daemon Status and Diagnostics Visibility (Priority: P2)

An operator needs to understand what the daemon is currently doing: which profile is active, what effects are running, which devices are configured, and where the state came from (which user last pushed config).

**Why this priority**: Without clear runtime status, operators cannot tell whether the daemon is running their intended profile or troubleshoot why audio sounds wrong.

**Independent Test**: Can be tested by pushing a profile via CLI and then querying daemon status to confirm all operational details are visible and accurate.

**Acceptance Scenarios**:

1. **Given** the daemon is running, **When** an operator queries service status, **Then** the active profile name, effects chain, device config, and last-push metadata are visible.
2. **Given** built-in and user-pushed profiles are both available, **When** profiles are enumerated, **Then** the source of each profile (built-in vs user-pushed) is clearly identified.

---

### User Story 4 - CLI/Daemon State Reconciliation at Login (Priority: P2)

A user logs into the Pi and runs the CLI or GUI. The CLI connects to the running daemon, reads its current state, and compares it to the user's local preferences. It surfaces actionable differences so the user can decide what to do.

**Why this priority**: The daemon may be running a profile pushed by a different session or resumed from a previous boot. Users need to understand what's running and reconcile it with their local preferences.

**Independent Test**: Can be tested by pushing a profile, modifying local config to reference a different profile, then running the CLI and confirming it surfaces the discrepancy.

**Acceptance Scenarios**:

1. **Given** the daemon is running profile `darth-vader` and the user's local config says `bane` should be active, **When** the user runs `voicechanger status`, **Then** the CLI reports the mismatch. If the user runs `voicechanger apply`, the CLI pushes `bane` to the daemon without prompting.
2. **Given** the daemon is running a profile the user does not have saved locally, **When** the CLI connects, **Then** it offers to save a copy of the running profile to the user's local profile directory.
3. **Given** the daemon is running a profile that matches the user's local version, **When** the CLI connects, **Then** no reconciliation action is needed and status displays cleanly.

### Edge Cases

- What happens when multiple users push different profiles in sequence? (Last push wins — daemon doesn't track sessions, just applies and persists.)
- What happens when shipped hardware hints conflict with user hardware selections pushed via IPC? (User overrides win; shipped hints are advisory.)
- What happens when the IPC socket is unavailable (daemon not running) and the user tries to push a profile? (CLI reports daemon unreachable and suggests checking service status.)

## Requirements *(mandatory)*

### Functional Requirements

#### Daemon (system service)

- **FR-001**: Daemon MUST start as a system service on Raspberry Pi CLI-boot without requiring a graphical desktop session or user login.
- **FR-002**: Daemon MUST persist its operational state (active profile definition, effects chain, device config, origin metadata) to a system-owned directory (e.g., `/var/lib/voicechanger/state.json`).
- **FR-003**: Daemon MUST resume from persisted operational state at boot. On fresh install (no state file), daemon starts with `clean` as the default.
- **FR-004**: Daemon MUST accept IPC commands to switch profiles, set devices, and update runtime configuration. When a change is accepted, the daemon MUST persist the new state.
- **FR-005**: Daemon MUST reject IPC requests that attempt to override built-in profile names and return a clear error explaining that built-in profiles are system-authoritative.
- **FR-006**: Daemon MUST expose its current operational state via IPC status queries: active profile name, effects chain, device config, last-push user metadata, and any startup warnings.
- **FR-007**: Daemon MUST distinguish built-in profiles from user-pushed profiles in listing and status output.
- **FR-008**: Daemon MUST NOT read user home directories or user-owned config files. All user preferences reach the daemon exclusively through IPC.
- **FR-009**: Shipped hardware hints are advisory build-time defaults only; user hardware configuration pushed via IPC MUST override shipped hardware hints.
- **FR-010**: Daemon MUST log state changes (profile switches, device changes, IPC connections) plus startup, shutdown, and errors. Daemon MUST NOT produce continuous or periodic log output during steady-state operation.

#### CLI/GUI (user context)

- **FR-011**: CLI/GUI MUST bootstrap `~/.voicechanger/` (config, profiles, hardware directories) on first use if it does not exist. Users should never need to manually create directories or copy files.
- **FR-012**: CLI/GUI MUST read user preferences from `~/.voicechanger/voicechanger.toml` and user profiles from `~/.voicechanger/profiles/`. Manually placed files in these directories MUST be discovered and usable.
- **FR-013**: CLI/GUI MUST validate that a target profile exists locally before pushing it to the daemon.
- **FR-014**: CLI/GUI MUST support a complete profile authoring flow through commands and GUI — create, edit, list, delete, push to daemon. Users MUST NOT be required to manually manage profile files to accomplish any standard workflow.
- **FR-015**: Profile save operations in CLI/GUI MUST allow overwrite semantics for existing user profiles with deterministic last-save-wins behavior.
- **FR-016**: CLI/GUI MUST perform state reconciliation on connect: compare daemon state to local preferences and surface actionable differences (profile not saved locally, local version differs, config says different profile should be active).
- **FR-017**: CLI/GUI MUST support an `apply` command (or equivalent) that reads the user's saved preferences and pushes them to the daemon without prompting, suitable for non-interactive use at login (e.g., from a shell profile). `apply` always overwrites the daemon's current state with the user's config.

#### Cross-cutting

- **FR-018**: System MUST remain scoped to service/profile/config behavior and MUST NOT require multi-architecture release automation changes as part of this feature.
- **FR-019**: Built-in characters are system-authoritative; the daemon owns them and neither CLI nor GUI can override them.
- **FR-020**: IPC socket permissions MUST control access to the daemon. No additional ownership validation is required.

### Key Entities *(include if feature involves data)*

- **Daemon Operational State**: The persisted state file (`/var/lib/voicechanger/state.json`) containing the active profile (using the existing profile schema: name, effects, author, description, schema_version), device configuration, and origin metadata (pushing user, timestamp). Uses the same schema_version convention and forward-compatible loading pattern established in `profile.py` and `hardware.py`. This is the daemon's source of truth at boot.
- **User Config**: The user's TOML configuration (`~/.voicechanger/voicechanger.toml`) read by CLI/GUI. Defines the user's preferred active profile, device selections, and other preferences. Never read by the daemon.
- **User Profile**: A user-authored voice profile stored in `~/.voicechanger/profiles/`, read by CLI/GUI and pushed to the daemon via IPC.
- **Built-in Profile**: A shipped profile owned by the daemon, available by default, and system-authoritative (cannot be overridden).
- **Built-in Hardware Hint**: A shipped best-guess device/channel configuration used only until user hardware configuration pushed via IPC provides a more specific runtime choice.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The daemon resumes the last-pushed profile in 100% of reboot tests without user login or manual intervention.
- **SC-002**: Operators can identify the active profile, effects chain, and device config within 30 seconds using the standard status command.
- **SC-003**: A new user starting from a fresh install can create a profile and push it to the daemon entirely through CLI/GUI in under 5 minutes on first attempt, with no manual file management.
- **SC-004**: CLI reconciliation identifies and surfaces all defined mismatch scenarios (profile not saved locally, local version differs from running, local config disagrees with running state) in 100% of test cases.

## Assumptions

- Device is a single-user embedded costume system; hostile multi-user security scenarios are out of scope.
- Target deployments use Raspberry Pi systems configured for CLI boot where service reliability does not depend on desktop login.
- The daemon runs as a dedicated system user (e.g., `voicechanger`) with access to its own state directory and built-in profiles. It does not access user home directories.
- Profile authoring may occur off-device (dev machine) or on-device (GUI/web), but deployment to the daemon always goes through CLI/GUI pushing via IPC.
- The CLI/GUI is the primary interface for all user workflows. Users should never need to manually create, copy, or edit files to use the voicechanger. Power users who do manage files directly are tolerated but not the target workflow.
- Built-in profiles remain available as fallback content. The daemon's persisted state is the authoritative record of what should be running.
- This feature focuses on the daemon/CLI boundary, state persistence, and profile push flow; packaging and multi-architecture release automation are explicitly out of scope.
