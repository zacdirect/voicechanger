#!/usr/bin/env python3
"""
Semantic version bumper for voicechanger release automation.

Detects bump type from commit message or branch prefix, updates:
- pyproject.toml
- src/voicechanger/__init__.py
- Any other version-bearing files

Creates annotated Git tag and pushes changes.

Usage:
  python version-bump.py [--commit-msg <msg>] [--bump <type>]

Bump types: major, minor, patch (default: patch)
Commit message hints: [major], [minor], [patch]
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal


def get_current_version() -> str:
    """Extract current version from pyproject.toml or __init__.py"""
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject) as f:
            for line in f:
                if line.startswith('version ='):
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        return match.group(1)
    raise RuntimeError("Could not find current version in pyproject.toml")


def parse_bump_type(commit_msg: str | None = None) -> Literal["major", "minor", "patch"]:
    """
    Detect bump type from commit message.
    Looks for [major], [minor], [patch] markers.
    Defaults to patch if not found.
    """
    if not commit_msg:
        return "patch"
    
    if "[major]" in commit_msg.lower():
        return "major"
    elif "[minor]" in commit_msg.lower():
        return "minor"
    else:
        return "patch"


def bump_version(current: str, bump_type: Literal["major", "minor", "patch"]) -> str:
    """Increment semantic version"""
    parts = current.split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    
    return f"{major}.{minor}.{patch}"


def update_pyproject(version: str) -> None:
    """Update version in pyproject.toml"""
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    content = pyproject.read_text()
    content = re.sub(
        r'version = "[^"]+"',
        f'version = "{version}"',
        content
    )
    pyproject.write_text(content)
    print(f"✓ Updated pyproject.toml to {version}")


def update_init_py(version: str) -> None:
    """Update __version__ in src/voicechanger/__init__.py"""
    init_file = Path(__file__).resolve().parents[2] / "src" / "voicechanger" / "__init__.py"
    if not init_file.exists():
        print(f"ℹ src/voicechanger/__init__.py not found, skipping")
        return
    
    content = init_file.read_text()
    content = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{version}"',
        content
    )
    if "__version__" not in content:
        # Add it if not present
        content = f'__version__ = "{version}"\n\n' + content
    init_file.write_text(content)
    print(f"✓ Updated __init__.py to {version}")


def create_git_tag(version: str) -> None:
    """Create annotated Git tag and push"""
    try:
        # Create tag
        subprocess.run(
            ["git", "tag", "-a", f"v{version}", "-m", f"Release {version}"],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True
        )
        print(f"✓ Created Git tag v{version}")
        
        # Push tag
        subprocess.run(
            ["git", "push", "origin", f"v{version}"],
            cwd=Path(__file__).resolve().parents[2],
            check=True,
            capture_output=True
        )
        print(f"✓ Pushed Git tag v{version}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Git tag failed: {e.stderr.decode() if e.stderr else e}")
        raise


def commit_version_bump(version: str) -> None:
    """Stage and commit version bump"""
    try:
        repo_root = Path(__file__).resolve().parents[2]
        
        # Stage pyproject.toml and __init__.py
        subprocess.run(
            ["git", "add", "pyproject.toml", "src/voicechanger/__init__.py"],
            cwd=repo_root,
            check=True,
            capture_output=True
        )
        
        # Commit
        subprocess.run(
            ["git", "commit", "-m", f"Bump version to {version}"],
            cwd=repo_root,
            check=True,
            capture_output=True
        )
        print(f"✓ Committed version bump to {version}")
    except subprocess.CalledProcessError as e:
        print(f"ℹ Commit failed (may already be committed): {e.stderr.decode() if e.stderr else e}")


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-msg", help="Commit message to parse for bump hints")
    parser.add_argument("--bump", choices=["major", "minor", "patch"], help="Explicit bump type (overrides commit message)")
    parser.add_argument("--dry-run", action="store_true", help="Print proposed version without making changes")
    args = parser.parse_args()
    
    current = get_current_version()
    bump_type = args.bump or parse_bump_type(args.commit_msg)
    next_version = bump_version(current, bump_type)
    
    print(f"Current version: {current}")
    print(f"Bump type: {bump_type}")
    print(f"Next version: {next_version}")
    
    if args.dry_run:
        print("\n[DRY RUN] No changes made")
        return
    
    print()
    update_pyproject(next_version)
    update_init_py(next_version)
    commit_version_bump(next_version)
    create_git_tag(next_version)
    print(f"\n✅ Version bumped to {next_version} and tag created")


if __name__ == "__main__":
    main()
