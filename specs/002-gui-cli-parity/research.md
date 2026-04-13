# Research: GUI–CLI Feature Parity

**Date**: 2026-04-13
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## R1: Flet Navigation Pattern for Multi-View Layout

**Decision**: Use `ft.NavigationRail` with a `ft.Row` layout — sidebar rail + main content area.

**Rationale**: NavigationRail is Flet's Material Design 3 component for switching between 3–5 top-level views. It renders as a persistent vertical sidebar with icon+label destinations. This matches the spec's tabbed/multi-view requirement (FR-017) and is the idiomatic Flet pattern for desktop applications with distinct feature areas.

**Alternatives considered**:
- `ft.Tabs` (TabBar + TabBarView) — horizontal tabs at the top. Good for content categories but less suitable for the primary app navigation with a mix of operational (Control) and creative (Editor) views. Tabs feel more like document tabs; NavigationRail feels more like an app shell.
- Custom sidebar with buttons — more control but reinvents what NavigationRail provides natively.

**Implementation pattern**:
```
ft.Row([
    ft.NavigationRail(destinations=[...], on_change=switch_view),
    ft.VerticalDivider(width=1),
    ft.Column([<active_view_content>], expand=True),
], expand=True)
```

**Views (4 destinations)**:
1. **Control** — Service start/stop, device selection, level meters, status dashboard
2. **Profiles** — Profile browser, switch, delete, export, import
3. **Editor** — Effect chain editor with sliders, preview (current app.py functionality)
4. **Tools** — Offline file processing

## R2: GUI ↔ Service IPC Integration (Remote Control Mode)

**Decision**: Create an async IPC client module (`gui/ipc_client.py`) that wraps the existing Unix domain socket protocol. The GUI auto-detects a running service on startup by probing the socket.

**Rationale**: The service already exposes `switch_profile`, `list_profiles`, `get_profile`, `get_status`, `reload_profiles` over Unix domain socket (JSON-over-newline). The GUI needs to send these same commands when operating in remote-control mode. An async client avoids blocking the Flet event loop.

**Alternatives considered**:
- Synchronous socket client — would block the Flet UI thread, causing freezes during IPC calls.
- HTTP/REST overlay — unnecessary complexity; the socket protocol already works and is well-tested.
- Shared memory / direct module import — requires same process; defeats the purpose of IPC.

**Detection flow**:
1. On GUI startup, attempt `socket.connect()` to the configured socket path.
2. If connection succeeds → remote-control mode. Send `get_status` to confirm.
3. If connection fails (FileNotFoundError / ConnectionRefused) → embedded mode. Start pipeline directly.

**New IPC commands needed for full parity**: The IPC protocol is extended with `set_device` (change input/output device on a running pipeline) and `set_monitor` (toggle monitor/mute). These two commands complete the IPC protocol for full GUI remote-control parity. See [contracts/ipc.md](contracts/ipc.md) for the full command specifications. The `IpcClient` wraps all seven commands: the original five from feature 001, plus `set_device` and `set_monitor`.

## R3: Real-Time Audio Level Metering

**Decision**: Add a level-metering callback to `AudioPipeline` that computes RMS levels from the audio buffer and exposes them via a thread-safe queue or atomic values. The GUI reads these values on a timer (≥15 fps) and renders them using `ft.ProgressBar` widgets with color-coded thresholds.

**Rationale**: The PoC (FsocietyVoiceChanger) computed RMS levels inside the audio callback and pushed them to Tkinter via `widget.after()`. In the Flet architecture, a similar approach works: the audio pipeline writes levels to a shared buffer, and a Flet timer/async loop reads and updates `ft.ProgressBar.value`.

**Alternatives considered**:
- Canvas-based custom VU meter — more visual fidelity but significantly more complexity. `ft.ProgressBar` with color thresholds (green/yellow/red) provides sufficient feedback.
- WebSocket streaming from service — over-engineered for local-only use.

**Implementation approach**:
- In `AudioPipeline`: add optional `level_callback(input_rms: float, output_rms: float)` invoked from the audio processing loop.
- In the GUI: use `page.run_task()` with an async loop that polls levels every ~60ms and updates the ProgressBar values.
- Color thresholds: green (< -20 dB), yellow (-20 to -6 dB), red (> -6 dB).

## R4: Builtin Profile Auto-Fork (Draft) Naming

**Decision**: When a builtin profile is modified in the editor, generate a draft name using the pattern `{original}-custom-{N}` where N starts at 1 and increments to avoid collisions with existing profiles.

**Rationale**: The spec requires a seamless, non-blocking transition (FR-020). Scanning the user profile directory for existing names matching the pattern and picking the next available number is simple and deterministic.

**Alternatives considered**:
- Append timestamp — less readable, harder to organize.
- Prompt for name — explicitly rejected by clarification (no blocking dialog).
- Copy-on-write with same name — would shadow builtins, causing confusion.

**Implementation**: Add a `generate_draft_name(base_name: str, registry: ProfileRegistry) -> str` helper to `gui/state.py` that scans `registry.list()` for `{base}-custom-{N}` collisions.

## R5: Shared GUI State Architecture

**Decision**: Create a `gui/state.py` module with a `GuiState` dataclass that holds cross-view state: selected profile, pipeline mode (embedded/remote), device choices, pipeline running status. Views read/write through this shared state rather than passing data through the Flet control tree.

**Rationale**: With 4 independent views, state must be shared consistently. A central state object avoids event spaghetti between views. The state is not Flet-coupled — it's plain Python, testable without a display.

**Alternatives considered**:
- Flet `page.session` — works but is stringly-typed and hard to test.
- Global module-level variables — not testable, hard to reason about.
- Redux-style store — over-engineered for 4 views with modest state.

## R6: ProfileRegistry Extension for Update

**Decision**: Add an `update(profile: Profile) -> None` method to `ProfileRegistry` that overwrites an existing user profile file. This is needed for the edit-in-place flow (FR-006).

**Rationale**: The current registry has `create()` (fails if exists) and `delete()`. The GUI needs `update()` to save changes to an existing user profile without delete+create (which would lose ordering and is non-atomic).

**Alternatives considered**:
- `delete()` then `create()` — non-atomic, could lose data on crash.
- Direct `Profile.save()` bypassing registry — would desync the in-memory index.
