# Feature Specification: Multi-Architecture Release Automation

**Feature Branch**: `003-multi-arch-release`  
**Created**: 2026-04-13  
**Status**: Draft  
**Input**: User description: "Build scripts into a formal release mechanism using GitHub Actions to handle pedalboard patching and publish binaries + Python packaging for x86_64, aarch64 RPi, and armv7l RPi. Includes example startup files, hardware discovery GUI workflow, production headless boot mode with startx toggle, auto-versioning on merge to main, publication to GitHub releases."

## Scope Clarification

**GUI and CLI Reuse**: The existing GUI and CLI are reused as-is without significant changes. The GUI already detects and displays audio devices and is available on Pi. **CLI is the primary/preferred method** for Pi configuration and headless operation; the GUI is available as an alternative.

**Minimal Code Changes**: This feature is primarily about **packaging, distribution, and documentation**. Code changes are limited to:
- Entry points and version management
- Systemd service files
- Optional helpers to simplify bundling (e.g., Python version bumper to avoid inline shell in GH Actions)
- Production mode toggle script

No new major features, UI redesigns, or extensive refactoring.

## User Scenarios & Testing

### User Story 1 - Cross-Architecture Binary Distribution (Priority: P1)

A developer merges code to `main`. GitHub Actions automatically detects the merge, triggers builds for x86_64 (Ubuntu/Debian), aarch64 (Raspberry Pi OS 64-bit), and armv7l (Raspberry Pi OS 32-bit), applies the pedalboard patch during each build, and publishes all binaries to a GitHub release with automatic version tagging.

**Why this priority**: Without automated multi-arch builds, end users cannot easily deploy to heterogeneous hardware. This is the foundation for the entire release pipeline.

**Independent Test**: Merge a commit to `main` with a version bump. Verify that GitHub Actions creates a new release with three architecture-specific wheels and a pedalboard patch artifact within 30 minutes.

**Acceptance Scenarios**:

1. **Given** code merged to `main` with a version update, **When** GitHub Actions workflow triggers, **Then** builds complete for all three architectures and a GitHub release is created with tagged binaries.
2. **Given** pedalboard patch file exists in the repository, **When** each architecture build runs, **Then** the patch is applied and verified (LivePitchShift present) before packaging.
3. **Given** x86_64 and ARM builds complete successfully, **When** a user downloads the x86_64 wheel on Ubuntu, **Then** the installed binary provides the same CLI/GUI entry points as the ARM build.

---

### User Story 2 - System Packages for Ubuntu and Raspberry Pi OS (Priority: P2)

Developers and system administrators can install the voice changer daemon with a single package manager command on Ubuntu 22.04+, Raspberry Pi OS (32-bit and 64-bit). The package includes systemd service files, entry points for CLI and GUI, and configuration templates.

**Why this priority**: Package managers are the standard distribution mechanism for Linux systems. Wheels alone don't handle daemon lifecycle management.

**Independent Test**: Can install on a fresh Raspberry Pi OS 64-bit using `apt install voicechanger`, then run `voicechanger serve` and `voicechanger gui` without additional setup.

**Acceptance Scenarios**:

1. **Given** an Ubuntu 22.04 system, **When** the user runs `sudo apt install voicechanger`, **Then** the daemon, CLI tools, and GUI launcher are installed with correct permissions.
2. **Given** a Raspberry Pi OS 64-bit system, **When** the package installs, **Then** a systemd service `voicechanger.service` is registered and can be started with `systemctl start voicechanger`.
3. **Given** the package is installed, **When** the user runs `which voicechanger`, **Then** the CLI entry point is in PATH and executable.

---

### User Story 3 - Hardware Discovery via CLI or GUI (Priority: P2)

A user performs a fresh Raspberry Pi OS install and configures audio devices. They can use either the **CLI (`voicechanger list-devices`, `voicechanger set-device`)** for headless operation, or boot into desktop mode and use the existing GUI Control tab, which detects audio input/output devices (including Bluetooth microphones), displays them with human-readable names, and allows selection. Configuration persists across restarts.

**Why this priority**: Pi users often have custom audio hardware (USB mics, Bluetooth speakers). Both CLI and GUI methods must be discoverable and work without additional development.

**Independent Test**: Boot a RPi with an external USB microphone attached. Use CLI to list and select the device; verify it persists. Alternatively, boot to desktop, launch GUI, verify device appears in Control tab, select it, restart, confirm persistence.

**Acceptance Scenarios**:

1. **Given** a fresh Pi with a USB microphone attached, **When** the user runs `voicechanger list-devices`, **Then** all audio devices are listed with human-readable names and current selection status.
2. **Given** a device ID from the list, **When** the user runs `voicechanger set-device input <device-id>`, **Then** the device is selected and persists across restarts.
3. **Given** the GUI Control tab is open with devices available, **When** the user selects a device from the dropdown, **Then** that device persists across restarts (same behavior as CLI).

---

### User Story 4 - Production Headless Boot Mode (Priority: P3)

After configuration via the GUI, a system administrator can switch the Pi to "production mode" where it boots directly into headless voice changer operation (no desktop environment) and automatically starts the service. The administrator can later toggle back to desktop mode with a single command (`startx` or similar), reconfigure if needed, and switch back to headless.

**Why this priority**: Live performers need zero-friction deployment. Headless mode eliminates GUI overhead and improves reliability on resource-constrained hardware.

**Independent Test**: After GUI setup, run a production mode toggle command. Reboot and verify the service starts without X11. Run the toggle again to re-enable desktop mode. Reboot and verify desktop accessible.

**Acceptance Scenarios**:

1. **Given** a configured Raspberry Pi OS system with the GUI setup complete, **When** the user runs `voicechanger production-mode enable`, **Then** the system is configured to boot into runlevel 3 (or equivalent) with the systemd service auto-started.
2. **Given** the system is in production mode, **When** it reboots, **Then** no desktop environment loads and the voice changer service is running (verifiable with `systemctl status voicechanger`).
3. **Given** a system in production mode, **When** the user types `startx`, **Then** the desktop environment starts, the user can open the GUI, and the service continues running in the background.
4. **Given** the user is done reconfiguring in desktop mode, **When** they run `voicechanger production-mode disable`, **Then** the system reverts to standard boot-to-desktop and requires manual service start.

---

### User Story 5 - Example Startup Files and Configuration Documentation (Priority: P3)

The repository includes example systemd service files, startup scripts, and step-by-step configuration guides for common scenarios: fresh Pi setup, Bluetooth pairing, desktop mode toggle, production mode workflow, and emergency fallback.

**Why this priority**: Documentation and examples reduce support burden and enable self-service for users with varying technical backgrounds.

**Independent Test**: A new user follows the README setup guide for Raspberry Pi OS, completes each step without errors, and successfully tests the voice changer on configured hardware.

**Acceptance Scenarios**:

1. **Given** a user with a fresh Raspberry Pi OS install, **When** they follow the setup guide in DEPLOYMENT.md, **Then** they can complete hardware detection, device selection, and a test audio playthrough in under 15 minutes.
2. **Given** the user has a Bluetooth microphone, **When** they follow the Bluetooth pairing subsection, **Then** pairing succeeds and the device appears in the GUI hardware selector.
3. **Given** the user wants to switch to production mode, **When** they follow the production mode guide, **Then** the system boots headless on next restart and the service is running.

---

### User Story 6 - Auto-Versioning on Merge to Main (Priority: P4)

When a developer merges a PR to `main`, the CI automatically detects the merge, increments the project version (semantic versioning: major, minor, patch), updates version strings in all relevant files (`pyproject.toml`, `__init__.py`, etc.), creates an annotated Git tag, and triggers the release build.

**Why this priority**: Manual version management is error-prone. Automation ensures consistency and reduces release checklists.

**Independent Test**: Merge a PR to `main`. Within 5 minutes, verify a new Git tag exists with incremented version and a corresponding GitHub release is created.

**Acceptance Scenarios**:

1. **Given** current version is 0.2.1, **When** a PR is merged to `main`, **Then** CI detects the merge, increments to 0.2.2 (by default), tags the commit, and updates `pyproject.toml` and version files.
2. **Given** a PR includes a commit message with `[major]` or `[minor]` prefix, **When** it merges, **Then** CI uses that to increment major or minor version instead of patch.
3. **Given** the version is bumped, **When** the release build completes, **Then** the GitHub release includes the new version in the title and description.

---

### User Story 7 - GitHub Release Publishing (Priority: P4)

All artifacts—pre-compiled wheels for all architectures, pedalboard patch file, system packages (deb files), documentation (PDF), and SHA256 checksums—are published to a GitHub release page with human-readable descriptions, download links, and installation instructions.

**Why this priority**: Centralized release management via GitHub is the standard for open-source projects and provides discoverability.

**Independent Test**: Navigate to the project's GitHub releases page, verify the latest release includes wheels, deb packages, and a clear installation instruction link.

**Acceptance Scenarios**:

1. **Given** a completed build, **When** the release workflow publishes, **Then** GitHub releases page displays wheels, deb packages, pedalboard patch, checksums, and a README-link in the release description.
2. **Given** a user downloads a wheel, **When** they verify the SHA256 checksum against the release asset, **Then** the checksum matches.
3. **Given** system packages are published, **When** a user follows the installation instructions, **Then** they can install via their OS package manager without manual wheel management.

---

### Edge Cases

- What happens if a build fails on one architecture? System should not publish a release; CI should notify and allow retry or rollback.
- How does the system handle a version conflict (e.g., a tag already exists for that version)? CI should detect and fail with a clear error message.
- What if the pedalboard patch fails to apply during the build? The build should fail loudly and not proceed to packaging.
- Can a user manually trigger a release without a merge? Yes, via a GitHub Actions workflow dispatch parameter for emergency releases or backlogs.

## Requirements

### Functional Requirements

- **FR-001**: GitHub Actions workflow MUST detect merges to `main` and trigger build pipeline.
- **FR-002**: Build pipeline MUST compile and package for x86_64 Linux, aarch64 Linux, and armv7l Linux.
- **FR-003**: Build pipeline MUST apply the pedalboard patch to the vendored submodule during each build and verify LivePitchShift is present.
- **FR-004**: Build pipeline MUST create installable wheels with entry points for `voicechanger` (CLI) and `voicechanger-gui`.
- **FR-005**: Release process MUST auto-increment version (semantic versioning) on merge to `main` based on branch naming or commit message hints.
- **FR-006**: Version MUST be updated in `pyproject.toml`, `src/voicechanger/__init__.py`, and any other version-bearing files.
- **FR-007**: Release process MUST create an annotated Git tag with the new version.
- **FR-008**: System packages (`.deb` files) MUST be generated for Ubuntu 22.04+ and Raspberry Pi OS (32-bit, 64-bit) and included in release assets.
- **FR-009**: System packages MUST include `systemd` service files for automatic daemon startup and management.
- **FR-010**: GitHub release MUST include wheels, system packages, pedalboard patch, and SHA256 checksums with clear installation instructions.
- **FR-011**: Production mode toggle command (`voicechanger production-mode enable|disable`) MUST switch between headless and desktop boot targets.
- **FR-012**: Production mode MUST auto-start the systemd service on boot with no GUI overhead.
- **FR-013**: CLI commands `list-devices` and `set-device` MUST provide device enumeration and selection without GUI dependency.
- **FR-014**: Device selection (via CLI or GUI Control tab) MUST persist across restarts (stored in config file).
- **FR-015**: Documentation MUST include setup guides, Bluetooth pairing instructions, production mode workflow, and emergency fallback procedures.

### Key Entities

- **Release Artifact**: A compiled binary (wheel or deb) for a specific architecture and version, published to GitHub.
- **Configuration Profile**: User-selected audio device preferences, persisted in the local config file (e.g., `/etc/voicechanger.toml`).
- **Systemd Service**: Unix daemon wrapper for the voice changer service, managed by `systemctl`.
- **Build Matrix**: GitHub Actions job matrix defining x86_64, aarch64, armv7l targets and their build configurations.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A GitHub release is automatically created and published within 30 minutes of merge to `main`.
- **SC-002**: All three architecture wheels (x86_64, aarch64, armv7l) are present in the release with correct checksums.
- **SC-003**: System packages (deb) can be installed via `apt install` on Ubuntu 22.04+ and Raspberry Pi OS without manual dependency resolution.
- **SC-004**: A fresh Raspberry Pi OS system can configure audio input via CLI or GUI within 2 minutes.
- **SC-005**: Production mode toggle completes in under 10 seconds; reboot to headless takes under 30 seconds total.
- **SC-006**: A user following the deployment guide can fully configure a Raspberry Pi and test the voice changer in under 30 minutes.
- **SC-007**: All release artifacts on GitHub are downloadable and installable on their target architecture without post-install configuration (beyond device selection).

## Assumptions

- The pedalboard patch file (`patches/pedalboard.patch`) is stable and applicable to all supported pedalboard versions during the release window.
- GitHub Actions is the CI/CD platform; other platforms (GitLab, CircleCI) are out of scope for initial release.
- Debian-based distributions (Ubuntu, Raspberry Pi OS) are the primary Linux targets; other distributions are out of scope for v1.
- Auto-versioning uses semantic versioning (MAJOR.MINOR.PATCH); pre-release and build metadata are out of scope for v1.
- Bluetooth and USB audio device support is hardware-dependent; both CLI and GUI surface OS-provided devices without custom Bluetooth stack implementation.
- Existing GUI and CLI are reused; no new major UI components or features are built as part of this release feature.
- Production mode uses standard Linux runlevels (runlevel 3 headless, runlevel 5 graphical); alternative boot managers are out of scope.
- Users have network access during initial setup to download and install packages; offline installation is out of scope for v1.
