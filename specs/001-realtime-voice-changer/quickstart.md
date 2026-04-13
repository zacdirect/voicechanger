# Quickstart: Realtime Voice Changer

**Date**: 2026-04-12
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Prerequisites

- Python 3.11+
- Linux (x86_64 for development, aarch64 for Raspberry Pi deployment)
- ALSA-compatible audio input and output (USB audio adapter, built-in, or virtual)
- Git (with submodule support)

## Clone & Setup

```bash
git clone --recurse-submodules https://github.com/<org>/voicechanger.git
cd voicechanger
```

If you already cloned without `--recurse-submodules`:
```bash
git submodule update --init --recursive
```

## Build the Patched Pedalboard Wheel

The project vendors Spotify's Pedalboard as a git submodule with a `LivePitchShift` patch applied for low-latency real-time pitch shifting.

```bash
# Apply the patch to the vendored pedalboard
cd vendor/pedalboard
git apply ../../native/patches/0001-add-LivePitchShift.patch
pip install .
cd ../..
```

> **CI note**: The `build-native.yml` workflow automates this for both x86_64 and aarch64.

## Install the Voice Changer

```bash
pip install -e ".[dev]"
```

This installs:
- `voicechanger` package (from `src/`)
- Development dependencies: pytest, ruff, mypy

## Verify Installation

```bash
# List available audio devices
voicechanger device list

# List built-in profiles
voicechanger profile list
```

Expected output includes three built-in profiles: `clean`, `high-pitched`, `low-pitched`.

## Run the Service (Development)

```bash
# Start with default config (uses default audio devices)
voicechanger serve

# Or specify a config file and initial profile
voicechanger serve --config voicechanger.toml --profile high-pitched
```

The service:
1. Opens the configured audio input and output devices
2. Loads the active profile's effect chain
3. Starts real-time audio processing
4. Listens on a Unix socket for CLI commands

Press `Ctrl-C` to stop.

## Switch Profiles at Runtime

In a second terminal:

```bash
# Switch to a different voice
voicechanger profile switch low-pitched

# Check service status
voicechanger status
```

## Create a Custom Profile

```bash
voicechanger profile create my-robot \
  --effect LivePitchShift semitones=-4.0 \
  --effect Distortion drive_db=15.0 \
  --effect Reverb room_size=0.8 wet_level=0.5 \
  --description "Robotic voice effect"

voicechanger profile switch my-robot
```

## Offline File Processing

```bash
voicechanger process input.wav output.wav --profile darth-vader
```

## Run Tests

```bash
# Full test suite
pytest

# With coverage
pytest --cov=voicechanger

# Lint and type check
ruff check src/ tests/
mypy src/
```

## Deploy to Raspberry Pi

1. Build the aarch64 wheel (or download from CI artifacts):
   ```bash
   # On Pi or via cross-compile
   cd vendor/pedalboard
   git apply ../../native/patches/0001-add-LivePitchShift.patch
   pip install .
   ```

2. Install the voice changer:
   ```bash
   pip install .
   ```

3. Copy configuration:
   ```bash
   sudo mkdir -p /etc/voicechanger
   sudo cp voicechanger.toml /etc/voicechanger/
   ```

4. Install the systemd service:
   ```bash
   sudo cp deploy/voicechanger.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now voicechanger
   ```

5. Check status:
   ```bash
   sudo systemctl status voicechanger
   voicechanger status
   ```

## Project Layout

```
src/voicechanger/     # Python package
native/patches/       # C++ patches for pedalboard
vendor/pedalboard/    # Vendored pedalboard (git submodule)
tests/                # pytest test suite
profiles/             # Built-in and user profile JSON files
```

See [plan.md](plan.md) for the full project structure.
