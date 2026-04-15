# Data Model: Service Config + User Profile Boot Workflow

## Entity: ServiceConfigFile

- Description: Parsed TOML configuration used by CLI, GUI, and service startup.
- Fields:
  - `path` (string): Absolute path to TOML file in use (`--config` explicit or default location).
  - `audio.sample_rate` (int): Runtime sample rate.
  - `audio.buffer_size` (int): Audio buffer size.
  - `audio.input_device` (string): Selected input device id/name.
  - `audio.output_device` (string): Selected output device id/name.
  - `profiles.builtin_dir` (string): Builtin profile directory (typically install-root relative).
  - `profiles.user_dir` (string): User profile directory override; empty means default `~/.voicechanger/profiles`.
  - `profiles.active_profile` (string): Profile requested for startup.
  - `service.socket_path` (string): IPC socket path override.
- Validation Rules:
  - Invalid or missing TOML yields default config object.
  - `profiles.active_profile` should reference an existing profile name where possible.
  - Device fields must map to `input_device`/`output_device` schema keys.

## Entity: ProfileDirectorySet

- Description: Resolved profile directories derived from config and runtime environment.
- Fields:
  - `builtin_dir_abs` (path): Absolute builtin path resolved from package root.
  - `user_dir_abs` (path): Absolute user profile directory.
  - `resolution_source` (enum): `default-home`, `config-absolute`, `config-relative-install-root`.
- Validation Rules:
  - `builtin_dir_abs` should exist in normal packaged installs.
  - Missing `user_dir_abs` is allowed; registry should load zero user profiles gracefully.

## Entity: HardwareHintSet

- Description: Resolved hardware hint sources used to choose known-good device/channel defaults.
- Fields:
  - `builtin_dir_abs` (path): Absolute path to shipped hardware hints.
  - `user_dir_abs` (path): Absolute path to user/discovered hardware hints.
  - `builtin_is_advisory` (bool): Always true for shipped hardware hints.
  - `user_overrides_builtin` (bool): True when user hint/config takes precedence.
- Validation Rules:
  - Missing user hardware dir is allowed; runtime may continue using builtin hints.
  - Unreadable user hardware dir must not prevent audible startup.

## Entity: ProfileRecord

- Description: Profile JSON document loaded by registry and consumable by service pipeline.
- Fields:
  - `name` (string): Lowercase/hyphen profile id.
  - `effects` (list[object]): Ordered DSP chain.
  - `schema_version` (int): Compatibility marker.
  - `author` (string): Optional metadata.
  - `description` (string): Optional human-readable summary.
  - `origin` (enum): `builtin` or `user`.
- Validation Rules:
  - `name` must match profile regex.
  - `effects` list required; each entry must include `type`.
  - Built-in profile names remain system-authoritative even if a user creates a conflicting local override.

## Entity: StartupResolutionResult

- Description: Deterministic startup selection used by service at boot.
- Fields:
  - `requested_profile` (string): Config or CLI profile request.
  - `resolved_profile` (string): Loaded profile name actually started.
  - `resolution_reason` (enum): `requested-found`, `fallback-clean`, `startup-failure`.
  - `profile_source` (enum): `builtin`, `user`, `none`.
- State Transitions:
  - `requested-found`: Profile exists and starts pipeline.
  - `fallback-clean`: Requested missing, service falls back to `clean` if available.
  - `startup-failure`: Requested missing and `clean` missing, or audio pipeline cannot start.

## Entity: OperatorWorkflowSession

- Description: End-user journey for creating and deploying a character.
- Steps:
  - `author_profile`: Create/edit profile via GUI or JSON on dev machine.
  - `deploy_profile`: Copy JSON into target user profile directory.
  - `activate_profile`: Update `profiles.active_profile` and relevant devices in config.
  - `restart_system`: Reboot Pi in production mode.
  - `verify_runtime`: Confirm with `voicechanger status` and audible output.
- Failure States:
  - `profile-not-found-at-boot`
  - `wrong-config-path-used`
  - `device-settings-not-persisted`
  - `user-hardware-dir-unreadable`
  - `user-config-dir-unreadable`
