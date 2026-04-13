"""CLI commands — argparse-based command routing."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, NoReturn

from voicechanger.config import Config, load_config
from voicechanger.effects import EffectValidationError, validate_effect
from voicechanger.profile import Profile, ProfileValidationError
from voicechanger.registry import ProfileRegistry


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="voicechanger",
        description="Real-time voice changer",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the voice changer service")
    serve_parser.add_argument("--config", default="voicechanger.toml", help="Config file path")
    serve_parser.add_argument("--profile", default=None, help="Initial profile name")
    serve_parser.add_argument("--log-level", default=None, help="Log level override")

    # profile
    profile_parser = subparsers.add_parser("profile", help="Profile management")
    profile_sub = profile_parser.add_subparsers(dest="profile_command", help="Profile commands")

    # profile list
    list_parser = profile_sub.add_parser("list", help="List all profiles")
    list_parser.add_argument("--json", action="store_true", help="JSON output")

    # profile show
    show_parser = profile_sub.add_parser("show", help="Show profile details")
    show_parser.add_argument("name", help="Profile name")
    show_parser.add_argument("--json", action="store_true", help="JSON output")

    # profile switch
    switch_parser = profile_sub.add_parser("switch", help="Switch active profile")
    switch_parser.add_argument("name", help="Profile name to switch to")

    # profile create
    create_parser = profile_sub.add_parser("create", help="Create a new profile")
    create_parser.add_argument("name", help="Profile name")
    create_parser.add_argument(
        "--effect", nargs="+", action="append", default=[],
        help="Effect: TYPE KEY=VALUE...",
    )
    create_parser.add_argument("--author", default="", help="Profile author")
    create_parser.add_argument("--description", default="", help="Profile description")

    # profile delete
    delete_parser = profile_sub.add_parser("delete", help="Delete a user profile")
    delete_parser.add_argument("name", help="Profile name to delete")
    delete_parser.add_argument("--force", action="store_true", help="Force delete")

    # profile export
    export_parser = profile_sub.add_parser("export", help="Export a profile")
    export_parser.add_argument("name", help="Profile name to export")
    export_parser.add_argument("--output", default=None, help="Output file path")

    # device
    device_parser = subparsers.add_parser("device", help="Device management")
    device_sub = device_parser.add_subparsers(dest="device_command")
    device_list_parser = device_sub.add_parser("list", help="List audio devices")
    device_list_parser.add_argument("--json", action="store_true", help="JSON output")

    # status
    status_parser = subparsers.add_parser("status", help="Show service status")
    status_parser.add_argument("--json", action="store_true", help="JSON output")

    # process
    process_parser = subparsers.add_parser("process", help="Offline file processing")
    process_parser.add_argument("input_file", help="Input audio file")
    process_parser.add_argument("output_file", help="Output audio file")
    process_parser.add_argument("--profile", required=True, help="Profile to apply")

    # gui
    subparsers.add_parser("gui", help="Launch the profile authoring GUI")

    return parser


def _get_config(config_path: str = "voicechanger.toml") -> Config:
    """Load config from file."""
    return load_config(Path(config_path))


def _get_socket_path(config: Config | None = None) -> str:
    """Resolve socket path from config or default."""
    if config and config.service.socket_path:
        return config.service.socket_path
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return os.path.join(runtime_dir, "voicechanger.sock")


def _send_ipc_command(
    socket_path: str, command: str, params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an IPC command to the running service."""
    request: dict[str, Any] = {"command": command}
    if params:
        request["params"] = params

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(socket_path)
        try:
            sock.sendall(json.dumps(request).encode("utf-8") + b"\n")
            data = sock.recv(65536)
            return json.loads(data.decode("utf-8").strip())
        finally:
            sock.close()
    except FileNotFoundError:
        print("Error: Service is not running", file=sys.stderr)
        sys.exit(1)
    except ConnectionRefusedError:
        print("Error: Service is not running", file=sys.stderr)
        sys.exit(1)


def _get_registry(config: Config) -> ProfileRegistry:
    """Create a ProfileRegistry from config."""
    return ProfileRegistry(
        builtin_dir=Path(config.profiles.builtin_dir),
        user_dir=Path(config.profiles.user_dir),
    )


def _cmd_serve(args: argparse.Namespace) -> int:
    """Start the service daemon."""
    import logging

    from voicechanger.service import Service

    config = _get_config(args.config)

    if args.log_level:
        config.service.log_level = args.log_level

    # Configure logging
    level = getattr(logging, config.service.log_level.upper(), logging.INFO)
    if config.service.log_format == "json":
        logging.basicConfig(
            level=level,
            format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        )
    else:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    service = Service(config)
    return service.run(initial_profile=args.profile)


def _cmd_profile_list(args: argparse.Namespace) -> int:
    """List all profiles."""
    config = _get_config()
    registry = _get_registry(config)

    # Try to get active profile from service
    active = ""
    try:
        socket_path = _get_socket_path(config)
        resp = _send_ipc_command(socket_path, "get_status")
        if resp.get("ok"):
            active = resp["data"].get("active_profile", "")
    except SystemExit:
        pass

    profiles_data = []
    for name in registry.list():
        profile = registry.get(name)
        if profile:
            profiles_data.append({
                "name": name,
                "type": registry.get_type(name),
                "effects_count": len(profile.effects),
                "description": profile.description,
            })

    if getattr(args, "json", False):
        print(json.dumps({"active": active, "profiles": profiles_data}, indent=2))
    else:
        print(f"  {'NAME':<16} {'TYPE':<10} {'EFFECTS':<8} DESCRIPTION")
        for p in profiles_data:
            marker = "*" if p["name"] == active else " "
            print(
                f"{marker} {p['name']:<16} {p['type']:<10} {p['effects_count']:<8} "
                f"{p['description']}"
            )

    return 0


def _cmd_profile_show(args: argparse.Namespace) -> int:
    """Show profile details."""
    config = _get_config()
    registry = _get_registry(config)
    profile = registry.get(args.name)

    if profile is None:
        print(f"Error: Profile '{args.name}' not found", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        print(json.dumps(profile.to_dict(), indent=2))
    else:
        print(f"Name:        {profile.name}")
        print(f"Type:        {registry.get_type(profile.name)}")
        print(f"Author:      {profile.author}")
        print(f"Description: {profile.description}")
        print(f"Schema:      v{profile.schema_version}")
        print("Effects:")
        for i, effect in enumerate(profile.effects, 1):
            params_str = " ".join(f"{k}={v}" for k, v in effect.get("params", {}).items())
            print(f"  {i}. {effect['type']:<16} {params_str}")

    return 0


def _cmd_profile_switch(args: argparse.Namespace) -> int:
    """Switch the active profile."""
    config = _get_config()
    socket_path = _get_socket_path(config)
    resp = _send_ipc_command(socket_path, "switch_profile", {"name": args.name})

    if resp.get("ok"):
        print(f"Switched to profile: {args.name}")
        return 0
    else:
        error = resp.get("error", {})
        print(f"Error: {error.get('message', 'Unknown error')}", file=sys.stderr)
        return 1


def _parse_effect_args(effect_args: list[list[str]]) -> list[dict[str, Any]]:
    """Parse --effect TYPE KEY=VALUE... arguments into effect dicts."""
    effects: list[dict[str, Any]] = []
    for parts in effect_args:
        if not parts:
            continue
        effect_type = parts[0]
        params: dict[str, Any] = {}
        for kv in parts[1:]:
            if "=" not in kv:
                raise ValueError(f"Invalid parameter format: '{kv}' (expected KEY=VALUE)")
            key, _, value = kv.partition("=")
            try:
                params[key] = float(value)
            except ValueError:
                params[key] = value

        effect = {"type": effect_type, "params": params}

        # Validate the effect
        validated = validate_effect(effect)
        if validated is None:
            raise ValueError(f"Unknown effect type '{effect_type}'")

        effects.append(validated)
    return effects


def _cmd_profile_create(args: argparse.Namespace) -> int:
    """Create a new profile."""
    config = _get_config()
    registry = _get_registry(config)

    try:
        effects = _parse_effect_args(args.effect)
    except (EffectValidationError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        profile = Profile(
            name=args.name,
            effects=effects,
            author=args.author,
            description=args.description,
        )
        registry.create(profile)
        print(f"Created profile: {args.name}")
        return 0
    except (ProfileValidationError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_profile_delete(args: argparse.Namespace) -> int:
    """Delete a user profile."""
    config = _get_config()
    registry = _get_registry(config)

    try:
        registry.delete(args.name)
        print(f"Deleted profile: {args.name}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_profile_export(args: argparse.Namespace) -> int:
    """Export a profile to a file."""
    config = _get_config()
    registry = _get_registry(config)
    profile = registry.get(args.name)

    if profile is None:
        print(f"Error: Profile '{args.name}' not found", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else Path(f"{args.name}.json")
    profile.save(output_path)
    print(f"Exported profile to: {output_path}")
    return 0


def _cmd_device_list(args: argparse.Namespace) -> int:
    """List audio devices."""
    from voicechanger.device import DeviceMonitor

    monitor = DeviceMonitor()
    inputs = monitor.list_input_devices()
    outputs = monitor.list_output_devices()

    if getattr(args, "json", False):
        print(json.dumps({"input_devices": inputs, "output_devices": outputs}, indent=2))
    else:
        print("INPUT DEVICES:")
        if inputs:
            for d in inputs:
                print(f"  card {d['card']}: {d['name']} [{d['card_description']}], "
                      f"device {d['device']}: {d['device_name']} [{d['device_description']}]")
        else:
            print("  (none detected)")
        print("  * default")
        print()
        print("OUTPUT DEVICES:")
        if outputs:
            for d in outputs:
                print(f"  card {d['card']}: {d['name']} [{d['card_description']}], "
                      f"device {d['device']}: {d['device_name']} [{d['device_description']}]")
        else:
            print("  (none detected)")
        print("  * default")

    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Show service status."""
    config = _get_config()
    socket_path = _get_socket_path(config)
    resp = _send_ipc_command(socket_path, "get_status")

    if not resp.get("ok"):
        error = resp.get("error", {})
        print(f"Error: {error.get('message', 'Unknown error')}", file=sys.stderr)
        return 1

    data = resp["data"]

    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
    else:
        uptime = data.get("uptime_seconds", 0)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m" if hours else f"{minutes}m {seconds}s"

        audio = data.get("audio", {})
        print("Service:  running")
        print(f"Profile:  {data.get('active_profile', 'unknown')}")
        print(f"State:    {data.get('state', 'unknown')}")
        print(f"Uptime:   {uptime_str}")
        print(f"Input:    {audio.get('input_device', 'unknown')} "
              f"({audio.get('sample_rate', '?')} Hz)")
        print(f"Output:   {audio.get('output_device', 'unknown')} "
              f"({audio.get('sample_rate', '?')} Hz)")
        print(f"Buffer:   {audio.get('buffer_size', '?')} frames")

    return 0


def _cmd_process(args: argparse.Namespace) -> int:
    """Offline file processing."""
    config = _get_config()
    registry = _get_registry(config)
    profile = registry.get(args.profile)

    if profile is None:
        print(f"Error: Profile '{args.profile}' not found", file=sys.stderr)
        return 1

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' not found", file=sys.stderr)
        return 1

    output_path = Path(args.output_file)

    try:
        from voicechanger.offline import process_file

        process_file(profile, input_path, output_path)
        print(f"Processed: {input_path} → {output_path}")
        return 0
    except ImportError:
        print("Error: pedalboard is required for offline processing", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_gui(_args: argparse.Namespace) -> int:
    """Launch the profile authoring GUI."""
    from voicechanger.gui import launch_gui

    launch_gui()
    return 0


def main(argv: list[str] | None = None) -> NoReturn:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    command_handlers: dict[str, Any] = {
        "serve": _cmd_serve,
        "device": _cmd_device_list,
        "status": _cmd_status,
        "process": _cmd_process,
        "gui": _cmd_gui,
    }

    if args.command == "profile":
        profile_handlers = {
            "list": _cmd_profile_list,
            "show": _cmd_profile_show,
            "switch": _cmd_profile_switch,
            "create": _cmd_profile_create,
            "delete": _cmd_profile_delete,
            "export": _cmd_profile_export,
        }
        handler = profile_handlers.get(getattr(args, "profile_command", None) or "")
        if handler is None:
            parser.parse_args(["profile", "--help"])
            sys.exit(0)
        exit_code = handler(args)
    else:
        handler = command_handlers.get(args.command)
        if handler is None:
            parser.print_help()
            sys.exit(0)
        exit_code = handler(args)

    sys.exit(exit_code)
