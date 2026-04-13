# Research: Realtime Voice Changer

**Date**: 2026-04-12
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Research Questions

### RQ-1: Is the LivePitchShift C++ patch still required?

**Verdict**: **YES — the patch is required.**

**Findings**:

1. Pedalboard's built-in `PitchShift` plugin wraps RubberBand via a `PrimeWithSilence` delay line that adds ~1 second of silence before any audio is returned. This is intentional for sample-accurate offline processing but catastrophic for live audio.

2. GitHub issue [spotify/pedalboard#350](https://github.com/spotify/pedalboard/issues/350) — "Very High Latency when using AudioStream with PitchShift on the PedalBoard" — was opened July 2024, is *still open* as of April 2026, and has *no comments or workarounds* from the Pedalboard maintainers.

3. The reference project (`FsocietyVoiceChanger`) solved this by creating a `LivePitchShift` C++ class that extends `RubberbandPlugin` directly (bypassing `PrimeWithSilence`). This reduces latency from ~1000 ms to RubberBand's own algorithmic latency (~2–100 ms depending on buffer configuration). The tradeoff is a short fade-in on the first few buffers — inaudible in a live monitoring context.

4. The `LivePitchShift` patch is minimal (~80 lines of C++ diffstat) and touches only the `PitchShift.h` header. It adds a new class alongside the existing `PitchShift` without modifying it.

**Decision**: Vendor Pedalboard as a git submodule under `vendor/pedalboard/`, maintain the `LivePitchShift` patch in `native/patches/`, and build a custom wheel in CI. Use `LivePitchShift` for all real-time audio and stock `PitchShift` for offline file processing (P5).

**Re-evaluation trigger**: If Pedalboard upstream closes issue #350 with a native low-latency pitch shift mode, re-evaluate whether the patch is still needed.

---

### RQ-2: AudioStream threading model and buffer sizing

**Findings**:

1. `AudioStream` uses JUCE's audio I/O internally. When both input and output devices are provided, it runs a real-time audio callback on a high-priority JUCE thread. The `plugins` property holds a `Pedalboard` object whose effects are applied in the callback.

2. `AudioStream` constructor accepts `buffer_size` (frames per callback). Reference project uses 256 frames @ 48 kHz = ~5.3 ms per buffer. This is well within the Pi 3's capabilities for effects like gain, reverb, and chorus. Pitch shift (RubberBand) has its own internal buffering.

3. The `plugins` property is a live reference — appending/removing/replacing plugins on the `Pedalboard` object takes effect on the *next* callback iteration. This means profile hot-switching can be done by rebuilding the `Pedalboard` plugins list without stopping the stream.

4. `AudioStream.run()` blocks until Ctrl-C. For a service daemon, we'll use the context manager (`with AudioStream(...) as stream:`) and block on a separate event/signal rather than `run()`, so we can handle IPC commands concurrently.

**Decision**: Use 256-frame buffer @ 48 kHz as default (configurable). Profile hot-switch implemented by replacing `stream.plugins` list contents. Service main loop uses `threading.Event` for signal-driven shutdown while the audio callback runs on JUCE's thread.

---

### RQ-3: Unix domain socket IPC for CLI ↔ Service communication

**Findings**:

1. Python's `socket` module natively supports `AF_UNIX` sockets. No additional dependencies needed.

2. Protocol options considered:
   - **JSON-over-newline** (JSON-RPC-like): Simple, human-debuggable, easy to test. Each message is a single JSON object terminated by `\n`. No framing library needed.
   - **HTTP over Unix socket**: Overly complex for this use case. Would require an HTTP server library.
   - **Protocol Buffers / msgpack**: Adds dependencies for no real benefit at this scale.

3. The socket file goes in the XDG runtime directory (`/run/user/<uid>/voicechanger.sock`) or falls back to `/tmp/voicechanger.sock`. The systemd service unit creates the runtime directory.

4. Concurrency model: The service runs a single-threaded `select`/`selectors`-based socket listener alongside the JUCE audio thread. Commands are small and fast (switch profile, list profiles, get status) — no need for async frameworks.

**Decision**: JSON-over-newline protocol on a Unix domain socket at `$XDG_RUNTIME_DIR/voicechanger.sock`. Request/response pattern. Use `selectors` module for non-blocking I/O. No third-party dependencies.

---

### RQ-4: Audio device enumeration and hot-detection on Linux/ALSA

**Findings**:

1. Pedalboard does NOT expose audio device enumeration in Python — `AudioStream` accepts device names as strings but doesn't provide a list of available devices.

2. The reference project uses subprocess calls to `aplay -l` and `arecord -l` to enumerate ALSA devices. This approach works on both Pi and x86_64 Linux.

3. For hot-detection (FR-016 polling for preferred device), we can poll `arecord -l` / `aplay -l` on a configurable interval (e.g., every 5 seconds). When the preferred device appears, rebuild the `AudioStream` with the new device. When it disappears, fall back to available hardware.

4. PipeWire's ALSA compatibility layer may require setting `PIPEWIRE_ALSA_PLUGIN_DIR` for correct device routing (observed in reference project).

5. `AudioStream` does expose `default_input_device_name` and `default_output_device_name` class properties.

**Decision**: Enumerate devices via `aplay -l` / `arecord -l` subprocess calls. Background thread polls on configurable interval for preferred device. `AudioStream.default_input_device_name` / `default_output_device_name` used as fallback. Device config stored in system config file (TOML).

---

### RQ-5: Profile file format

**Findings**:

1. Constitution requires human-readable, version-controllable format. JSON and TOML are the candidates.

2. JSON pros: Universal support, no extra dependency, easy to validate with `json` stdlib module, compatible with schema validation libraries. Profiles in the reference project already use JSON.

3. TOML pros: More human-friendly for editing by hand. Python 3.11+ has `tomllib` in stdlib (read-only). Writing TOML requires `tomli-w` (extra dependency).

4. Profile files are primarily machine-generated (by the GUI authoring tool or CLI create command) and machine-consumed. Hand-editing is a secondary use case.

**Decision**: JSON for profile files (zero dependencies, consistent with reference project). TOML for system configuration (`voicechanger.toml`) since it's more appropriate for human-edited config and `tomllib` is read-only in stdlib (we only read system config, never write it programmatically from the service).

---

### RQ-6: Pedalboard available effect types for profile support

**Findings**:

Built-in Pedalboard plugins usable in effect chains (all are `Plugin` subclasses compatible with `Pedalboard`/`AudioStream`):

| Effect | Class | Key Parameters |
|--------|-------|----------------|
| Pitch Shift (offline) | `PitchShift` | `semitones` |
| Pitch Shift (live) | `LivePitchShift` (patched) | `semitones` |
| Gain | `Gain` | `gain_db` |
| Reverb | `Reverb` | `room_size`, `damping`, `wet_level`, `dry_level`, `width`, `freeze_mode` |
| Chorus | `Chorus` | `rate_hz`, `depth`, `centre_delay_ms`, `feedback`, `mix` |
| Distortion | `Distortion` | `drive_db` |
| Delay | `Delay` | `delay_seconds`, `feedback`, `mix` |
| Compressor | `Compressor` | `threshold_db`, `ratio`, `attack_ms`, `release_ms` |
| Limiter | `Limiter` | `threshold_db`, `release_ms` |
| NoiseGate | `NoiseGate` | `threshold_db`, `ratio`, `attack_ms`, `release_ms` |
| HighpassFilter | `HighpassFilter` | `cutoff_frequency_hz` |
| LowpassFilter | `LowpassFilter` | `cutoff_frequency_hz` |
| HighShelfFilter | `HighShelfFilter` | `cutoff_frequency_hz`, `gain_db`, `q` |
| LowShelfFilter | `LowShelfFilter` | `cutoff_frequency_hz`, `gain_db`, `q` |
| PeakFilter | `PeakFilter` | `cutoff_frequency_hz`, `gain_db`, `q` |
| LadderFilter | `LadderFilter` | `mode`, `cutoff_hz`, `resonance`, `drive` |
| Phaser | `Phaser` | `rate_hz`, `depth`, `centre_frequency_hz`, `feedback`, `mix` |
| Bitcrush | `Bitcrush` | `bit_depth` |
| Clipping | `Clipping` | `threshold_db` |
| Resample | `Resample` | `target_sample_rate`, `quality` |
| GSMFullRateCompressor | `GSMFullRateCompressor` | (no configurable params) |
| Invert | `Invert` | (no configurable params) |
| Convolution | `Convolution` | `impulse_response_filename`, `mix` |

**Decision**: Support all standard Pedalboard plugin types in profiles via a type registry that maps effect type strings to classes. A profile's `effects` array lists objects with `type` and `params`. Unknown types are skipped with a warning per the additive model (Clarification Q2).

## Open Questions (for implementation)

- **OQ-1**: What is RubberBand's actual algorithmic latency on a Pi 3 with 256-frame buffer? Needs empirical measurement during implementation. Budget: must be <45 ms (50 ms total minus ~5 ms buffer latency).
- **OQ-2**: Should the systemd service use `Type=notify` with `sd_notify` for readiness signaling, or the simpler `Type=simple`? Decision deferred to implementation — start with `Type=simple`.
- **OQ-3**: Should profile validation happen at load time only, or also at save time? Both — validate on save (in CLI/GUI) and on load (in service, with fallback to pass-through on failure per FR-003).
