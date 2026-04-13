# AGENTS.md

## Voicechanger Agent Guidance

This file captures project-specific guidance for agentic coding work in this repository.

## Flet GUI Guidance (v0.84.x)

Use these rules when editing GUI code under src/voicechanger/gui/.

- Treat this project as using Flet 0.84 APIs. Verify behavior against the installed version before using patterns from older examples.
- FilePicker follows service API semantics (docs: `services/filepicker`):
  - Treat `pick_files(...)`, `save_file(...)`, and `get_directory_path(...)` as async methods.
  - In event handlers, use `async def ...` and `await` these methods.
  - Prefer direct documented calls such as:
    - `files = await ft.FilePicker().pick_files(...)`
    - `path = await ft.FilePicker().save_file(...)`
  - Do not pass `on_result` to `FilePicker(...)`.
  - Do not manually mount FilePicker into layout containers.
- Linux desktop requirement:
  - Ensure `zenity` is installed for FilePicker dialogs to work (`sudo apt-get install zenity`).
- Banner controls require at least one visible action control:
  - Never set `actions=[]`.
  - Include a dismiss/confirm action button even if `open=False` initially.
- NavigationRail must have bounded height:
  - Place it in a vertically constrained layout.
  - Prefer `expand=True` on NavigationRail when hosted in a Column/Row shell.
  - If needed, provide an explicit `height`.
- Initialize navigation views only after view builders are registered:
  - Do not switch to a view before all view builders are attached.
  - Avoid placeholder fallback for primary views during startup.

## Validation Checklist for GUI Changes

When touching GUI code, run:

- `.venv/bin/pytest --tb=short -q`
- `.venv/bin/ruff check src/ tests/`
- `.venv/bin/python -m voicechanger gui`

For runtime GUI regressions, reproduce by opening each rail tab at least once:

- Control
- Profiles
- Editor
- Tools
