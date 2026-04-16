# IPC State Protocol Contract

Extends the existing IPC protocol (Unix socket, JSON-framed messages) with state persistence commands.

## Existing Commands (unchanged)

- `switch_profile` — switch active profile by name (daemon resolves from built-ins)
- `list_profiles` — list available profiles with source type
- `get_profile` — get profile details by name
- `get_status` — get daemon runtime status
- `reload_profiles` — re-scan profile directories
- `set_monitor` — enable/disable audio monitoring
- `set_device` — set input/output device
- `shutdown` — graceful shutdown

## Modified Commands

### `switch_profile` (extended)

Previously: daemon looked up profile by name from its registry.

Now: CLI pushes the full profile definition in the request. Daemon validates it, applies it, and persists the new state.

**Request**:
```json
{
  "command": "switch_profile",
  "name": "darth-vader",
  "profile": {
    "schema_version": 1,
    "name": "darth-vader",
    "effects": [{"type": "PitchShift", "params": {"semitones": -12}}],
    "author": "zac",
    "description": "Deep voice"
  }
}
```

**Success response**:
```json
{
  "status": "ok",
  "active_profile": "darth-vader",
  "source": "user-pushed"
}
```

**Error response (built-in name collision)**:
```json
{
  "status": "error",
  "error": "Cannot override built-in profile 'clean'. Built-in profiles are system-authoritative."
}
```

**State persistence**: On success, daemon writes updated state to `/var/lib/voicechanger/state.json` with `origin_user` and `origin_timestamp`.

### `get_status` (extended)

Now includes origin metadata and state source in the response.

**Response**:
```json
{
  "status": "ok",
  "active_profile": "darth-vader",
  "profile_source": "user-pushed",
  "effects": [{"type": "PitchShift", "params": {"semitones": -12}}],
  "origin_user": "zac",
  "origin_timestamp": "2026-04-16T12:00:00Z",
  "input_device": "default",
  "output_device": "default",
  "sample_rate": 48000,
  "buffer_size": 256,
  "monitor_enabled": false,
  "pipeline_running": true,
  "uptime_seconds": 3600
}
```

### `set_device` (extended)

Now persists device changes to daemon state file.

**State persistence**: On success, daemon updates device_config in state file.

## New Commands

### `get_state`

Returns the full daemon operational state for CLI reconciliation. Unlike `get_status` (which is a display-oriented summary), `get_state` returns the complete profile definition suitable for saving locally.

**Request**:
```json
{
  "command": "get_state"
}
```

**Response**:
```json
{
  "status": "ok",
  "state_schema_version": 1,
  "active_profile": {
    "schema_version": 1,
    "name": "darth-vader",
    "effects": [{"type": "PitchShift", "params": {"semitones": -12}}],
    "author": "zac",
    "description": "Deep voice"
  },
  "device_config": {
    "input_device": "default",
    "output_device": "default",
    "sample_rate": 48000,
    "buffer_size": 256
  },
  "origin_user": "zac",
  "origin_timestamp": "2026-04-16T12:00:00Z"
}
```

## Contract Rules

1. All state-mutating commands (`switch_profile`, `set_device`) MUST persist state before returning success.
2. The daemon MUST reject `switch_profile` requests where `name` matches a built-in profile name and the request includes a `profile` payload (user trying to override a built-in).
3. `switch_profile` without a `profile` payload switches to a built-in by name (existing behavior).
4. `switch_profile` with a `profile` payload pushes a user-defined profile (new behavior).
5. State persistence uses atomic write (write-to-temp, rename) to prevent corruption on power loss.
