# Data Model: GUI–CLI Feature Parity

**Date**: 2026-04-13
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Entities

### GuiState

Central state object shared across all GUI views. Not persisted — lives only while the GUI is running.

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `PipelineMode` | `EMBEDDED` or `REMOTE` — how the GUI interacts with the audio pipeline |
| `pipeline_running` | `bool` | Whether the audio pipeline is currently active |
| `pipeline_state` | `str` | Current pipeline state string: `STOPPED`, `RUNNING`, `DEGRADED`, `STARTING` |
| `active_profile_name` | `str` | Name of the currently active profile |
| `selected_input_device` | `str` | Currently selected input device identifier |
| `selected_output_device` | `str` | Currently selected output device identifier |
| `input_level` | `float` | Current input audio RMS level (0.0–1.0), updated by metering loop |
| `output_level` | `float` | Current output audio RMS level (0.0–1.0), updated by metering loop |
| `monitor_enabled` | `bool` | Whether speaker output monitoring is enabled |
| `uptime_seconds` | `int` | Service uptime in seconds (from status polling) |
| `sample_rate` | `int` | Current audio sample rate |
| `buffer_size` | `int` | Current audio buffer size |
| `editing_profile` | `EditingProfile | None` | Profile currently being edited, if any |

**Validation rules**:
- `input_level` and `output_level` clamped to [0.0, 1.0]
- `active_profile_name` must be non-empty when `pipeline_running` is True

### PipelineMode (enum)

| Value | Description |
|-------|-------------|
| `EMBEDDED` | GUI runs its own AudioPipeline instance directly |
| `REMOTE` | GUI connects to a running service via IPC socket |

### EditingProfile

Transient state for a profile being edited in the Editor view.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Current profile name (may be auto-generated for builtin forks) |
| `original_name` | `str` | Name of the profile that was loaded (for tracking forks) |
| `is_builtin_fork` | `bool` | True if this was forked from a builtin profile |
| `is_dirty` | `bool` | True if modifications have been made since last save |
| `effects` | `list[GuiEffectState]` | Current effect chain state |
| `author` | `str` | Profile author |
| `description` | `str` | Profile description |

**State transitions**:
- Load builtin profile → `is_builtin_fork=False`, `is_dirty=False`
- First modification on builtin → `is_builtin_fork=True`, `is_dirty=True`, `name` auto-generated
- Load user profile → `is_builtin_fork=False`, `is_dirty=False`
- Modify user profile → `is_dirty=True`, `name` unchanged
- Save → `is_dirty=False`

### IpcClient

Async wrapper around the existing Unix domain socket protocol.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `connect()` | `socket_path: str` | `bool` | Attempt connection; returns True if service is running |
| `get_status()` | — | `dict` | Fetch `get_status` from service |
| `switch_profile(name)` | `name: str` | `dict` | Send `switch_profile` command |
| `list_profiles()` | — | `dict` | Send `list_profiles` command |
| `get_profile(name)` | `name: str` | `dict` | Send `get_profile` command |
| `reload_profiles()` | — | `dict` | Send `reload_profiles` command |
| `close()` | — | — | Close the socket connection |

### Existing Entities (unchanged)

These entities from feature 001 are used but not modified by this feature:

- **Profile** — `name`, `effects`, `schema_version`, `author`, `description`. JSON file in `profiles/builtin/` or `profiles/user/`.
- **AudioPipeline** — States: `STOPPED → STARTING → RUNNING → DEGRADED → SWITCHING_PROFILE → STOPPING → STOPPED`. Extended with level callback.
- **ProfileRegistry** — `list()`, `get()`, `create()`, `delete()`, `is_builtin()`, `get_type()`, `reload()`. Extended with `update()`.
- **DeviceMonitor** — `list_input_devices()`, `list_output_devices()`. Unchanged.
- **Config** — `AudioConfig`, `ProfilesConfig`, `ServiceConfig`, `GuiConfig`. Unchanged.
- **GuiEffectState** — `type: str`, `params: dict[str, float]`. Unchanged.

## Relationships

```
GuiState 1──1 PipelineMode
GuiState 1──0..1 EditingProfile
GuiState 1──0..1 IpcClient       (only when mode=REMOTE)
GuiState *──1 AudioPipeline       (only when mode=EMBEDDED)
GuiState *──1 ProfileRegistry
GuiState *──1 DeviceMonitor
EditingProfile *──* GuiEffectState
```
