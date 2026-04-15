# Feature Specification: Pi CLI Service Profile Ownership

**Feature Branch**: `004-pi-cli-service-profile`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "UX review for users who set Raspberry Pi to boot to CLI while still easily starting service. Service should read TOML config from user directory. Profile authoring flow: design character on dev machine or on Pi via web/GUI, save profile to user folder, update config, reboot Pi, service picks up profile. Review and capture gaps in service handling of TOML directory resolution and per-user saved profiles. Canonical service ownership model: user-owned config/profile paths with service running in that same user context."

## Clarifications

### Session 2026-04-15

- Q: Which service ownership model should be canonical for production? -> A: User-owned config/profile paths with service running in that same user context.
- Q: What should startup do when the configured active profile is missing or invalid? -> A: Log warning and fallback to `clean`; CLI must validate profile existence before writing config.
- Q: How should profile name collisions between user and built-in profiles be handled? -> A: Last-save-wins for user profile saves, except built-in characters remain system-authoritative and cannot be overridden from local `built-in` folders.
- Q: How should runtime handle both user-level and system-level config files when both exist? -> A: Use user-mode config only for runtime behavior; do not merge system config by default.
- Q: How should startup behave if user directories cannot be read? -> A: Fall back to shipped system defaults, prefer audible clean/pass-through behavior plus known-good hardware polling, and emit a clear warning with corrective guidance such as checking for SD-card corruption.
- Q: What is the security and profile-write model for this device? -> A: Treat as single-user embedded system; security controls are out of scope and profile saves use last-save-wins behavior.
- Q: How should built-in hardware hints behave compared to built-in sound profiles? -> A: Built-in sound profiles are system-authoritative; built-in hardware hints are best guesses and user hardware config overrides them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable CLI-Boot Startup for User-Owned Service (Priority: P1)

A Raspberry Pi operator configures their device to boot to CLI mode (no desktop) and still wants voice changing to start reliably without manually fixing paths or permissions. They run and manage the service under their own user account so the service reads the same config and profiles they manage.

**Why this priority**: Boot-to-CLI operation is the deployment baseline for Raspberry Pi use. If startup and ownership context are inconsistent, profile loading and day-to-day operation break.

**Independent Test**: Can be fully tested by configuring a non-root user with user-owned config and profiles, rebooting in CLI mode, and verifying service startup, active profile loading, and steady audio operation.

**Acceptance Scenarios**:

1. **Given** the Pi is configured to boot to CLI and the service is enabled for a specific user, **When** the Pi boots, **Then** the service starts in that user context and reads that user's config/profile paths.
2. **Given** the service starts in CLI mode, **When** the configured active profile exists in the user's profile directory, **Then** that profile is loaded without requiring manual intervention.
3. **Given** the service startup context does not match config/profile ownership, **When** startup occurs, **Then** the system reports a clear, actionable error explaining the ownership/path mismatch.

---

### User Story 2 - Profile Authoring and Deployment Loop Across Devices (Priority: P1)

A profile author designs a character voice on a development machine or on the Pi through GUI/web tooling, saves it into the target Pi user's profile folder, updates the active profile in user config, reboots, and expects the service to use the new profile automatically.

**Why this priority**: This is the primary content creation and deployment journey. If it is inconsistent, users cannot confidently iterate on custom voices.

**Independent Test**: Can be fully tested by creating a new profile, placing it in the target user's profile directory, setting it active in user config, rebooting, and confirming the service loads that exact profile.

**Acceptance Scenarios**:

1. **Given** a new profile is authored and saved to the target user's profile directory, **When** the profile list is refreshed, **Then** the new profile appears and is selectable.
2. **Given** the user's config is updated to set the new profile as active, **When** the Pi reboots, **Then** the service loads that active profile on startup.
3. **Given** the active profile reference is invalid after reboot, **When** startup validation runs, **Then** service logs a warning, falls back to `clean`, and continues startup.

---

### User Story 3 - Path Resolution and Gap Visibility for Operators (Priority: P2)

An operator needs to understand exactly which config file and profile directories the service resolved at runtime, especially when troubleshooting why a custom profile is not loaded.

**Why this priority**: Misresolved user paths are a high-frequency failure mode in service environments and can look like profile bugs unless made visible.

**Independent Test**: Can be tested by starting the service under expected and unexpected user contexts and verifying runtime status/log output clearly shows resolved config path, profile roots, and mismatch warnings.

**Acceptance Scenarios**:

1. **Given** the service is running, **When** an operator queries service status, **Then** resolved config and profile paths are visible.
2. **Given** user profile discovery returns zero profiles due to path mismatch, **When** diagnostics are inspected, **Then** the reason is explicit and includes corrective guidance.
3. **Given** built-in and user profiles are both present, **When** profiles are enumerated, **Then** the source of each profile is clearly identified.

---

### User Story 4 - Canonical Ownership Model Documentation and Enforcement (Priority: P3)

A maintainer wants one canonical model: the same user account that owns config/profile files also runs the service, so behavior is predictable and support guidance is consistent.

**Why this priority**: A single ownership model reduces support burden and prevents environment-specific ambiguity.

**Independent Test**: Can be tested by validating service setup instructions and runtime behavior against multiple user-account combinations and confirming only the canonical model is treated as supported default behavior.

**Acceptance Scenarios**:

1. **Given** setup guidance is followed for the canonical model, **When** the service is deployed, **Then** config/profile discovery and profile activation work without extra permissions workarounds.
2. **Given** a non-canonical ownership setup is attempted, **When** validation occurs, **Then** the system warns that the setup is unsupported or degraded and explains the canonical alternative.

### Edge Cases

- What happens when the user-specific TOML config file is missing at service startup?
- What happens when user configuration or profile directories exist but are unreadable?
- What happens when both a system-level config and a user-level config are present with conflicting active profile values?
- What happens when the configured active profile exists in built-in profiles but not in the user profile directory?
- What happens when a user-saved profile collides with a built-in profile name?
- What happens when service starts under root but profile files are owned by a non-root user?
- What happens after reboot if the profile file referenced in config was renamed or deleted?
- What happens when multiple profile saves target the same profile name?
- What happens when shipped hardware hints conflict with user hardware selections or discovered user hardware hints?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support Raspberry Pi CLI-boot operation where the voice changer service starts and runs without requiring a graphical desktop session.
- **FR-002**: System MUST resolve the primary runtime configuration from the service user's TOML configuration path.
- **FR-003**: System MUST resolve user profile storage from directories owned by the same user account that runs the service.
- **FR-004**: System MUST load the active profile defined in the resolved user configuration during startup and after reboot.
- **FR-005**: System MUST support a profile authoring flow in which a profile created on a development machine or on-Pi GUI/web flow can be placed into the target user's profile directory and then activated through user config.
- **FR-006**: System MUST treat per-user saved profiles as first-class runtime assets and include them in profile discovery and activation behavior.
- **FR-007**: System MUST provide clear diagnostics that expose resolved configuration path, resolved profile directories, and active runtime user identity.
- **FR-008**: System MUST detect and report path-resolution mismatches between service runtime user and config/profile ownership.
- **FR-009**: System MUST define and enforce a canonical ownership model: config and profiles are user-owned, and the service runs in that same user context.
- **FR-010**: System MUST provide deterministic startup behavior when the configured active profile cannot be loaded: log a warning, fall back to `clean`, and continue startup.
- **FR-011**: System MUST distinguish built-in profiles from user profiles in listing and diagnostic output.
- **FR-012**: System MUST provide operator guidance for recovering from common ownership/path failures (missing config, missing profile, permission denied, mismatched runtime user).
- **FR-013**: System MUST remain scoped to service/profile/config behavior and MUST NOT require multi-architecture release automation changes as part of this feature.
- **FR-014**: CLI commands that set or switch active profiles MUST validate that the target profile exists before persisting config changes.
- **FR-015**: Profile save operations from CLI/GUI MUST allow overwrite semantics for existing user profiles with deterministic last-save-wins behavior.
- **FR-016**: Built-in characters are system-authoritative; runtime MUST ignore/deny local overrides in user `built-in` folders and emit a diagnostic warning when such overrides are detected.
- **FR-017**: When both user-level and system-level config files are present, runtime MUST use user-level config for effective behavior and MUST NOT merge system config.
- **FR-018**: If user configuration directories are unreadable at startup, runtime MUST continue startup using shipped system defaults and known-good hardware polling rather than failing silent.
- **FR-019**: Shipped hardware hints are advisory build-time defaults only; user hardware configuration and discovered user hardware hints MUST override shipped hardware hints.
- **FR-020**: In unreadable-user-directory fallback mode, runtime MUST prefer audible clean/pass-through behavior and emit a high-visibility warning with corrective guidance, including checking likely storage issues such as SD-card corruption.

### Key Entities *(include if feature involves data)*

- **Service Runtime User**: The operating-system user account under which the service process executes; determines which config and profile paths are authoritative.
- **User Service Config**: The user's TOML configuration source that defines active profile and profile directory settings for runtime behavior.
- **User Profile**: A user-authored voice profile stored in a user-owned profile directory and eligible for startup activation.
- **Built-in Profile**: A shipped profile available by default and separate from user-owned profile content.
- **Built-in Hardware Hint**: A shipped best-guess device/channel configuration used only until user hardware configuration or discovered user hints provide a more specific runtime choice.
- **Path Resolution Result**: The evaluated runtime mapping of config path, profile directories, active profile, and ownership checks.
- **Ownership Mismatch Diagnostic**: A runtime finding that indicates inconsistency between process user and config/profile ownership or permissions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In at least 95% of CLI-boot test runs, the service starts successfully in the intended user context and resolves the expected user TOML config path.
- **SC-002**: In at least 95% of reboot validation runs, the active profile configured in user TOML is loaded on startup without manual path correction.
- **SC-003**: 100% of tested ownership/path mismatch scenarios produce a clear diagnostic message that identifies the mismatch and suggested corrective action.
- **SC-004**: Operators can identify the resolved config path and profile directories within 30 seconds using standard service status/log outputs.
- **SC-005**: In profile authoring loop tests, users complete create-save-configure-reboot-verify workflow within 5 minutes on first attempt in at least 90% of test sessions.
- **SC-006**: Support incidents caused by ambiguous config/profile path resolution decrease by at least 50% compared to the previous release baseline.

## Assumptions

- Device is a single-user embedded costume system; hostile multi-user security scenarios are out of scope.
- Target deployments use Raspberry Pi systems configured for CLI boot where service reliability does not depend on desktop login.
- At least one non-root user account is designated as the canonical service owner for normal operation.
- Profile authoring may occur off-device (dev machine) or on-device (GUI/web), but deployment to runtime always ends in the target service user's profile directory.
- Users performing setup have permission to manage files in their own config/profile paths and to enable service execution in their user context.
- Existing built-in profiles remain available as fallback content when user profile activation fails.
- This feature focuses on ownership, path resolution, and profile activation flow; packaging and multi-architecture release automation are explicitly out of scope.
