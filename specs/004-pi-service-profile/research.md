# Research: Pi CLI Service Profile

## Decision 1: Daemon state persistence format

**Decision**: JSON file at `/var/lib/voicechanger/state.json`, extending the existing profile schema with origin metadata and device config.

**Rationale**: The project already uses JSON for profiles and hardware hints with a `schema_version` convention and forward-compatible loading. Using the same format and patterns keeps the codebase consistent. A single file is sufficient — the daemon has exactly one operational state at any time.

**Alternatives considered**:
- TOML (used for user config) — rejected because state includes nested effects chain which is awkward in TOML
- SQLite — rejected as overkill for a single-record state; adds a dependency
- Pickle — rejected due to security and version-compatibility concerns

## Decision 2: Daemon startup without state file (fresh install)

**Decision**: Start with `clean` profile and default device config. No error, no warning — this is just the default first-boot behavior.

**Rationale**: The deb package creates `/var/lib/voicechanger/` with correct ownership. On first boot, the daemon has no state file yet because no user has pushed a profile. Starting with `clean` (pass-through audio) is the existing fallback behavior and is already a built-in profile.

**Alternatives considered**:
- Seed a default state file during deb install — rejected as unnecessary complexity; the daemon can handle the absence
- Log a warning on missing state — rejected per spec; this is normal, not an error

## Decision 3: CLI `apply` as non-interactive push

**Decision**: `apply` reads the user's `~/.voicechanger/voicechanger.toml`, resolves the active profile from the user's local profile directory, and pushes the full profile definition to the daemon via IPC without prompting.

**Rationale**: `apply` is designed for use in `.bash_profile` or similar login hooks. Interactive prompts would block shell login. State reconciliation (surfacing differences) is the job of `status`, which is interactive.

**Alternatives considered**:
- Interactive `apply` with prompts — rejected because it blocks login automation
- `apply` only pushes if daemon is on `clean` — rejected because users expect their preferences to take effect on login regardless of prior state

## Decision 4: Service unit type change

**Decision**: Change from user service (`%h` expansion) to system service running as a dedicated `voicechanger` user.

**Rationale**: The daemon must start at boot before any user logs in. A system service with `User=voicechanger` achieves this. The daemon reads its own state from `/var/lib/voicechanger/`, not user home directories, so it doesn't need user-context `%h` expansion.

**Alternatives considered**:
- Keep as user service with systemd `--user` and `linger` — rejected because it requires user login or explicit linger enablement, adding setup complexity
- Run as root — rejected; unnecessary privilege for audio processing

## Decision 5: CLI/GUI bootstrap on first use

**Decision**: CLI/GUI creates `~/.voicechanger/` with `profiles/`, `hardware/` subdirectories and a default `voicechanger.toml` on first use if the directory doesn't exist.

**Rationale**: Users should never need to manually create directories. The deb package seeds `/etc/skel/.voicechanger/` for new users, but this doesn't cover existing users or non-deb installs. The CLI must be self-sufficient.

**Alternatives considered**:
- Rely solely on skel/post-install — rejected because it doesn't handle existing users or pip installs
- Prompt the user before creating — rejected because it adds friction to the zero-config goal

## Decision 6: State schema extending profile schema

**Decision**: The daemon state file wraps the existing profile schema (`schema_version`, `name`, `effects`, `author`, `description`) with additional fields: `origin_user`, `origin_timestamp`, `device_config`, and a top-level `state_schema_version`.

**Rationale**: Reusing the profile schema avoids duplication and ensures profiles can round-trip between user files and daemon state. The `state_schema_version` is separate from the profile's `schema_version` to allow independent evolution. Forward-compatible loading follows the same pattern as `profile.py` and `hardware.py`.

**Alternatives considered**:
- Flatten everything into one schema — rejected because profile schema and state schema evolve independently
- Store profile as a nested sub-object — this is the chosen approach; the profile is embedded in the state, not referenced by name
