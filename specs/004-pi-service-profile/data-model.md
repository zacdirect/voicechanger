# Data Model: Pi CLI Service Profile

## Daemon Operational State

The daemon's persisted state file. Written to `/var/lib/voicechanger/state.json` by the daemon after each accepted state change. Read by the daemon at startup.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| state_schema_version | int | Yes | Schema version for the state file format. Independent of profile schema_version. Current: 1. |
| active_profile | object | Yes | Embedded profile definition (see Profile below). |
| device_config | object | Yes | Current device selections (see DeviceConfig below). |
| origin_user | string | No | OS username of the CLI/GUI process that last pushed state. Empty string if set by daemon default. |
| origin_timestamp | string | No | ISO 8601 timestamp of the last state push. Empty string if set by daemon default. |

### Forward Compatibility

Unknown `state_schema_version` values greater than current: load with best-effort and log a warning. Same pattern as `profile.py` and `hardware.py`.

### Lifecycle

- **Created**: On first accepted IPC state change (profile switch, device set).
- **Updated**: After each accepted IPC state change. Atomic overwrite (write-to-temp, rename).
- **Read**: At daemon startup only.
- **Absent**: On fresh install. Daemon starts with `clean` profile and default device config.

---

## Profile (existing, embedded in state)

Reuses the existing profile schema from `profile.py`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| schema_version | int | Yes | Profile schema version. Current: 1. |
| name | string | Yes | Profile name. Validated: `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$`. |
| effects | list[object] | Yes | Ordered chain of effects. Each has `type` (string) and optional `params` (object). |
| author | string | No | Profile author. Defaults to "". |
| description | string | No | Profile description. Defaults to "". |

No changes to the existing profile schema. The daemon state embeds a full profile definition, not a reference by name.

---

## DeviceConfig

Device selections within the daemon state.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| input_device | string | Yes | Selected input device name. "default" if not explicitly set. |
| output_device | string | Yes | Selected output device name. "default" if not explicitly set. |
| sample_rate | int | Yes | Audio sample rate. Default: 48000. |
| buffer_size | int | Yes | Audio buffer size. Default: 256. |

---

## User Config (TOML, read by CLI/GUI only)

Existing config schema from `config.py`. The daemon never reads this file. The CLI/GUI reads it to determine the user's preferred active profile and device selections, then pushes those to the daemon via IPC.

Key fields relevant to this feature:

| Section | Field | Description |
|---------|-------|-------------|
| profiles | active_profile | Name of the user's preferred active profile. |
| profiles | user_dir | Path to user profile directory. Defaults to `~/.voicechanger/profiles`. |
| audio | input_device | User's preferred input device. |
| audio | output_device | User's preferred output device. |

---

## State Transitions

### Daemon State

```
[No state file] ---(boot)---> Running with `clean` profile, default devices
[State file exists] ---(boot)---> Running with persisted profile and devices
Running ---(IPC: switch_profile)---> Running with new profile; state file updated
Running ---(IPC: set_device)---> Running with new device config; state file updated
Running ---(IPC: shutdown)---> Stopped; state file retained for next boot
```

### CLI/GUI Reconciliation (on connect)

```
[Read daemon state via IPC] + [Read local config/profiles]
  |
  +--> Match: display clean status
  +--> Daemon profile not in local dir: offer to save copy
  +--> Local config disagrees with daemon: report mismatch
  +--> Local version differs from running: report difference
```
