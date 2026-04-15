# Quickstart: Pi Boot-to-CLI with User Character Profiles

This flow targets a Raspberry Pi that should boot headless and auto-start voicechanger, while still making profile authoring easy.

## 1. Author your character profile

Option A (dev machine):

1. Build or edit a JSON profile (`my-character.json`) using the same schema as builtins.
2. Validate locally:
   ```bash
   voicechanger profile show clean --json > /dev/null
   ```

Option B (on Pi desktop):

1. Run `voicechanger gui`.
2. Create/edit your character in the editor.
3. Save/export to JSON.

## 2. Place profile in the user profile directory on Pi

1. Ensure directory exists:
   ```bash
   mkdir -p ~/.voicechanger/profiles
   ```
2. Copy your profile JSON there:
   ```bash
   cp my-character.json ~/.voicechanger/profiles/
   ```
3. Confirm discovery:
   ```bash
   voicechanger profile list
   ```

## 3. Configure active profile and devices

1. Open your config at `~/.config/voicechanger/voicechanger.toml`.
2. Runtime uses the user-owned config as authoritative. Do not rely on a system-level config being merged into headless startup behavior.
2. Set or verify:
   ```toml
   [profiles]
   builtin_dir = "profiles/builtin"
   user_dir = ""
   active_profile = "my-character"

   [audio]
   input_device = "default"
   output_device = "default"
   ```
3. Optional: select explicit devices with CLI once persistence gaps are closed:
   ```bash
   voicechanger set-device input default
   voicechanger set-device output default
   ```

Built-in sound profiles remain system-authoritative. If a user profile collides with a shipped built-in character name, the shipped built-in wins. Shipped hardware hints are different: they are advisory defaults only, and user or discovered hardware hints should override them when available.

## 4. Ensure production mode and reboot

1. Enable production mode:
   ```bash
   voicechanger production-mode enable
   ```
2. Reboot:
   ```bash
   sudo reboot
   ```

## 5. Verify service loaded your character

After boot:

```bash
voicechanger status
voicechanger profile list
```

Expected:

- Service is running.
- `active_profile` equals your character profile.
- Audio pipeline opens selected devices.

If the service cannot read user config or profile directories at startup, it should still come up audibly using shipped defaults, `clean`/pass-through behavior, and known-good hardware polling. Treat that as a recovery mode, not a success state.

## 6. Recovery checks for headless setups

- Missing config: recreate or restore `~/.config/voicechanger/voicechanger.toml` and reboot.
- Missing profile: set `active_profile` back to an existing profile such as `clean`, then reboot.
- Permission denied or wrong runtime user: confirm the same non-root user owns the config/profile paths and runs the service.
- Unreadable user directories: expect audible fallback with warning diagnostics; check filesystem health and likely storage issues such as SD-card corruption.

## Known Gaps To Address In Implementation

- `profile switch` and `set-device` currently persist to a CWD-local `voicechanger.toml` instead of the active `--config` path.
- `set-device` currently writes wrong field names (`device_input`/`device_output`) and does not update runtime-read keys.
- Relative `profiles.user_dir` values are not consistently resolved when not under install root.

Until these are fixed, prefer direct edits to `~/.config/voicechanger/voicechanger.toml` for production changes.
