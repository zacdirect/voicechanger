# Data Model: Realtime Voice Changer

**Date**: 2026-04-12
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

## Entities

### Character Profile

A named, portable configuration file defining an ordered chain of audio effects and their parameters. Stored as a single JSON file. The baseline is "clean" (empty effects list = pass-through).

```json
{
  "schema_version": 1,
  "name": "darth-vader",
  "author": "sound-designer",
  "description": "Deep, menacing voice with reverb",
  "effects": [
    {
      "type": "LivePitchShift",
      "params": {
        "semitones": -8.0
      }
    },
    {
      "type": "Gain",
      "params": {
        "gain_db": 3.0
      }
    },
    {
      "type": "Reverb",
      "params": {
        "room_size": 0.6,
        "wet_level": 0.3,
        "dry_level": 0.7
      }
    }
  ]
}
```

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `int` | Yes | Schema version for forward compatibility. Current: `1`. |
| `name` | `str` | Yes | Unique profile name. Must match filename (sans `.json`). Lowercase alphanumeric + hyphens. |
| `author` | `str` | No | Profile creator attribution. |
| `description` | `str` | No | Human-readable description of the voice effect. |
| `effects` | `list[Effect]` | Yes | Ordered list of effects. Empty list = pass-through. |

**Validation rules**:
- `name` must match regex `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` (2–64 chars, lowercase alphanumeric + hyphens, no leading/trailing hyphens).
- `name` must not collide with built-in profile names (case-insensitive).
- `effects` list may be empty (clean pass-through profile).
- Unknown `schema_version` values > current: load with best effort, log warning.
- File must be valid JSON and parseable within 100 ms.

### Effect

A single audio effect instance within a profile's effect chain. Processed in order (first to last).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Effect class name matching the type registry (e.g., `"LivePitchShift"`, `"Gain"`, `"Reverb"`). |
| `params` | `dict[str, float \| int \| str \| bool]` | Yes | Effect-specific parameter key-value pairs. |

**Validation rules**:
- Unknown `type` values are skipped with a warning (additive model per Clarification Q2).
- `params` values are validated against the effect type's parameter ranges at load time. Out-of-range values log a warning and clamp to the nearest valid value.
- An effect with no recognized params but a known `type` uses that effect's defaults.

### System Configuration

System-wide settings stored in `voicechanger.toml` at a configurable path (default: `/etc/voicechanger/voicechanger.toml` on Pi, `./voicechanger.toml` for dev).

```toml
[audio]
sample_rate = 48000
buffer_size = 256
input_device = "default"      # ALSA device name or "default"
output_device = "default"     # ALSA device name or "default"
preferred_input_device = ""   # Optional: poll for this device
preferred_output_device = ""  # Optional: poll for this device
device_poll_interval = 5      # Seconds between device polls
device_mode = "flexible"      # "flexible" (use available, poll for preferred) or "strict" (wait for preferred)

[profiles]
builtin_dir = "profiles/builtin"
user_dir = "profiles/user"
active_profile = "clean"

[service]
socket_path = ""              # Empty = auto ($XDG_RUNTIME_DIR/voicechanger.sock)
log_level = "INFO"
log_format = "json"           # "json" or "text"

[gui]
window_width = 800
window_height = 600
```

### Profile Registry

Runtime component (not persisted). Discovers and indexes profiles from the built-in and user directories.

**Behavior**:
- Scans `builtin_dir` and `user_dir` on startup.
- Built-in profiles are immutable (no delete, no overwrite).
- User profiles with names matching built-in profiles are rejected at creation time.
- Provides `list()`, `get(name)`, `create(profile)`, `delete(name)`, `exists(name)`, `is_builtin(name)`.
- Watches for filesystem changes (or re-scans on demand via IPC command).

### Audio Pipeline

Runtime component (not persisted). Manages the `AudioStream` lifecycle and effect chain application.

**State machine**:

```
STOPPED → STARTING → RUNNING → SWITCHING_PROFILE → RUNNING
                  ↘  DEGRADED (pass-through fallback)  ↗
                     RUNNING → STOPPING → STOPPED
```

- `STARTING`: Enumerating devices, opening `AudioStream`, loading active profile.
- `RUNNING`: Audio flowing through effect chain.
- `SWITCHING_PROFILE`: Rebuilding `Pedalboard` plugins list (audio continues flowing — may hear brief transition).
- `DEGRADED`: Active profile failed to load; audio passes through unprocessed.
- `STOPPING`: Closing `AudioStream`, releasing devices.

## Built-in Profiles

### `clean.json`
```json
{
  "schema_version": 1,
  "name": "clean",
  "author": "voicechanger",
  "description": "Pass-through — no effects applied",
  "effects": []
}
```

### `high-pitched.json`
```json
{
  "schema_version": 1,
  "name": "high-pitched",
  "author": "voicechanger",
  "description": "Chipmunk-style high pitch shift",
  "effects": [
    {
      "type": "LivePitchShift",
      "params": { "semitones": 6.0 }
    },
    {
      "type": "Gain",
      "params": { "gain_db": -2.0 }
    }
  ]
}
```

### `low-pitched.json`
```json
{
  "schema_version": 1,
  "name": "low-pitched",
  "author": "voicechanger",
  "description": "Deep, lowered voice",
  "effects": [
    {
      "type": "LivePitchShift",
      "params": { "semitones": -6.0 }
    },
    {
      "type": "Gain",
      "params": { "gain_db": 2.0 }
    }
  ]
}
```

## Type Registry

The effect type registry maps string type names to Pedalboard plugin classes and their parameter schemas. This enables validation at profile load time and forward-compatible profile parsing.

```python
# Conceptual — actual implementation in src/voicechanger/effects.py
EFFECT_REGISTRY: dict[str, type[Plugin]] = {
    "LivePitchShift": LivePitchShift,  # From patched pedalboard
    "PitchShift": PitchShift,          # For offline processing
    "Gain": Gain,
    "Reverb": Reverb,
    "Chorus": Chorus,
    "Distortion": Distortion,
    "Delay": Delay,
    "Compressor": Compressor,
    "Limiter": Limiter,
    "NoiseGate": NoiseGate,
    "HighpassFilter": HighpassFilter,
    "LowpassFilter": LowpassFilter,
    "HighShelfFilter": HighShelfFilter,
    "LowShelfFilter": LowShelfFilter,
    "PeakFilter": PeakFilter,
    "LadderFilter": LadderFilter,
    "Phaser": Phaser,
    "Bitcrush": Bitcrush,
    "Clipping": Clipping,
    "Resample": Resample,
    "Convolution": Convolution,
}
```

Unknown types at load time → skip with warning, log the type name and profile name.
