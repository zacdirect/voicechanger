# CLI Contract: Realtime Voice Changer

**Date**: 2026-04-12
**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md)

## Overview

The `voicechanger` CLI serves two roles:
1. **Service management** — starting the audio service daemon.
2. **Client commands** — communicating with the running service over a Unix domain socket to manage profiles and query status.

Entry point: `python -m voicechanger` or installed as `voicechanger` console script.

## Commands

### `voicechanger serve`

Start the voice changer audio service. Blocks until SIGTERM/SIGINT.

```
voicechanger serve [--config PATH] [--profile NAME] [--log-level LEVEL]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--config` | `voicechanger.toml` | Path to system configuration file |
| `--profile` | From config `active_profile` | Override the initially active profile |
| `--log-level` | From config `log_level` | Override log level (DEBUG, INFO, WARNING, ERROR) |

**Behavior**: Opens audio devices, loads active profile, starts AudioStream, opens Unix socket for IPC, blocks on signal. On SIGTERM: graceful shutdown (close stream, close socket). On unhandled error: log, fall back to pass-through, continue running.

**Exit codes**: `0` = clean shutdown, `1` = startup failure (no audio devices), `2` = config error.

---

### `voicechanger profile list`

List all available profiles.

```
voicechanger profile list [--json]
```

**Output (text)**:
```
  NAME            TYPE      EFFECTS  DESCRIPTION
* clean           built-in  0        Pass-through — no effects applied
  high-pitched    built-in  2        Chipmunk-style high pitch shift
  low-pitched     built-in  2        Deep, lowered voice
  darth-vader     user      3        Deep, menacing voice with reverb
```

`*` marks the currently active profile.

**Output (JSON)**:
```json
{
  "active": "clean",
  "profiles": [
    {"name": "clean", "type": "builtin", "effects_count": 0, "description": "Pass-through — no effects applied"},
    ...
  ]
}
```

---

### `voicechanger profile show <name>`

Show detailed information about a profile.

```
voicechanger profile show <name> [--json]
```

**Output (text)**:
```
Name:        darth-vader
Type:        user
Author:      sound-designer
Description: Deep, menacing voice with reverb
Schema:      v1
Effects:
  1. LivePitchShift  semitones=-8.0
  2. Gain            gain_db=3.0
  3. Reverb          room_size=0.6 wet_level=0.3 dry_level=0.7
```

**Error**: Profile not found → exit code 1, message to stderr.

---

### `voicechanger profile switch <name>`

Switch the running service to a different profile.

```
voicechanger profile switch <name>
```

**Behavior**: Sends a `switch_profile` command to the running service over IPC. The service rebuilds the Pedalboard plugins list. Audio continues flowing during the switch.

**Output**: `Switched to profile: darth-vader`

**Errors**:
- Service not running → exit code 1, `Error: Service is not running`
- Profile not found → exit code 1, `Error: Profile 'foo' not found`

---

### `voicechanger profile create <name> [--effect TYPE KEY=VALUE...]...`

Create a new user profile.

```
voicechanger profile create darth-vader \
  --effect LivePitchShift semitones=-8.0 \
  --effect Gain gain_db=3.0 \
  --effect Reverb room_size=0.6 wet_level=0.3
```

| Argument | Description |
|----------|-------------|
| `<name>` | Profile name (must match naming rules) |
| `--effect` | Repeatable. Effect type followed by key=value params |
| `--author` | Optional author attribution |
| `--description` | Optional description |

**Behavior**: Validates name (not built-in, matches regex), validates effect types and params, writes JSON file to user profiles directory.

**Errors**:
- Name conflicts with built-in → exit code 1, `Error: 'clean' is a reserved built-in profile name`
- Invalid effect type → exit code 1, `Error: Unknown effect type 'Foo'`
- Invalid param → exit code 1, `Error: Invalid parameter 'xyz' for effect 'Gain'`

---

### `voicechanger profile delete <name>`

Delete a user profile.

```
voicechanger profile delete <name> [--force]
```

**Behavior**: Removes the profile file from the user profiles directory.

**Errors**:
- Built-in profile → exit code 1, `Error: Cannot delete built-in profile 'clean'`
- Active profile → exit code 1, `Error: Cannot delete active profile 'darth-vader'. Switch to another profile first.` (unless `--force`)
- Not found → exit code 1, `Error: Profile 'foo' not found`

---

### `voicechanger profile export <name> [--output PATH]`

Export a profile to a standalone file.

```
voicechanger profile export darth-vader --output ~/darth-vader.json
```

**Default output**: `./<name>.json` in current directory.

---

### `voicechanger device list`

List available audio input and output devices.

```
voicechanger device list [--json]
```

**Output (text)**:
```
INPUT DEVICES:
  card 1: USB Audio [USB Audio Device], device 0: USB Audio [USB Audio]
  * default

OUTPUT DEVICES:
  card 1: USB Audio [USB Audio Device], device 0: USB Audio [USB Audio]
  * default
```

---

### `voicechanger status`

Query the running service status.

```
voicechanger status [--json]
```

**Output (text)**:
```
Service:  running
Profile:  darth-vader
State:    RUNNING
Uptime:   2h 34m
Input:    USB Audio Device (48000 Hz, 1 ch)
Output:   USB Audio Device (48000 Hz, 1 ch)
Buffer:   256 frames (5.3 ms)
```

---

### `voicechanger process <input-file> <output-file> --profile <name>`

Offline file processing (P5).

```
voicechanger process input.wav output.wav --profile darth-vader
```

**Behavior**: Reads input file, applies profile effect chain (using stock `PitchShift` for offline, not `LivePitchShift`), writes output file. Does NOT require the service to be running.

**Exit codes**: `0` = success, `1` = error (file not found, invalid profile, unsupported format).
