"""Unit tests for system config loader."""

from __future__ import annotations

from pathlib import Path

from voicechanger.config import Config, load_config, save_config


class TestConfigLoading:
    """Test TOML config loading."""

    def test_load_valid_config(self, config_toml: Path) -> None:
        config = load_config(config_toml)
        assert config.audio.sample_rate == 48000
        assert config.audio.buffer_size == 256
        assert config.audio.input_device == "default"

    def test_load_profiles_section(self, config_toml: Path) -> None:
        config = load_config(config_toml)
        assert config.profiles.active_profile == "clean"

    def test_load_service_section(self, config_toml: Path) -> None:
        config = load_config(config_toml)
        assert config.service.log_level == "INFO"
        assert config.service.log_format == "json"


class TestConfigDefaults:
    """Test default config values when file is missing or incomplete."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "nonexistent.toml")
        assert config.audio.sample_rate == 48000
        assert config.audio.buffer_size == 256
        assert config.profiles.active_profile == "clean"

    def test_partial_config_fills_defaults(self, tmp_path: Path) -> None:
        partial = tmp_path / "partial.toml"
        partial.write_text('[audio]\nsample_rate = 44100\n')
        config = load_config(partial)
        assert config.audio.sample_rate == 44100
        assert config.audio.buffer_size == 256  # default
        assert config.profiles.active_profile == "clean"  # default


class TestConfigInvalidValues:
    """Test handling of invalid config values."""

    def test_invalid_toml_syntax(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.toml"
        bad.write_text("this is not valid toml [[[")
        config = load_config(bad)
        # Should return defaults on parse error
        assert config.audio.sample_rate == 48000

    def test_wrong_type_uses_default(self, tmp_path: Path) -> None:
        bad = tmp_path / "wrong-type.toml"
        bad.write_text('[audio]\nsample_rate = "not_a_number"\n')
        config = load_config(bad)
        assert config.audio.sample_rate == 48000


class TestConfigPaths:
    """Test path resolution in config."""

    def test_socket_path_auto(self, config_toml: Path) -> None:
        config = load_config(config_toml)
        # Empty socket_path should resolve to auto
        assert config.service.socket_path == ""

    def test_profile_dirs(self, config_toml: Path, tmp_profiles: dict[str, Path]) -> None:
        config = load_config(config_toml)
        assert str(tmp_profiles["builtin"]) in config.profiles.builtin_dir
        assert str(tmp_profiles["user"]) in config.profiles.user_dir


class TestConfigPersistence:
    """Test persisted config round-trips shared settings."""

    def test_save_and_reload_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "voicechanger.toml"
        config = Config()
        config.profiles.active_profile = "high-pitched"
        config.audio.input_device = "PipeWire Sound Server"
        config.audio.output_device = "USB C Earbuds, USB Audio; Front output / input"

        save_config(path, config)
        reloaded = load_config(path)

        assert reloaded.profiles.active_profile == "high-pitched"
        assert reloaded.audio.input_device == "PipeWire Sound Server"
        assert reloaded.audio.output_device == "USB C Earbuds, USB Audio; Front output / input"
