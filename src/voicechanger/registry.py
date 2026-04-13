"""ProfileRegistry — discover, index, and manage profiles."""

from __future__ import annotations

import logging
from pathlib import Path

from voicechanger.profile import Profile

logger = logging.getLogger(__name__)


class ProfileRegistry:
    """Discovers and manages profiles from builtin and user directories."""

    def __init__(self, builtin_dir: Path, user_dir: Path) -> None:
        self._builtin_dir = builtin_dir
        self._user_dir = user_dir
        self._builtin: dict[str, Profile] = {}
        self._user: dict[str, Profile] = {}
        self._scan()

    def _scan(self) -> None:
        """Scan builtin and user directories for profile files."""
        self._builtin = self._load_dir(self._builtin_dir)
        self._user = self._load_dir(self._user_dir)

    def _load_dir(self, directory: Path) -> dict[str, Profile]:
        """Load all profile JSON files from a directory."""
        profiles: dict[str, Profile] = {}
        if not directory.exists():
            return profiles
        for path in sorted(directory.glob("*.json")):
            try:
                profile = Profile.load(path)
                profiles[profile.name] = profile
            except Exception:
                logger.warning("Failed to load profile from %s, skipping", path)
        return profiles

    def list(self) -> list[str]:
        """Return sorted list of all profile names."""
        return sorted(set(list(self._builtin.keys()) + list(self._user.keys())))

    def get(self, name: str) -> Profile | None:
        """Get a profile by name. Returns None if not found."""
        if name in self._builtin:
            return self._builtin[name]
        return self._user.get(name)

    def create(self, profile: Profile) -> None:
        """Create a new user profile."""
        if self.is_builtin(profile.name):
            raise ValueError(
                f"Cannot create profile '{profile.name}': conflicts with a built-in profile name"
            )
        if profile.name in self._user:
            raise ValueError(f"Profile '{profile.name}' already exists")

        path = self._user_dir / f"{profile.name}.json"
        profile.save(path)
        self._user[profile.name] = profile

    def delete(self, name: str) -> None:
        """Delete a user profile."""
        if self.is_builtin(name):
            raise ValueError(f"Cannot delete built-in profile '{name}'")
        if name not in self._user:
            raise ValueError(f"Profile '{name}' not found")

        path = self._user_dir / f"{name}.json"
        path.unlink(missing_ok=True)
        del self._user[name]

    def update(self, profile: Profile) -> None:
        """Update an existing user profile (atomic overwrite)."""
        if self.is_builtin(profile.name):
            raise ValueError(
                f"Cannot update built-in profile '{profile.name}'"
            )
        if profile.name not in self._user:
            raise ValueError(f"Profile '{profile.name}' not found")

        path = self._user_dir / f"{profile.name}.json"
        profile.save(path)
        self._user[profile.name] = profile

    def exists(self, name: str) -> bool:
        """Check if a profile exists."""
        return name in self._builtin or name in self._user

    def is_builtin(self, name: str) -> bool:
        """Check if a profile is a built-in profile."""
        return name in self._builtin

    def get_type(self, name: str) -> str:
        """Return 'builtin' or 'user' for a profile."""
        if name in self._builtin:
            return "builtin"
        if name in self._user:
            return "user"
        return "unknown"

    def reload(self) -> int:
        """Re-scan profile directories. Returns total profile count."""
        self._scan()
        return len(self._builtin) + len(self._user)
