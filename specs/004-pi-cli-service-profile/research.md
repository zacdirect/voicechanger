# Phase 0 Research: Pi CLI Boot + User Profile Service UX

## Decision 1: Default to user-owned config and profile directories for the documented production workflow

- Decision: Document and target `~/.config/voicechanger/voicechanger.toml` + `~/.voicechanger/profiles` as the canonical operator workflow for profile authoring and headless startup.
- Rationale: Existing service unit already starts with `--config ${HOME}/.config/voicechanger/voicechanger.toml`, and config resolution already defaults user profiles to `~/.voicechanger/profiles` when `profiles.user_dir` is empty.
- Alternatives considered:
  - `/etc/voicechanger/voicechanger.toml` + system-owned profile directory: robust for shared systems, but adds ownership friction for profile editing and exporting from GUI.
  - Repository-relative `voicechanger.toml` and `profiles/user`: easy for local dev, brittle for systemd boot and user sessions.

## Decision 2: Treat relative profile directory paths as install-root-relative only for builtin assets; require explicit absolute or home-relative paths for user profile overrides

- Decision: Keep builtin profile path resolution package-root relative, but document that operator-managed profile overrides should use either empty `profiles.user_dir` (auto-default) or explicit absolute path.
- Rationale: Current `_resolve_dir` behavior only makes relative paths absolute if they exist under package root; otherwise unresolved strings can break profile discovery in service mode.
- Alternatives considered:
  - Resolve all relative paths against config file directory: intuitive but currently not implemented and would require broader migration/testing.
  - Force all paths absolute via validation error: safer but less ergonomic for first-time users.

## Decision 3: Close CLI persistence gaps before relying on reboot workflow

- Decision: Define implementation tasks to make persistence commands (`profile switch`, `set-device`) honor the active config path and valid config keys.
- Rationale: Current CLI flows save to hardcoded `voicechanger.toml` in CWD and write device fields as `device_input`/`device_output`, while runtime reads `input_device`/`output_device`. This can make service restarts ignore user intent.
- Alternatives considered:
  - Require manual TOML edits for every change: unacceptable UX for non-expert users.
  - Persist all live settings only through IPC service state: volatile across reboots without config writeback.

## Decision 4: Keep boot-to-CLI UX as a documented sequence with explicit verification checkpoints

- Decision: Publish a README sequence: design profile on dev machine/Pi GUI -> save JSON in user profile directory -> set active profile and devices in config -> reboot -> verify with CLI status.
- Rationale: This maps directly to the performer/operator journey and minimizes support ambiguity.
- Alternatives considered:
  - Fully automated installer wizard: out of scope for this release slice.
  - GUI-only deployment flow: violates headless-first expectation.

## Decision 5: Add contract-level checks around startup resolution and profile precedence

- Decision: Define tests ensuring service startup reads configured profile dirs, loads active profile from user dir when present, and falls back to `clean` deterministically.
- Rationale: Reliability at boot is core to production mode and must be guarded by tests.
- Alternatives considered:
  - Rely on integration/manual testing only: too fragile for release automation.

## Decision 6: Treat shipped hardware hints as advisory and user hardware hints as authoritative

- Decision: Keep shipped hardware hints under `hardware/builtin` as best guesses, but allow user hardware configuration and discovered user hints to override them.
- Rationale: Unlike built-in sound profiles, hardware hints represent build-time guesses about unknown deployment devices and must yield to runtime user reality.
- Alternatives considered:
  - Make shipped hardware hints authoritative: too rigid for heterogeneous field hardware.
  - Remove shipped hardware hints entirely: weakens out-of-box behavior on common Pi targets.
