"""System configuration loader — TOML config with defaults."""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    sample_rate: int = 48000
    buffer_size: int = 256
    input_device: str = "default"
    output_device: str = "default"
    preferred_input_device: str = ""
    preferred_output_device: str = ""
    device_poll_interval: int = 5
    device_mode: str = "flexible"


@dataclass
class ProfilesConfig:
    builtin_dir: str = "profiles/builtin"
    user_dir: str = "profiles/user"
    active_profile: str = "clean"


@dataclass
class ServiceConfig:
    socket_path: str = ""
    log_level: str = "INFO"
    log_format: str = "json"


@dataclass
class GuiConfig:
    window_width: int = 800
    window_height: int = 600


@dataclass
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    profiles: ProfilesConfig = field(default_factory=ProfilesConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)


def _safe_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    return default


def _safe_str(value: Any, default: str) -> str:
    if isinstance(value, str):
        return value
    return default


def load_config(path: Path) -> Config:
    """Load configuration from a TOML file, falling back to defaults."""
    config = Config()

    if not path.exists():
        logger.debug("Config file %s not found, using defaults", path)
        return config

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        logger.warning("Failed to parse config file %s, using defaults", path)
        return config

    audio = data.get("audio", {})
    if isinstance(audio, dict):
        config.audio = AudioConfig(
            sample_rate=_safe_int(audio.get("sample_rate"), 48000),
            buffer_size=_safe_int(audio.get("buffer_size"), 256),
            input_device=_safe_str(audio.get("input_device"), "default"),
            output_device=_safe_str(audio.get("output_device"), "default"),
            preferred_input_device=_safe_str(audio.get("preferred_input_device"), ""),
            preferred_output_device=_safe_str(audio.get("preferred_output_device"), ""),
            device_poll_interval=_safe_int(audio.get("device_poll_interval"), 5),
            device_mode=_safe_str(audio.get("device_mode"), "flexible"),
        )

    profiles = data.get("profiles", {})
    if isinstance(profiles, dict):
        config.profiles = ProfilesConfig(
            builtin_dir=_safe_str(profiles.get("builtin_dir"), "profiles/builtin"),
            user_dir=_safe_str(profiles.get("user_dir"), "profiles/user"),
            active_profile=_safe_str(profiles.get("active_profile"), "clean"),
        )

    service = data.get("service", {})
    if isinstance(service, dict):
        config.service = ServiceConfig(
            socket_path=_safe_str(service.get("socket_path"), ""),
            log_level=_safe_str(service.get("log_level"), "INFO"),
            log_format=_safe_str(service.get("log_format"), "json"),
        )

    gui = data.get("gui", {})
    if isinstance(gui, dict):
        config.gui = GuiConfig(
            window_width=_safe_int(gui.get("window_width"), 800),
            window_height=_safe_int(gui.get("window_height"), 600),
        )

    return config
