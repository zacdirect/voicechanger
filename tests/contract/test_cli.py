"""Contract tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from voicechanger.cli import _build_parser, main


class TestCLIArgumentParsing:
    """Test CLI argument parsing for all commands."""

    def test_serve_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["serve"])
        assert args.command == "serve"

    def test_serve_with_options(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["serve", "--config", "test.toml", "--profile", "clean"])
        assert args.command == "serve"
        assert args.config == "test.toml"
        assert args.profile == "clean"

    def test_profile_list(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["profile", "list"])
        assert args.command == "profile"
        assert args.profile_command == "list"

    def test_profile_list_json(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["profile", "list", "--json"])
        assert args.json is True

    def test_profile_show(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["profile", "show", "darth-vader"])
        assert args.profile_command == "show"
        assert args.name == "darth-vader"

    def test_profile_switch(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["profile", "switch", "high-pitched"])
        assert args.profile_command == "switch"
        assert args.name == "high-pitched"

    def test_profile_create(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([
            "profile", "create", "my-robot",
            "--effect", "Gain", "gain_db=3.0",
            "--description", "Test profile",
        ])
        assert args.profile_command == "create"
        assert args.name == "my-robot"
        assert args.description == "Test profile"

    def test_profile_delete(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["profile", "delete", "my-robot"])
        assert args.profile_command == "delete"
        assert args.name == "my-robot"

    def test_profile_delete_force(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["profile", "delete", "my-robot", "--force"])
        assert args.force is True

    def test_profile_export(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["profile", "export", "darth-vader", "--output", "/tmp/dv.json"])
        assert args.profile_command == "export"
        assert args.name == "darth-vader"
        assert args.output == "/tmp/dv.json"

    def test_device_list(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["device", "list"])
        assert args.command == "device"

    def test_status_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_status_json(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["status", "--json"])
        assert args.json is True

    def test_process_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["process", "input.wav", "output.wav", "--profile", "clean"])
        assert args.command == "process"
        assert args.input_file == "input.wav"

    def test_gui_command(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["gui"])
        assert args.command == "gui"


class TestCLIExitCodes:
    """Test CLI exit codes for various scenarios."""

    def test_profile_list_succeeds(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        """profile list with local dirs (no service needed) should succeed."""
        with patch("voicechanger.cli._get_config") as mock_config:
            from voicechanger.config import Config, ProfilesConfig

            mock_config.return_value = Config(
                profiles=ProfilesConfig(
                    builtin_dir=str(builtin_profiles),
                    user_dir=str(tmp_profiles["user"]),
                )
            )
            # profile list reads directly from filesystem, no service needed
            with pytest.raises(SystemExit) as exc:
                main(["profile", "list"])
            assert exc.value.code == 0

    def test_profile_show_existing(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        with patch("voicechanger.cli._get_config") as mock_config:
            from voicechanger.config import Config, ProfilesConfig

            mock_config.return_value = Config(
                profiles=ProfilesConfig(
                    builtin_dir=str(builtin_profiles),
                    user_dir=str(tmp_profiles["user"]),
                )
            )
            with pytest.raises(SystemExit) as exc:
                main(["profile", "show", "clean"])
            assert exc.value.code == 0

    def test_profile_show_nonexistent(
        self, builtin_profiles: Path, tmp_profiles: dict[str, Path]
    ) -> None:
        with patch("voicechanger.cli._get_config") as mock_config:
            from voicechanger.config import Config, ProfilesConfig

            mock_config.return_value = Config(
                profiles=ProfilesConfig(
                    builtin_dir=str(builtin_profiles),
                    user_dir=str(tmp_profiles["user"]),
                )
            )
            with pytest.raises(SystemExit) as exc:
                main(["profile", "show", "nonexistent"])
            assert exc.value.code == 1


class TestCLIOutputFormat:
    """Test text and JSON output formats."""

    def test_profile_list_text(
        self, builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with patch("voicechanger.cli._get_config") as mock_config:
            from voicechanger.config import Config, ProfilesConfig

            mock_config.return_value = Config(
                profiles=ProfilesConfig(
                    builtin_dir=str(builtin_profiles),
                    user_dir=str(tmp_profiles["user"]),
                )
            )
            with pytest.raises(SystemExit):
                main(["profile", "list"])
            output = capsys.readouterr().out
            assert "clean" in output
            assert "high-pitched" in output

    def test_profile_list_json(
        self, builtin_profiles: Path,
        tmp_profiles: dict[str, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with patch("voicechanger.cli._get_config") as mock_config:
            from voicechanger.config import Config, ProfilesConfig

            mock_config.return_value = Config(
                profiles=ProfilesConfig(
                    builtin_dir=str(builtin_profiles),
                    user_dir=str(tmp_profiles["user"]),
                )
            )
            with pytest.raises(SystemExit):
                main(["profile", "list", "--json"])
            output = capsys.readouterr().out
            data = json.loads(output)
            assert "profiles" in data
            names = [p["name"] for p in data["profiles"]]
            assert "clean" in names
