# IPC Contract Extension: Device & Monitor Commands

**Date**: 2026-04-13
**Spec**: [../spec.md](../spec.md) | **Extends**: [../../001-realtime-voice-changer/contracts/ipc.md](../../001-realtime-voice-changer/contracts/ipc.md)

## Overview

This contract extends the feature-001 IPC protocol with two new commands: `set_device` and `set_monitor`. These commands enable the GUI to control device selection and monitor/mute state when operating in remote mode (connected to a running service via IPC).

The message format, socket path, connection model, and error handling conventions are unchanged from the base IPC contract.

## New Commands

### `set_device`

Change the input device, output device, or both on the running pipeline. The service restarts the audio stream with the new device(s) while preserving the active profile and effect chain.

**Request**:
```json
{"command": "set_device", "params": {"input_device": "hw:1,0", "output_device": "hw:2,0"}}
```

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `input_device` | `str` | No | ALSA hardware address for the input device. Omit to keep current. |
| `output_device` | `str` | No | ALSA hardware address for the output device. Omit to keep current. |

At least one of `input_device` or `output_device` MUST be provided.

**Success Response**:
```json
{
  "ok": true,
  "data": {
    "input_device": "hw:1,0",
    "output_device": "hw:2,0",
    "restarted": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `input_device` | `str` | The active input device after the change |
| `output_device` | `str` | The active output device after the change |
| `restarted` | `bool` | Whether the audio stream was restarted |

**Error Responses**:
- `INVALID_PARAMS`: Neither `input_device` nor `output_device` provided.
- `DEVICE_NOT_FOUND`: Specified device does not exist or is not available.
- `DEVICE_OPEN_FAILED`: Device exists but could not be opened (in use, permission denied). Service remains on the previous device.
- `PIPELINE_NOT_RUNNING`: No active pipeline to change devices on.

---

### `set_monitor`

Enable or disable audio monitoring (speaker output) on the running pipeline.

**Request**:
```json
{"command": "set_monitor", "params": {"enabled": true}}
```

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | `bool` | Yes | `true` to enable speaker output, `false` to mute |

**Success Response**:
```json
{
  "ok": true,
  "data": {
    "monitor_enabled": true
  }
}
```

**Error Responses**:
- `INVALID_PARAMS`: Missing or non-boolean `enabled` parameter.
- `PIPELINE_NOT_RUNNING`: No active pipeline to change monitor state on.

---

## New Error Codes

| Code | HTTP-like | Description |
|------|-----------|-------------|
| `DEVICE_NOT_FOUND` | 404 | Specified audio device does not exist |
| `DEVICE_OPEN_FAILED` | 422 | Device exists but could not be opened |
| `PIPELINE_NOT_RUNNING` | 409 | Command requires a running pipeline |

## Behavior Notes

- `set_device` triggers a brief audio interruption while the stream restarts. The service MUST keep the pipeline in `RUNNING` state during the transition if possible, falling back to the previous device on failure.
- `set_monitor` toggles a mute gain at the output stage. This is instantaneous with no audio interruption.
- The `get_status` response (from the base contract) already includes `input_device` and `output_device` in the `audio` object. A new `monitor_enabled` field is added to the `audio` object to reflect monitor state.
