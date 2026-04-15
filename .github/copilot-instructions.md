# voicechanger Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-15

## Active Technologies
- Python 3.11+ + pedalboard (vendored patched build), numpy, tomllib, argparse, systemd service manager (004-pi-cli-service-profile)
- File-based TOML + JSON (`~/.config/voicechanger/voicechanger.toml`, `~/.voicechanger/profiles/*.json`) (004-pi-cli-service-profile)

- Python 3.11+ + pedalboard (patched, vendored as submodule), numpy (001-realtime-voice-changer)

## Project Structure

```text
src/
tests/
```

## Commands

cd src && pytest && ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 004-pi-cli-service-profile: Added Python 3.11+ + pedalboard (vendored patched build), numpy, tomllib, argparse, systemd service manager

- 001-realtime-voice-changer: Added Python 3.11+ + pedalboard (patched, vendored as submodule), numpy

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
