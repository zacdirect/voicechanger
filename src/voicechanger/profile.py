"""Profile model — load, save, validate character profiles."""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CURRENT_SCHEMA_VERSION = 1
NAME_REGEX = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


class ProfileValidationError(Exception):
    """Raised when a profile fails validation."""


@dataclass
class Profile:
    """A character voice profile with an ordered chain of audio effects."""

    name: str
    effects: list[dict[str, Any]]
    schema_version: int = CURRENT_SCHEMA_VERSION
    author: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not NAME_REGEX.match(self.name):
            raise ProfileValidationError(
                f"Invalid profile name '{self.name}': must match {NAME_REGEX.pattern} "
                f"(2-64 chars, lowercase alphanumeric + hyphens, no leading/trailing hyphens)"
            )
        if not isinstance(self.effects, list):
            raise ProfileValidationError("effects must be a list")
        for i, effect in enumerate(self.effects):
            if not isinstance(effect, dict):
                raise ProfileValidationError(f"Effect at index {i} must be a dict")
            if "type" not in effect:
                raise ProfileValidationError(f"Effect at index {i} missing required 'type' field")

    @classmethod
    def load(cls, path: Path) -> Profile:
        """Load a profile from a JSON file."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ProfileValidationError(f"Invalid JSON in {path}: {e}") from e

        if not isinstance(data, dict):
            raise ProfileValidationError(
                f"Profile must be a JSON object, got {type(data).__name__}"
            )

        name = data.get("name")
        if not name:
            raise ProfileValidationError(f"Profile in {path} missing required 'name' field")

        effects = data.get("effects")
        if effects is None:
            raise ProfileValidationError(f"Profile in {path} missing required 'effects' field")
        if not isinstance(effects, list):
            raise ProfileValidationError(
                f"Profile 'effects' must be a list, got {type(effects).__name__}"
            )

        schema_version = data.get("schema_version", CURRENT_SCHEMA_VERSION)
        if isinstance(schema_version, int) and schema_version > CURRENT_SCHEMA_VERSION:
            warnings.warn(
                f"Profile '{name}' has schema_version {schema_version} "
                f"(current: {CURRENT_SCHEMA_VERSION}). Loading with best effort.",
                stacklevel=2,
            )

        return cls(
            name=name,
            effects=effects,
            schema_version=(
                schema_version if isinstance(schema_version, int)
                else CURRENT_SCHEMA_VERSION
            ),
            author=data.get("author", ""),
            description=data.get("description", ""),
        )

    def save(self, path: Path) -> None:
        """Save the profile to a JSON file."""
        data = {
            "schema_version": self.schema_version,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "effects": self.effects,
        }
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to a dictionary."""
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "effects": self.effects,
        }
