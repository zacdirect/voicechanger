---
name: flet
description: "Use when editing Flet GUI code (views, app shell, dialogs, file pickers, navigation) in this repository. Covers Flet 0.84 API patterns, layout constraints, and regression checks."
---

# Flet Skill (voicechanger)

## Scope

Apply this skill for changes in:

- src/voicechanger/gui/app.py
- src/voicechanger/gui/views/*.py
- src/voicechanger/gui/__init__.py

## Version Assumption

This project currently targets Flet 0.84.x. If behavior seems inconsistent, verify API signatures in the active environment before coding.

## Required Patterns

- FilePicker usage:
  - Use return values from `pick_files(...)` and `save_file(...)`.
  - Do not use `on_result` in `FilePicker(...)` constructor for this version.
- Banner usage:
  - `actions` must contain at least one visible control.
  - Avoid empty actions lists.
- NavigationRail layout:
  - Ensure bounded height via parent layout and/or `expand=True`.
  - If needed, set explicit height.
- App initialization:
  - Register view builders before initial `_switch_view(...)`.
  - Prevent startup from rendering placeholder "coming soon" view when actual builders exist.

## Practical Guardrails

- For heavy/blocking work, use `page.run_thread(...)` and update UI states safely.
- Keep each major tab (Control, Profiles, Editor, Tools) loadable with no runtime exceptions.
- Favor explicit user feedback with snackbars for recoverable GUI errors.

## Validation Before Finish

Run all of the following after GUI changes:

- `.venv/bin/pytest --tb=short -q`
- `.venv/bin/ruff check src/ tests/`
- `.venv/bin/python -m voicechanger gui`

Manual smoke test:

- Open each NavigationRail tab once.
- Use Editor and Tools interactions at least once.
- Confirm no runtime tracebacks in terminal.
