"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def tmp_profiles(tmp_path: Path) -> dict[str, Path]:
    """Create temporary builtin and user profile directories."""
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()
    return {"builtin": builtin_dir, "user": user_dir}


@pytest.fixture
def sample_profile_dict() -> dict[str, Any]:
    """A valid sample profile dictionary."""
    return {
        "schema_version": 1,
        "name": "test-profile",
        "author": "tester",
        "description": "A test profile",
        "effects": [
            {"type": "Gain", "params": {"gain_db": 3.0}},
            {"type": "Reverb", "params": {"room_size": 0.5, "wet_level": 0.3, "dry_level": 0.7}},
        ],
    }


@pytest.fixture
def clean_profile_dict() -> dict[str, Any]:
    """A clean pass-through profile dictionary."""
    return {
        "schema_version": 1,
        "name": "clean",
        "author": "voicechanger",
        "description": "Pass-through — no effects applied",
        "effects": [],
    }


@pytest.fixture
def builtin_profiles(tmp_profiles: dict[str, Path], clean_profile_dict: dict[str, Any]) -> Path:
    """Create builtin profiles in a temp directory and return the directory."""
    builtin_dir = tmp_profiles["builtin"]

    profiles = [
        clean_profile_dict,
        {
            "schema_version": 1,
            "name": "high-pitched",
            "author": "voicechanger",
            "description": "Chipmunk-style high pitch shift",
            "effects": [
                {"type": "LivePitchShift", "params": {"semitones": 6.0}},
                {"type": "Gain", "params": {"gain_db": -2.0}},
            ],
        },
        {
            "schema_version": 1,
            "name": "low-pitched",
            "author": "voicechanger",
            "description": "Deep, lowered voice",
            "effects": [
                {"type": "LivePitchShift", "params": {"semitones": -6.0}},
                {"type": "Gain", "params": {"gain_db": 2.0}},
            ],
        },
    ]

    for profile in profiles:
        path = builtin_dir / f"{profile['name']}.json"
        path.write_text(json.dumps(profile, indent=2))

    return builtin_dir


@pytest.fixture
def config_toml(tmp_path: Path, tmp_profiles: dict[str, Path]) -> Path:
    """Create a temporary config TOML file."""
    config_path = tmp_path / "voicechanger.toml"
    config_path.write_text(f"""\
[audio]
sample_rate = 48000
buffer_size = 256
input_device = "default"
output_device = "default"
preferred_input_device = ""
preferred_output_device = ""
device_poll_interval = 5
device_mode = "flexible"

[profiles]
builtin_dir = "{tmp_profiles['builtin']}"
user_dir = "{tmp_profiles['user']}"
active_profile = "clean"

[service]
socket_path = ""
log_level = "INFO"
log_format = "json"

[gui]
window_width = 800
window_height = 600
""")
    return config_path
