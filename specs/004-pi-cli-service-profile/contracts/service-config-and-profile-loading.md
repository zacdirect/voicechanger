# Contract: Service Config And Profile Loading

## Purpose

Define expected behavior for how CLI and service locate config, resolve profile directories, and choose the active profile at startup for Pi headless operation.

## Scope

- CLI command persistence semantics for profile and device settings.
- Service startup profile selection from TOML and profile directories.
- Directory/path resolution rules affecting per-user saved profiles.

## Configuration Path Contract

1. `voicechanger serve --config <path>` MUST load TOML from `<path>`.
2. Any command that persists runtime-affecting settings (`profile switch`, `set-device`) MUST write to the same active config path used by operator workflow, not a hardcoded CWD file.
3. If no explicit config path is provided, default path policy MUST be documented and consistent across CLI, GUI, and service unit.
4. When both user-level and system-level config files exist, runtime MUST use user-level config as authoritative and MUST NOT merge system config.

## Profile Directory Resolution Contract

1. `profiles.builtin_dir` MUST resolve relative to install/package root.
2. `profiles.user_dir = ""` MUST resolve to `~/.voicechanger/profiles` for the runtime user.
3. If `profiles.user_dir` is set explicitly:
   - absolute path MUST be used as-is;
   - relative path behavior MUST be deterministic and documented.
4. Missing user directory MUST NOT crash startup; service continues with shipped defaults.
5. Unreadable user configuration or profile directories MUST degrade to shipped defaults, prefer clean/pass-through audio behavior, and emit corrective warning diagnostics.

## Hardware Hint Resolution Contract

1. Shipped hardware hints under the system builtin hardware directory are advisory defaults only.
2. User hardware configuration and discovered user hardware hints MUST override shipped hardware hints.
3. If user hardware configuration cannot be read at startup, runtime MUST fall back to shipped defaults and known-good hardware polling rather than failing silent.

## Startup Profile Selection Contract

1. Service startup requested profile order:
   - `--profile` CLI override if provided;
   - otherwise `profiles.active_profile` from config.
2. If requested profile exists, service MUST load it and expose it as active.
3. If requested profile does not exist, service MUST attempt fallback to `clean`.
4. If `clean` is also unavailable, service MUST fail startup with a non-zero exit code and structured error logging.

## Profile Precedence Contract

1. Profile names are globally unique at runtime.
2. User profile saves and updates MUST be deterministic last-save-wins for user-owned profiles.
3. Built-in profiles are system-authoritative and MUST NOT be overridden by local user `built-in` folders.
4. If an attempted local built-in override is detected, runtime MUST ignore the override and emit a warning with the selected source.

## Device Persistence Contract

1. Persisted audio device keys MUST be:
   - `audio.input_device`
   - `audio.output_device`
2. Persisted values MUST survive reboot and be used by service startup.
3. Invalid device values MUST return actionable CLI errors without corrupting config.

## Observability Contract

1. `voicechanger status` MUST include active profile and current audio devices.
2. Logs on startup MUST include:
   - selected config path;
   - resolved profile directories;
   - active profile result (`requested-found` or fallback reason).

## Suggested Contract Tests

1. `serve` uses provided `--config` and loads active profile from configured user directory.
2. `profile switch` persists `profiles.active_profile` to active config path when service online and offline.
3. `set-device` persists to `audio.input_device`/`audio.output_device` keys.
4. Missing requested profile falls back to `clean`; missing `clean` fails startup.
5. Explicit absolute `profiles.user_dir` works; empty `user_dir` resolves to home default.
