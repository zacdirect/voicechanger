# Quickstart: Pi CLI Service Profile

## Prerequisites

- Raspberry Pi with voicechanger deb package installed
- Audio device connected (USB adapter or HAT DAC)

## First Use (fresh install)

1. **Install the package**:
   ```bash
   sudo apt install voicechanger
   ```
   The deb package installs the daemon, creates the `voicechanger` system user, and enables the systemd service. The daemon starts automatically with `clean` (pass-through audio).

2. **Verify the daemon is running**:
   ```bash
   voicechanger status
   ```
   Expected: shows `clean` profile active, default devices, no origin user.

3. **Create your first profile**:
   ```bash
   voicechanger profile create darth-vader
   ```
   The CLI bootstraps `~/.voicechanger/` if it doesn't exist, then opens the profile for editing. On first run, this creates the user's config directory, profiles directory, and a default config file automatically.

4. **Push the profile to the daemon**:
   ```bash
   voicechanger profile switch darth-vader
   ```
   The CLI reads the profile from your local directory, pushes it to the daemon via IPC, and the daemon applies it immediately. Audio effects are now active.

5. **Verify**:
   ```bash
   voicechanger status
   ```
   Expected: shows `darth-vader` active, your username as origin, effects chain visible.

## Login-Time Profile Loading

To have your profile applied automatically when you log in:

```bash
# Add to ~/.bash_profile or ~/.profile
voicechanger apply
```

`apply` reads your `~/.voicechanger/voicechanger.toml`, resolves your preferred active profile, and pushes it to the daemon without prompting. Safe for non-interactive use.

## Checking What's Running

```bash
voicechanger status
```

Shows: active profile name, effects chain, device config, who last pushed config and when. If the daemon is running a profile you don't have locally, `status` will tell you and offer to save a copy.

## Switching Profiles

```bash
# List available profiles (your local profiles + daemon built-ins)
voicechanger profile list

# Switch to a different profile
voicechanger profile switch bane

# Switch to a built-in
voicechanger profile switch clean
```

## Device Configuration

```bash
# List available audio devices
voicechanger device list

# Set input/output devices
voicechanger device set --input "USB Audio" --output "USB Audio"
```

Device changes are pushed to the daemon and persisted in its state file. They survive reboots.

## Reboot Behavior

After reboot, the daemon starts automatically and resumes with the last-pushed profile and device config. No user login required. When you log in and run `voicechanger status` or `voicechanger apply`, the CLI connects to the already-running daemon.

## Validation Checklist

- [ ] Fresh install: `voicechanger status` shows `clean`, daemon is running
- [ ] First profile: `voicechanger profile create` bootstraps `~/.voicechanger/` automatically
- [ ] Push profile: `voicechanger profile switch <name>` applies effects immediately
- [ ] Reboot: daemon resumes last profile without user login
- [ ] Login apply: `voicechanger apply` pushes user's preferred profile non-interactively
- [ ] Status: shows active profile, effects, devices, origin metadata
