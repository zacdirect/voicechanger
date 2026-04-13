# Feature Specification: Realtime Voice Changer

**Feature Branch**: `001-realtime-voice-changer`
**Created**: 2026-04-12
**Status**: Draft
**Input**: User description: "Python-based real-time voice changer for Raspberry Pi, built on Spotify's Pedalboard library, with modular community-distributable character profiles, CLI-first headless operation, and a reference UI for profile authoring."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live Voice Transformation (Priority: P1)

A performer wearing a costume powers on the Raspberry Pi. The device boots, automatically starts the voice changer service, and begins transforming microphone input through the active character profile to the speaker output in real time. The performer speaks naturally and hears the transformed voice with no perceptible delay.

**Why this priority**: This is the core value proposition — without reliable, low-latency live voice transformation, nothing else matters.

**Independent Test**: Can be fully tested by starting the service with a known profile, speaking into the mic, and verifying that transformed audio is produced at the speaker within the latency budget.

**Acceptance Scenarios**:

1. **Given** the Pi has booted with a valid configuration and a character profile selected, **When** the service starts automatically, **Then** microphone audio is captured, transformed through the active profile's effect chain, and played through the speaker with end-to-end latency under 50 ms.
2. **Given** the service is running, **When** the performer speaks continuously for 30 minutes, **Then** audio processing remains stable with no dropouts, glitches, or crashes.
3. **Given** the active profile cannot be loaded (corrupted file, missing dependency), **When** the service starts, **Then** it falls back to pass-through audio (clean, unprocessed voice) and logs a warning.

---

### User Story 2 - Character Profile Management via CLI (Priority: P2)

A user (performer or sound designer) uses CLI commands to list available character profiles, inspect their settings, switch the active profile, create new profiles, and delete custom profiles. Profiles are self-contained files that can be copied between installations.

**Why this priority**: Profile management is the primary user interaction model for a headless device. Without it, the performer is locked to a single voice effect.

**Independent Test**: Can be tested entirely from the command line without audio hardware — create a profile, list profiles, switch active profile, verify config state.

**Acceptance Scenarios**:

1. **Given** the system has built-in profiles ("high-pitched", "low-pitched", "clean") and one user-created profile, **When** the user runs the list command, **Then** all profiles are displayed with their names and a summary of effect settings.
2. **Given** a valid profile name, **When** the user runs the switch command, **Then** the active profile changes and the running audio pipeline picks up the new effect chain within 2 seconds.
3. **Given** a set of effect parameters (pitch shift amount, gain, reverb level, etc.), **When** the user runs the create command with a profile name, **Then** a new profile file is written to the profiles directory and is immediately available for use.
4. **Given** a built-in profile name, **When** the user attempts to delete it, **Then** the system refuses and displays an error explaining that built-in profiles are read-only.

---

### User Story 3 - Profile Authoring with Dialled-In Settings (Priority: P3)

A sound designer uses a desktop GUI application on a development machine to adjust effect parameters in real time — pitch shift, gain, reverb, chorus, etc. — while hearing the result through live audio on the dev machine's audio hardware. Once satisfied, they save the combination as a named character profile file that can be copied to a Raspberry Pi or distributed to the community.

**Why this priority**: Enabling users to craft and fine-tune custom voices is what drives community contribution and long-term project value. However, it builds on top of P1 and P2.

**Independent Test**: Can be tested by launching the authoring interface, adjusting multiple parameters, saving a profile, and then loading that profile in pure CLI mode to confirm settings persisted correctly.

**Acceptance Scenarios**:

1. **Given** the authoring interface is running with live audio, **When** the user adjusts the pitch shift slider, **Then** the change is heard in the speaker output within 1 second.
2. **Given** the user has dialled in a set of effect parameters, **When** they save the profile with a name (e.g., "darth-vader"), **Then** a profile file is created containing all effect settings in a portable format.
3. **Given** a saved profile file, **When** another user copies it into their profiles directory, **Then** the profile appears in their profile list and produces the same audio transformation when activated.

---

### User Story 4 - Community Profile Distribution (Priority: P4)

A community member creates an excellent character voice (e.g., "darth-vader") and wants to share it. They package the profile as a single file. Other users install the profile by placing it in their profiles directory (or using a CLI install command). The project repository hosts a curated gallery of community-contributed profiles.

**Why this priority**: Community contributions multiply the project's value but depend on the profile format being stable and the authoring workflow being mature.

**Independent Test**: Can be tested by exporting a profile from one installation, importing it on a fresh installation, and verifying the audio output matches.

**Acceptance Scenarios**:

1. **Given** a community-contributed profile file, **When** a user places it in the profiles directory, **Then** the profile appears in the profile list and works without additional configuration.
2. **Given** a profile was created on a development machine (x86_64), **When** it is deployed to a Raspberry Pi (aarch64), **Then** the profile produces the same audio transformation.
3. **Given** a profile references an effect or parameter not supported by the user's installed version, **When** the profile is loaded, **Then** the system logs a warning identifying the unrecognized effect, skips it, and applies the remaining supported effects in the chain.

---

### User Story 5 - Offline File Processing (Priority: P5)

A user wants to preview what a character profile sounds like by processing a pre-recorded audio file through the same effect chain, producing an output file. This is useful for testing profiles without hardware and for creating demo samples.

**Why this priority**: Useful for CI testing, demonstrations, and profile previews, but not essential for the core live use case.

**Independent Test**: Can be tested by processing a known WAV file through a profile and comparing the output to expected characteristics (pitch shifted by the correct amount, effects applied).

**Acceptance Scenarios**:

1. **Given** an input audio file and a profile name, **When** the user runs the process-file command, **Then** an output audio file is produced with the profile's effects applied.
2. **Given** a mono or stereo input file, **When** processed through any valid profile, **Then** the output file has the same duration (within 1 second) and channel count as the input.

---

### Edge Cases

- What happens when the configured audio device is not present at boot (e.g., USB adapter unplugged)? → Resolved: system starts with available hardware and polls for preferred device.
- How does the system handle audio device hot-plug/unplug while running? → Resolved: background polling detects preferred device availability and switches automatically.
- What happens when two profiles share the same name (one built-in, one user-created)? → Resolved: built-in names are reserved; user creation with a built-in name is rejected.
- How does the system behave when disk is full and a profile save is attempted?
- What happens when an effect parameter in a profile is outside the valid range?
- How does the system handle corrupt or zero-byte profile files?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST capture audio from a configurable input device, apply an ordered chain of audio effects defined by the active character profile, and output the result to a configurable output device in real time.
- **FR-002**: System MUST start automatically on boot as a standalone Python process managed by systemd and begin voice transformation without user interaction.
- **FR-003**: System MUST fall back to pass-through audio (unprocessed mic-to-speaker) if the active profile fails to load.
- **FR-004**: System MUST support the following effect types at minimum: pitch shift, gain. Additional effects (reverb, chorus, distortion, EQ) are expected to be supported as the Pedalboard library provides them.
- **FR-005**: System MUST allow hot-switching character profiles at runtime via CLI (communicating with the running service over a Unix domain socket) without stopping the audio stream.
- **FR-006**: System MUST provide a CLI for profile management: list, show, create, edit, delete, switch, and export operations.
- **FR-007**: Character profiles MUST be stored as self-contained files (one file per profile) in a designated profiles directory.
- **FR-008**: Profile files MUST be portable across architectures — a profile created on x86_64 MUST work on aarch64 without modification.
- **FR-009**: System MUST ship with at least three built-in profiles: a clean pass-through, a high-pitched voice, and a low-pitched voice. Built-in profiles MUST NOT be deletable or overwritable by users. Built-in profile names are reserved — the system MUST reject creation of user profiles with the same name as a built-in.
- **FR-010**: System MUST provide a desktop GUI application for interactive profile authoring, intended to run on a development machine (not on the Pi). The GUI MUST allow real-time adjustment of effect parameters with live audio feedback and saving the result as a portable profile file.
- **FR-011**: System MUST support offline processing of audio files through a specified profile's effect chain.
- **FR-012**: System MUST log operational status, errors, and profile changes to structured log output for headless diagnostics.
- **FR-013**: System MUST expose audio device enumeration so users can identify and configure input/output devices.
- **FR-016**: System MUST support configurable audio device selection with a default behavior of: start immediately with whatever audio hardware is available, poll in the background for the user's preferred (configured) device, and switch to it automatically when detected. An optional strict mode MUST be supported where the system waits for the specific configured device.
- **FR-014**: The audio effect pipeline MUST be built on Spotify's Pedalboard library and its associated audio I/O facilities.
- **FR-015**: C/C++ patches to the Pedalboard library (e.g., low-latency pitch shifting) MUST be maintained as documented patches or submodules, with clear rationale for why the upstream library's built-in capabilities are insufficient.

### Key Entities

- **Character Profile**: A named, portable configuration file defining an ordered list of audio effects and their parameters. Includes metadata (name, author, description, schema_version) and the effect chain definition. The baseline is "clean" (no effects); every profile is additive, layering effects on top of silence/pass-through.
- **Effect Chain**: An ordered sequence of audio effect instances (pitch shift, gain, reverb, etc.) with their parameter values. Processed in series from first to last.
- **Audio Pipeline**: The runtime component that captures audio from the input device, passes it through the active effect chain, and sends it to the output device. Manages device lifecycle and buffer handling.
- **Profile Registry**: The mechanism that discovers, validates, and serves profiles from the profiles directory. Distinguishes built-in from user-created profiles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Voice transformation is audible to the performer within 50 ms of speaking (end-to-end latency).
- **SC-002**: System operates continuously for 8 hours without audio dropouts, crashes, or memory growth beyond 50 MB of the initial footprint.
- **SC-003**: Switching character profiles completes within 2 seconds with no audio silence gap exceeding 500 ms.
- **SC-004**: A new user can install the system, select a built-in profile, and hear live transformed audio within 10 minutes of first boot.
- **SC-005**: A community-contributed profile file can be installed by copying a single file, with no additional steps required.
- **SC-006**: Offline file processing of a 60-second audio file completes within 30 seconds on the target hardware.
- **SC-007**: The system recovers automatically from a crash and resumes voice transformation within 30 seconds.

## Clarifications

### Session 2026-04-12

- Q: How does the CLI communicate with the running audio service for hot-switching profiles? → A: Unix domain socket for bidirectional IPC; the service runs as a standalone Python process managed by systemd (not a complex daemon framework).
- Q: How should the system handle profile format evolution when new effect types are added? → A: Schema version field in each profile; unrecognized effects are skipped with a warning (additive model — baseline is clean/no effects). Older installations gracefully degrade to the subset of effects they support.
- Q: What should happen when the configured audio device is not present at boot? → A: Configurable. Default: use whatever hardware is available immediately and poll indefinitely in the background to switch to the preferred (configured) device when it appears. Users can override in config (e.g., strict mode requiring a specific device).
- Q: What happens when a user-created profile has the same name as a built-in profile? → A: Built-in always wins — the system rejects creation of a user profile with a built-in name.
- Q: What form does the interactive authoring interface take, and where does it run? → A: Desktop GUI application (consistent with the reference project) running on a dev machine only. The Pi is pure headless with no authoring UI. Profiles and config are transferred to the Pi via file copy (SSH/SCP, USB, or SD card sneakernet).

## Assumptions

- The Raspberry Pi will have a USB audio adapter or HAT DAC providing ALSA-compatible mic input and speaker output. On-board 3.5 mm audio jack is not assumed to be sufficient quality.
- PipeWire or PulseAudio is available on the target Raspberry Pi OS to provide an audio server layer above ALSA.
- Spotify's Pedalboard library (v0.9.14+, which added Linux AudioStream support) is the primary audio processing dependency. A C++ patch for low-latency pitch shifting (bypassing PrimeWithSilence) is expected to be necessary based on reference project findings, but the upstream `AudioStream` API may offer alternative approaches that should be evaluated during planning.
- The interactive authoring UI is a desktop GUI application (e.g., tkinter) that runs on a development machine only. The Pi has no authoring interface — profiles and configuration are transferred via file copy (SSH/SCP, USB drive, or SD card reader). No web server or TUI is required on the Pi.
- Profile files use a human-readable, version-controllable format (JSON or TOML). Binary formats are not acceptable for community distribution.
- The project will vendor Pedalboard as a git submodule if C++ patches are required, building a custom wheel as part of CI.
- "Community distribution" in the initial scope means sharing profile files manually (copy/download). A package registry or marketplace is out of scope.
