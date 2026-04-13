# IPC Contract: Unix Domain Socket Protocol

**Date**: 2026-04-12
**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md)

## Overview

The voice changer service listens on a Unix domain socket for commands from the CLI client. The protocol is JSON-over-newline: each message is a single JSON object terminated by `\n`. The service processes one request per connection and sends one response.

**Socket path**: `$XDG_RUNTIME_DIR/voicechanger.sock` (fallback: `/tmp/voicechanger.sock`)

**Connection model**: Short-lived connections. CLI opens socket, sends request, reads response, closes. No persistent connections. No authentication (socket file permissions provide access control).

## Message Format

### Request

```json
{"command": "<command_name>", "params": { ... }}\n
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | `str` | Yes | Command name (see below) |
| `params` | `dict` | No | Command-specific parameters |

### Response

```json
{"ok": true, "data": { ... }}\n
```

or on error:

```json
{"ok": false, "error": {"code": "<ERROR_CODE>", "message": "<human-readable>"}}\n
```

## Commands

### `switch_profile`

Switch the active profile.

**Request**:
```json
{"command": "switch_profile", "params": {"name": "darth-vader"}}
```

**Success Response**:
```json
{"ok": true, "data": {"profile": "darth-vader", "effects_count": 3}}
```

**Error Responses**:
- `PROFILE_NOT_FOUND`: Profile does not exist.
- `PROFILE_LOAD_FAILED`: Profile exists but failed to load (invalid JSON, unsupported effects). Service remains on previous profile.

---

### `list_profiles`

List all available profiles.

**Request**:
```json
{"command": "list_profiles"}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "active": "clean",
    "profiles": [
      {"name": "clean", "type": "builtin", "effects_count": 0, "description": "Pass-through"},
      {"name": "high-pitched", "type": "builtin", "effects_count": 2, "description": "Chipmunk-style"},
      {"name": "darth-vader", "type": "user", "effects_count": 3, "description": "Deep, menacing voice"}
    ]
  }
}
```

---

### `get_profile`

Get detailed profile information.

**Request**:
```json
{"command": "get_profile", "params": {"name": "darth-vader"}}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "name": "darth-vader",
    "type": "user",
    "author": "sound-designer",
    "description": "Deep, menacing voice with reverb",
    "schema_version": 1,
    "effects": [
      {"type": "LivePitchShift", "params": {"semitones": -8.0}},
      {"type": "Gain", "params": {"gain_db": 3.0}},
      {"type": "Reverb", "params": {"room_size": 0.6, "wet_level": 0.3, "dry_level": 0.7}}
    ]
  }
}
```

---

### `get_status`

Get service status.

**Request**:
```json
{"command": "get_status"}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "state": "RUNNING",
    "active_profile": "darth-vader",
    "uptime_seconds": 9240,
    "audio": {
      "sample_rate": 48000,
      "buffer_size": 256,
      "input_device": "USB Audio Device",
      "output_device": "USB Audio Device",
      "input_channels": 1,
      "output_channels": 1
    }
  }
}
```

State values: `STARTING`, `RUNNING`, `DEGRADED`, `STOPPING`.

---

### `reload_profiles`

Re-scan profile directories.

**Request**:
```json
{"command": "reload_profiles"}
```

**Response**:
```json
{"ok": true, "data": {"profiles_count": 5}}
```

---

## Error Codes

| Code | HTTP-like | Description |
|------|-----------|-------------|
| `PROFILE_NOT_FOUND` | 404 | Requested profile does not exist |
| `PROFILE_LOAD_FAILED` | 422 | Profile exists but is invalid |
| `INVALID_COMMAND` | 400 | Unknown command name |
| `INVALID_PARAMS` | 400 | Missing or invalid command parameters |
| `SERVICE_ERROR` | 500 | Internal service error |
| `NAME_RESERVED` | 409 | Attempted to use a reserved built-in name |

## Security Considerations

- Socket file created with mode `0600` (owner-only access).
- No authentication beyond filesystem permissions — appropriate for single-user Pi device.
- Input size limit: reject messages > 64 KB to prevent memory exhaustion.
- JSON parsing uses `json.loads()` with no custom decoders to avoid injection.
