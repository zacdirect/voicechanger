# Feature Specification: GUI–CLI Feature Parity

**Feature Branch**: `002-gui-cli-parity`
**Created**: 2026-04-12
**Status**: Draft
**Input**: User description: "GUI capability unification between CLI and GUI — full parity feature-wise. Explore Flet-native patterns where they simplify unifying the Pi deployment and dev kit experience. Close gaps between FsocietyVoiceChanger PoC capabilities and the current GUI."

## Clarifications

### Session 2026-04-13

- Q: What is the primary platform target for the GUI vs CLI? → A: Pi is primary for CLI, dev workstation is primary for GUI. CLI and GUI maintain full feature parity.
- Q: How should the expanded GUI features be organized? → A: Tabbed or multi-view layout (e.g., "Control", "Profiles", "Editor", "Tools").
- Q: When a service is already running via CLI, how should the GUI interact with it? → A: Connect to the running service via IPC — GUI becomes a remote control for the existing pipeline.
- Q: How deeply should the implementation lean into Flet-native patterns? → A: Flet-idiomatic UI — adopt Flet navigation, layout, and dialog patterns; keep business logic (audio, profiles, effects) custom.
- Q: Should users be able to edit existing profiles in-place or only create new ones? → A: User profiles are editable in-place (save overwrites). Builtin profiles auto-fork into a named draft (e.g., "high-pitched custom 1") on first modification — no UI lock or blocking dialog, seamless transition.
- Q: How should device selection and monitor/mute work when the GUI is in remote mode (connected to a running service via IPC)? → A: The IPC protocol is extended with `set_device` and `set_monitor` commands so the GUI can control device selection and monitor/mute on the remote service. All control actions work identically in both embedded and remote modes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Service Control from the GUI (Priority: P1)

A performer opens the voice changer GUI on a Raspberry Pi or a dev machine and starts or stops the real-time voice processing pipeline directly from the interface, just as they would with `voicechanger serve` on the command line. The GUI displays clear feedback about whether the service is running, what profile is active, and current audio status.

**Why this priority**: Without the ability to start and stop real-time voice processing, the GUI is only a profile editor — it cannot replace the CLI for the core use case.

**Independent Test**: Can be tested by launching the GUI, pressing Start, verifying that audio is captured and played back through the active profile, pressing Stop, and confirming the pipeline halts.

**Acceptance Scenarios**:

1. **Given** the GUI is open and no processing is active, **When** the user presses "Start", **Then** the audio pipeline begins with the currently selected profile and the UI shows a "Running" status indicator.
2. **Given** the audio pipeline is running, **When** the user presses "Stop", **Then** the pipeline shuts down cleanly and the status indicator shows "Stopped".
3. **Given** the audio pipeline is running, **When** an audio device is disconnected or an error occurs, **Then** the GUI displays a meaningful error message and transitions to a degraded or stopped state.
4. **Given** a service is already running (started via `voicechanger serve`), **When** the GUI is launched, **Then** it detects the running service via IPC, connects to it, and displays the current service state — acting as a remote control rather than starting a second pipeline.

---

### User Story 2 — Audio Device Selection in the GUI (Priority: P1)

A user selects their preferred input microphone and output speaker from drop-down menus in the GUI. The available devices are enumerated from the system, displayed in a human-readable format (card name and sub-device), and the user's selection is applied when the audio pipeline starts or while it is running.

**Why this priority**: The CLI supports `device list` and the PoC had full device selection. Without this, the GUI forces users to the command line to pick the right hardware — a dealbreaker for the unified experience.

**Independent Test**: Can be tested by launching the GUI, verifying the device dropdowns are populated from real hardware or test stubs, selecting a non-default device, starting the pipeline, and confirming audio routes through the chosen device.

**Acceptance Scenarios**:

1. **Given** the system has multiple input and output audio devices, **When** the user opens the device selection controls, **Then** all detected devices are listed with readable labels (card name and device description).
2. **Given** a device is selected in the GUI, **When** the user starts the pipeline, **Then** audio flows through the selected input and output devices.
3. **Given** the pipeline is running and the user changes the output device, **When** the change is confirmed, **Then** the pipeline switches to the new device without requiring a manual restart.
4. **Given** a previously selected device is no longer available, **When** the GUI refreshes the device list, **Then** it falls back to the system default and shows a notification.

---

### User Story 3 — Profile Management in the GUI (Priority: P2)

A user can list, browse, create, switch, delete, export, and import profiles entirely through the GUI. The GUI provides the same profile operations available via `voicechanger profile list|show|switch|create|delete|export`, presented with visual affordances for browsing and editing.

**Why this priority**: Profile management is the second-most-used workflow. The current GUI only supports save/load from the file system with no awareness of the profile registry (builtin vs. user directories).

**Independent Test**: Can be tested by launching the GUI and exercising each profile operation — listing all profiles, switching active profile, creating a new one, deleting a user profile, and exporting a profile — then verifying state matches `voicechanger profile list` output.

**Acceptance Scenarios**:

1. **Given** there are builtin and user profiles on the system, **When** the user opens the profile browser, **Then** all profiles are displayed grouped by type (builtin / user) with name, description, and effect count.
2. **Given** a user browses profiles, **When** they select a different profile and press "Activate", **Then** the running pipeline switches to the new profile's effect chain within 2 seconds.
3. **Given** the user has designed an effect chain in the editor, **When** they press "Save as Profile" and enter a name, **Then** a new profile is created in the user profiles directory and appears in the profile list.
4. **Given** a user profile is loaded in the editor, **When** the user modifies parameters and presses "Save", **Then** the profile is updated in-place in the user profiles directory.
5. **Given** a builtin profile is loaded in the editor, **When** the user modifies any parameter, **Then** the editor automatically creates a draft with an auto-generated name based on the original (e.g., "high-pitched custom 1") — no blocking dialog or UI lock — and subsequent saves write to this new user profile.
4. **Given** a user profile is selected, **When** the user presses "Delete", **Then** a confirmation is shown and upon confirmation the profile is removed from disk and the list.
5. **Given** a builtin profile is selected, **When** the user attempts to delete it, **Then** the delete action is disabled or rejected with an explanation.
6. **Given** a profile is selected, **When** the user presses "Export", **Then** a file save dialog appears and the profile is written to the chosen location.

---

### User Story 4 — Real-Time Audio Level Monitoring (Priority: P2)

The GUI shows real-time input and output audio level meters so the user can confirm their microphone is active, see signal levels, and verify that the transformed output is being generated. Level meters update smoothly during operation.

**Why this priority**: The FsocietyVoiceChanger PoC had level meters and they proved essential for troubleshooting on-site. Without visual feedback, users cannot distinguish "no audio device" from "effect is too quiet."

**Independent Test**: Can be tested by starting the pipeline with a known audio source, verifying that input meter moves with microphone input, and that output meter reflects the processed signal.

**Acceptance Scenarios**:

1. **Given** the pipeline is running and audio is being captured, **When** the user speaks into the microphone, **Then** the input level meter responds in real time, visually reflecting signal amplitude.
2. **Given** the pipeline is running, **When** the effect chain produces output, **Then** the output level meter displays the processed signal level.
3. **Given** no audio is being captured (silence or muted mic), **When** the user observes the meters, **Then** both meters show minimal or no activity.

---

### User Story 5 — Service Status Dashboard (Priority: P3)

A user can view a status panel in the GUI showing the same information as `voicechanger status`: active profile, pipeline state, uptime, input/output device, sample rate, and buffer size. This gives at-a-glance awareness of the system's health.

**Why this priority**: Operational status is critical on a Pi deployment where the user may not have terminal access. However, it builds on top of P1/P2 capabilities.

**Independent Test**: Can be tested by starting the pipeline and verifying each status field displays the correct current value compared to the `status --json` CLI output.

**Acceptance Scenarios**:

1. **Given** the pipeline is running, **When** the user views the status panel, **Then** the active profile name, pipeline state, uptime, device names, sample rate, and buffer size are all displayed.
2. **Given** the user switches profiles or devices, **When** the switch completes, **Then** the status panel updates to reflect the new state within 1 second.

---

### User Story 6 — Offline File Processing in the GUI (Priority: P3)

A user selects an input audio file, chooses a profile, and processes the file to produce a transformed output file — equivalent to running `voicechanger process input.wav output.wav --profile myprofile`. The GUI shows progress and notifies the user when complete.

**Why this priority**: Offline processing is a secondary workflow useful for previewing profiles or generating demo clips. It rounds out full CLI parity but is not core to the real-time use case.

**Independent Test**: Can be tested by selecting a known WAV file, choosing a profile with a pitch shift effect, processing, and verifying the output file has the expected transformation applied.

**Acceptance Scenarios**:

1. **Given** the user selects an input file and a profile, **When** they press "Process", **Then** the file is processed through the profile's effect chain and the output file is saved to the user-specified location.
2. **Given** processing is in progress, **When** the user observes the GUI, **Then** a progress indicator or status message is displayed.
3. **Given** the input file does not exist or is unreadable, **When** the user attempts to process, **Then** a clear error message is displayed.

---

### User Story 7 — Desktop-First GUI with Cross-Platform Compatibility (Priority: P3)

The GUI is designed primarily for developer workstations where profile authoring, effect tuning, and operational monitoring workflows are most common. The Pi is the primary target for headless CLI operation. The GUI should still function on a Pi if launched, but layout and UX decisions are driven by the desktop experience. CLI and GUI maintain full feature parity so users can accomplish any task from either interface.

**Why this priority**: The dev workstation is where users spend time authoring and refining profiles via the GUI; the Pi is where those profiles run headlessly via the CLI. Cross-platform GUI compatibility is a nice-to-have, not a design driver.

**Independent Test**: Can be tested by launching the GUI on a standard desktop, verifying all features work well, and optionally launching on a Pi to verify basic functionality.

**Acceptance Scenarios**:

1. **Given** the GUI is launched on a developer workstation (1080p or higher), **When** the user navigates the interface, **Then** the layout makes effective use of the available space and all features are easily accessible.
2. **Given** the GUI is launched on a Raspberry Pi with an HDMI display, **When** the user navigates the interface, **Then** core controls remain functional (may require scrolling on very small displays).
3. **Given** a profile created on the dev machine GUI, **When** transferred to the Pi and loaded via CLI, **Then** the profile works identically.

---

### Edge Cases

- What happens when the user starts the pipeline with no audio devices detected? The GUI should display an informative error and prevent the start action.
- What happens when the user rapidly switches profiles while the pipeline is running? The system should queue switches and apply the last-selected profile without crashing.
- What happens when offline file processing is started while real-time processing is active? Both should operate independently (offline processing uses its own pipeline instance).
- What happens when the GUI is launched remotely (e.g., via Flet's web mode)? Basic operations should function, though audio routing is host-local.
- What happens when the GUI is launched while a CLI service is running? The GUI connects to the existing service via IPC and operates as a remote control. All control actions (start/stop, profile switch, device change, monitor/mute toggle) are sent as IPC commands.
- What happens when the user changes the audio device via the GUI in remote mode? The GUI sends a `set_device` IPC command to the running service, which restarts the pipeline with the new device. If the device is invalid or unavailable, the service returns an error and remains on the previous device.
- What happens when the user toggles monitor/mute via the GUI in remote mode? The GUI sends a `set_monitor` IPC command to the running service, which enables or disables audio monitoring. The status panel updates to reflect the new state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The GUI MUST provide controls to start and stop the real-time audio processing pipeline.
- **FR-002**: The GUI MUST enumerate and display all detected audio input and output devices in a selectable list.
- **FR-003**: The GUI MUST allow the user to select input and output audio devices before or during pipeline operation.
- **FR-004**: The GUI MUST display a list of all available profiles (builtin and user), grouped by type, with name, description, and effect summary.
- **FR-005**: The GUI MUST allow the user to switch the active profile on a running pipeline.
- **FR-006**: The GUI MUST allow the user to create a new profile from the current effect chain configuration and save it to the user profiles directory. User profiles MUST be editable in-place (save overwrites the existing file).
- **FR-007**: The GUI MUST allow the user to delete user-created profiles with a confirmation step, and MUST prevent deletion of builtin profiles.
- **FR-008**: The GUI MUST allow the user to export a profile to an arbitrary file system location.
- **FR-009**: The GUI MUST allow the user to import a profile from a file into the user profiles directory.
- **FR-010**: The GUI MUST display real-time input and output audio level meters when the pipeline is running.
- **FR-011**: The GUI MUST display a status panel showing: active profile, pipeline state, uptime, input/output device, sample rate, and buffer size.
- **FR-012**: The GUI MUST provide offline file processing: select an input audio file, choose a profile, and produce a processed output file.
- **FR-013**: The GUI MUST provide a monitor/mute toggle to enable or disable speaker output during real-time processing.
- **FR-014**: The GUI MUST be designed for developer workstation displays (1080p+) and SHOULD remain functional on Raspberry Pi HDMI displays when launched there.
- **FR-015**: The GUI MUST retain all existing profile authoring capabilities: add/remove effects in a chain, adjust parameters via sliders with real-time values, and preview audio live.
- **FR-016**: Every operation available through the CLI MUST have a corresponding operation available through the GUI.
- **FR-017**: The GUI MUST use a tabbed or multi-view navigation model to organize features into distinct views (e.g., service control, profile browsing, effect editing, tools/processing), each accessible via a persistent navigation element.
- **FR-018**: When a service is already running (started via CLI), the GUI MUST detect it via the existing IPC socket and connect as a remote control. The GUI MUST NOT start a second audio pipeline when a service is already active.
- **FR-019**: The GUI MUST use Flet-idiomatic patterns for navigation, layout, and dialogs (e.g., NavigationRail, adaptive containers, built-in file pickers and confirmation dialogs). Audio pipeline, profile management, and effect processing logic MUST remain in the existing custom modules, not coupled to the GUI framework.
- **FR-020**: When a builtin profile is loaded in the editor and the user makes any modification, the GUI MUST automatically create a new user profile draft with an auto-generated name derived from the original (e.g., "high-pitched custom 1"), incrementing the suffix to avoid collisions. This transition MUST be seamless — no blocking dialog or UI lock.

### Key Entities

- **Audio Device**: A system input (microphone) or output (speaker) identified by card name, sub-device name, and hardware address. Users select devices to control audio routing.
- **Profile**: A named, portable configuration containing an ordered chain of audio effects with their parameters. Profiles are either builtin (read-only, shipped with the application) or user-created (read-write).
- **Pipeline**: The running audio processing engine that captures input, applies a profile's effect chain, and produces output. Has states: Stopped, Running, Degraded.
- **Effect**: A single audio transformation (pitch shift, gain, reverb, chorus, etc.) with typed, bounded parameters. Effects are composed into ordered chains within profiles.
- **Status**: An operational snapshot of the running system — active profile, pipeline state, uptime, device configuration, audio parameters.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every CLI command (`serve`, `profile list|show|switch|create|delete|export`, `device list`, `status`, `process`) has a corresponding, functional GUI interaction that achieves the same result.
- **SC-002**: A user can perform full end-to-end setup — select devices, choose a profile, start real-time processing, monitor levels, switch profiles, and stop — entirely within the GUI, without touching the command line.
- **SC-003**: The GUI is fully functional on developer workstation displays (1080p+). On a Raspberry Pi with an HDMI display, core features remain accessible.
- **SC-004**: Input and output level meters update at least 15 times per second during active processing, providing responsive visual feedback.
- **SC-005**: Profile operations (list, switch, create, delete, export, import) in the GUI complete within 2 seconds for a profile library of up to 50 profiles.
- **SC-006**: Switching between profiles on a running pipeline completes without audible gaps or glitches lasting longer than 100 milliseconds.
- **SC-007**: Offline file processing of a 60-second audio file completes within 30 seconds on a Raspberry Pi 3.
- **SC-008**: The same GUI application binary/package works on both the Raspberry Pi deployment target and developer workstations without platform-specific builds.

## Assumptions

- The Raspberry Pi is the primary deployment target for CLI/headless operation. The developer workstation is the primary deployment target for GUI operation. Both interfaces offer full feature parity.
- Flet is already adopted as the GUI framework (current codebase uses Flet with Material Design 3). The GUI layer adopts Flet-idiomatic patterns for navigation, layout, and standard dialogs, while all business logic (audio pipeline, profile registry, effects, device enumeration) remains in the existing custom Python modules, decoupled from the framework.
- The existing audio pipeline (`AudioPipeline`), profile registry (`ProfileRegistry`), device monitor (`DeviceMonitor`), and effects system remain as the underlying engine. This feature extends the GUI to expose their full capabilities, not to rewrite them.
- The Raspberry Pi deployment uses ALSA-based audio with PipeWire/PulseAudio. Device enumeration via `aplay`/`arecord` is the established mechanism.
- The GUI replaces the previous Tkinter-based PoC interface entirely. There is one GUI codebase going forward.
- Profile format and file structure (JSON in `profiles/builtin` and `profiles/user`) remain unchanged. Existing profiles are compatible.
- The IPC mechanism (Unix domain socket) between CLI and service is the primary integration point. When a service is already running, the GUI connects via IPC as a remote control. When no service is running, the GUI starts an embedded pipeline directly.
- Web-mode operation via Flet is a future consideration, not a requirement of this feature. Audio routing constraints (host-local) make remote web GUI a separate concern.
- The Pi 3 HDMI port supports resolutions up to 1920×1200. The previous 800×480 assumption was based on the official Pi touchscreen, not HDMI output. The GUI targets desktop resolution and does not constrain itself to small-touchscreen dimensions.
