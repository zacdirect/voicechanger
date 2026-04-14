"""Integration checks for release pipeline assets and scripts."""

from __future__ import annotations

from pathlib import Path


def test_release_scripts_exist() -> None:
    assert Path("scripts/release/version-bump.py").exists()
    assert Path("scripts/release/build-deb.sh").exists()


def test_release_workflows_exist() -> None:
    assert Path(".github/workflows/multi-arch-release.yml").exists()
    assert Path(".github/workflows/build-linux.yml").exists()
    assert Path(".github/workflows/publish-release.yml").exists()


def test_production_mode_toggle_script_exists_and_is_shell() -> None:
    script = Path("deploy/production-mode-toggle.sh")
    assert script.exists()
    first_line = script.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!/bin/bash")
