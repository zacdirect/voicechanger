# Voicechanger

Real-time voice changer for Raspberry Pi, built on [Spotify's Pedalboard](https://github.com/spotify/pedalboard). Transform your voice through modular character profiles with effects like pitch shift, reverb, chorus, and more — all within a 50 ms latency budget.

- **Headless-first**: Runs as a systemd service on a Raspberry Pi with CLI control over a Unix socket
- **Profile-based**: Character voices are portable JSON files with ordered effect chains
- **Community-friendly**: Copy a profile JSON into the user directory and it's immediately available
- **GUI authoring**: Desktop Flet app for full-parity voice changer control with live audio preview

## Requirements

- Python 3.11+
- Linux (x86_64 for development, aarch64 for Raspberry Pi deployment)
- ALSA-compatible audio input and output
- Git (with submodule support)

## Quick Start

```bash
# Clone with submodules (for the patched Pedalboard)
git clone --recurse-submodules https://github.com/<org>/voicechanger.git
cd voicechanger

# Build the patched Pedalboard (low-latency LivePitchShift)
cd vendor/pedalboard
git apply ../../native/patches/0001-add-LivePitchShift.patch
pip install .
cd ../..

# Install voicechanger with dev dependencies
pip install -e ".[dev]"
```

## Usage

### List Profiles

```bash
voicechanger profile list
```

```
  NAME            TYPE      EFFECTS  DESCRIPTION
* clean           built-in  0        Pass-through — no effects applied
  high-pitched    built-in  2        Chipmunk-style high pitch shift
  low-pitched     built-in  2        Deep, lowered voice
```

### Start the Service

```bash
voicechanger serve
```

This opens the configured audio devices, loads the active profile, and listens for CLI commands on a Unix socket. Press Ctrl-C to stop.

### Switch Profiles at Runtime

```bash
voicechanger profile switch low-pitched
voicechanger status
```

### Create a Custom Profile

```bash
voicechanger profile create my-robot \
  --effect LivePitchShift semitones=-4.0 \
  --effect Distortion drive_db=15.0 \
  --effect Reverb room_size=0.8 wet_level=0.5 \
  --description "Robotic voice effect"
```

### Export & Share Profiles

```bash
voicechanger profile export my-robot --output my-robot.json
```

Copy the JSON file to another installation's `profiles/user/` directory and run `voicechanger profile list` — it appears automatically.

### Offline File Processing

Process a pre-recorded audio file through a profile without running the service:

```bash
voicechanger process input.wav output.wav --profile darth-vader
```

### List Audio Devices

```bash
voicechanger device list
```

### Launch the GUI

The desktop GUI provides full-parity control — everything the CLI can do, plus live audio preview:

```bash
voicechanger gui
```

**Mode detection**: If the service is already running, the GUI connects in **Remote** mode (IPC). Otherwise it starts in **Embedded** mode with its own audio pipeline.

**Four views** (via NavigationRail sidebar):

| View | Purpose |
|------|---------|
| **Control** | Start/stop pipeline, select audio devices, toggle monitor, view status and level meters |
| **Profiles** | Browse builtin/user profiles, activate, delete, export, import |
| **Editor** | Effect chain editor with sliders, live preview, save, builtin auto-fork |
| **Tools** | Offline file processing with profile selection and progress display |

## Configuration

System configuration lives in `voicechanger.toml`:

```toml
[audio]
sample_rate = 48000
buffer_size = 256
input_device = "default"
output_device = "default"

[profiles]
builtin_dir = "profiles/builtin"
user_dir = "profiles/user"
active_profile = "clean"

[service]
socket_path = ""          # Auto: $XDG_RUNTIME_DIR/voicechanger.sock
log_level = "INFO"
log_format = "json"
```

See `voicechanger.toml` in the repo root for all options.

## Deploy to Raspberry Pi

```bash
# Install on the Pi
pip install .

# Copy config
sudo mkdir -p /etc/voicechanger
sudo cp voicechanger.toml /etc/voicechanger/

# Install and enable the systemd service
sudo cp deploy/voicechanger.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now voicechanger
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Project Layout

```
src/voicechanger/       Python package (audio pipeline, CLI, service, GUI)
tests/                  Unit, contract, and integration tests
profiles/builtin/       Built-in character profiles (clean, high-pitched, low-pitched)
profiles/user/          User-created profiles
native/patches/         C++ patch for low-latency LivePitchShift
deploy/                 systemd service unit
voicechanger.toml       Default system configuration
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute features, profiles, and bug fixes.

## License

[MIT](LICENSE)
