# GUI Views Contract: GUI–CLI Feature Parity

**Date**: 2026-04-13
**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md)

## Overview

The GUI exposes four views via a `NavigationRail` sidebar. Each view is a self-contained Flet layout that reads/writes through the shared `GuiState`. Views do not communicate directly with each other.

## Navigation Shell

**Component**: `app.py` — `VoiceChangerApp`

```
┌─────────────────────────────────────────────────────────────┐
│ NavigationRail │ Active View Content                        │
│                │                                            │
│  ◉ Control     │  (rendered by control.py, profiles.py,     │
│  ○ Profiles    │   editor.py, or tools.py depending on      │
│  ○ Editor      │   selected_index)                          │
│  ○ Tools       │                                            │
│                │                                            │
└─────────────────────────────────────────────────────────────┘
```

**Behavior**:
- `on_change` callback swaps the content column to the selected view.
- Views are lazily constructed on first visit, then cached.
- App shell handles startup detection (embedded vs. remote mode).

---

## View 1: Control

**File**: `gui/views/control.py`
**Maps to**: FR-001 (start/stop), FR-002/FR-003 (device selection), FR-010 (level meters), FR-011 (status), FR-013 (monitor toggle), FR-018 (IPC remote control)

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  SERVICE CONTROL                                         │
│  ┌──────────────────────────┐  ┌──────────────────────┐  │
│  │ [▶ Start] [■ Stop]       │  │ Status: RUNNING      │  │
│  │ Profile: clean       [▼] │  │ Uptime: 2h 15m       │  │
│  │ Monitor: [✓]             │  │ Rate: 48000 Hz       │  │
│  └──────────────────────────┘  │ Buffer: 256 frames   │  │
│                                └──────────────────────┘  │
│  AUDIO DEVICES                                           │
│  Input:  [USB Mic ▼]                                     │
│  Output: [USB Speaker ▼]                                 │
│  [🔄 Refresh Devices]                                    │
│                                                          │
│  LEVEL METERS                                            │
│  Input:  ████████░░░░░░░░░░░░  -12 dB                   │
│  Output: ██████░░░░░░░░░░░░░░  -18 dB                   │
└──────────────────────────────────────────────────────────┘
```

### Actions

| Action | Embedded Mode | Remote Mode |
|--------|--------------|-------------|
| Start | `AudioPipeline.start()` | Display "Service already running" (start via CLI) |
| Stop | `AudioPipeline.stop()` | Not available (stop via CLI / systemd) |
| Switch profile | `AudioPipeline.switch_profile()` | `IpcClient.switch_profile()` |
| Select device | Store in `GuiState`, apply on next start | `IpcClient.set_device()` |
| Refresh devices | `DeviceMonitor.list_*()` | `DeviceMonitor.list_*()` (local) |
| Toggle monitor | Toggle mute gain in pipeline | `IpcClient.set_monitor()` |

### Status Polling

- In remote mode: poll `IpcClient.get_status()` every 2 seconds.
- In embedded mode: read from `AudioPipeline.get_status()` directly.

---

## View 2: Profiles

**File**: `gui/views/profiles.py`
**Maps to**: FR-004 (list profiles), FR-005 (switch), FR-006 (create/edit), FR-007 (delete), FR-008 (export), FR-009 (import)

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  PROFILE BROWSER                                         │
│  ┌───────────────────────────────────────────────────┐   │
│  │ BUILTIN                                           │   │
│  │  clean           0 effects   Pass-through         │   │
│  │  high-pitched    2 effects   Chipmunk-style       │   │
│  │  low-pitched     2 effects   Deep, lowered        │   │
│  │ USER                                              │   │
│  │  darth-vader     3 effects   Deep, menacing       │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  SELECTED: darth-vader (user)                            │
│  Author: sound-designer                                  │
│  Effects: LivePitchShift(-8), Gain(+3), Reverb           │
│                                                          │
│  [Activate] [Edit] [Delete] [Export] [Import]            │
└──────────────────────────────────────────────────────────┘
```

### Actions

| Action | Behavior |
|--------|----------|
| Activate | Switch pipeline to selected profile (embedded or IPC) |
| Edit | Load profile into Editor view, navigate to Editor tab |
| Delete | Confirmation dialog → `ProfileRegistry.delete()`. Disabled for builtins. |
| Export | `ft.FilePicker.save_file()` → `Profile.save()` |
| Import | `ft.FilePicker.pick_files()` → `Profile.load()` → `ProfileRegistry.create()` |

---

## View 3: Editor

**File**: `gui/views/editor.py`
**Maps to**: FR-006 (create/edit), FR-015 (effect authoring), FR-020 (builtin auto-fork)

### Layout

Identical to current `app.py` layout (refactored into this view):

```
┌──────────────────────────────────────────────────────────┐
│  PROFILE EDITOR                                          │
│  Name: [darth-vader-custom-1]  Author: [___]             │
│  Description: [____________________]                     │
│  ⓘ Forked from "darth-vader" (builtin)                   │
│                                                          │
│  EFFECTS CHAIN            [Add ▼] [Remove Last]          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ LivePitchShift                                   │    │
│  │   semitones: ────────●──────── -8.00             │    │
│  │ Gain                                             │    │
│  │   gain_db:   ──────────●────── +3.00             │    │
│  │ Reverb                                           │    │
│  │   room_size: ────●──────────── 0.60              │    │
│  │   wet_level: ──●────────────── 0.30              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  [Save] [Save As...] [Preview ▶]                         │
└──────────────────────────────────────────────────────────┘
```

### Builtin Auto-Fork Behavior (FR-020)

1. User loads a builtin profile (e.g., "high-pitched") into the editor.
2. Name field shows "high-pitched", editor state: `is_builtin_fork=False`, `is_dirty=False`.
3. User moves any slider or modifies any field.
4. Editor detects builtin → auto-generates name: "high-pitched-custom-1" (or next available N).
5. Name field updates to "high-pitched-custom-1". A subtle info banner appears: "Forked from high-pitched (builtin)".
6. User can rename the forked profile freely.
7. Save writes to `profiles/user/high-pitched-custom-1.json`.

### Actions

| Action | Behavior |
|--------|----------|
| Save | If user profile: `ProfileRegistry.update()`. If new/forked: `ProfileRegistry.create()`. |
| Save As | Prompt for name → `ProfileRegistry.create()` |
| Preview | Toggle live audio preview via `PreviewManager` (existing logic) |

---

## View 4: Tools

**File**: `gui/views/tools.py`
**Maps to**: FR-012 (offline processing)

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  OFFLINE PROCESSING                                      │
│                                                          │
│  Input File:  [________________________] [Browse...]     │
│  Output File: [________________________] [Browse...]     │
│  Profile:     [clean ▼]                                  │
│                                                          │
│  [Process]                                               │
│                                                          │
│  Status: Idle                                            │
│  ████████████████░░░░░░░░  67%                           │
└──────────────────────────────────────────────────────────┘
```

### Actions

| Action | Behavior |
|--------|----------|
| Browse (input) | `ft.FilePicker.pick_files()` with audio extensions |
| Browse (output) | `ft.FilePicker.save_file()` with audio extensions |
| Process | Run `offline.process_file()` in a background thread via `page.run_thread()` |

Processing runs independently of the real-time pipeline. Progress is estimated by file position or reported as indeterminate.

---

## Cross-View Interactions

| Trigger | Source View | Target View | Mechanism |
|---------|-------------|-------------|-----------|
| "Edit" button on profile | Profiles | Editor | Write to `GuiState.editing_profile`, switch `NavigationRail.selected_index` to Editor |
| Profile saved in editor | Editor | Profiles | `ProfileRegistry.create/update()` → Profiles view re-reads registry on next visit |
| Profile activated | Profiles | Control | Write to `GuiState.active_profile_name` → Control view status updates |
| Device changed | Control | — | Written to `GuiState`, read by pipeline on start |
