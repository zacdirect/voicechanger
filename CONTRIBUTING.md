# Contributing to Voicechanger

Thanks for your interest in contributing! This project uses **speckit** — an AI-assisted specification workflow — to keep features well-specified, planned, and tested before code is written. Please follow the workflow below so the repo stays consistent.

## The speckit Workflow

Every non-trivial change follows this pipeline. Each step produces artifacts in `specs/<feature>/` that the next step builds on.

```
specify → clarify → plan → tasks → checklist → implement → analyze
```

### 1. Write a Specification

Open VS Code with GitHub Copilot and run:

```
/speckit.specify <one-line description of your feature>
```

This creates a `specs/<NNN>-<feature>/spec.md` with user stories, acceptance criteria, and success metrics — no implementation details.

### 2. Clarify Ambiguities

```
/speckit.clarify
```

Reviews the spec for gaps, ambiguous requirements, and untestable criteria. Produces clarification questions and updates the spec.

### 3. Plan the Implementation

```
/speckit.plan
```

Produces `plan.md` with tech stack decisions, file structure, data models (`data-model.md`), API contracts (`contracts/`), and a quickstart guide.

### 4. Generate Tasks

```
/speckit.tasks
```

Creates `tasks.md` — a phased task breakdown with dependencies, parallel markers, and test-first ordering.

### 5. Run Checklists

```
/speckit.checklist
```

Generates quality checklists in `checklists/` and validates spec completeness before implementation begins.

### 6. Implement

```
/speckit.implement
```

Executes the task plan phase by phase: setup, tests, core, integration, polish. Marks tasks complete as it goes.

### 7. Analyze

```
/speckit.analyze
```

Reviews the implementation against the original spec and reports coverage, quality, and any gaps.

## Git Workflow

speckit also manages branching and commits:

- `/speckit.git.feature` — creates a feature branch before specification
- `/speckit.git.commit` — commits changes at each workflow stage
- `/speckit.git.validate` — checks branch state before merging

A typical contribution flow:

```bash
# 1. Start from main
git checkout main && git pull

# 2. Let speckit create your feature branch
/speckit.git.feature

# 3. Run through the workflow
/speckit.specify <description>
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.checklist
/speckit.implement

# 4. Push and open a PR
git push -u origin HEAD
```

## Contributing Profiles

Community profiles don't need the full speckit workflow. Just:

1. Create a profile JSON in `profiles/user/`:

   ```json
   {
     "schema_version": 1,
     "name": "my-character",
     "author": "your-name",
     "description": "What the voice sounds like",
     "effects": [
       {"type": "LivePitchShift", "params": {"semitones": -4.0}},
       {"type": "Reverb", "params": {"room_size": 0.5, "wet_level": 0.3}}
     ]
   }
   ```

2. Verify it loads: `voicechanger profile show my-character`
3. Open a PR adding the file to `profiles/builtin/` if you'd like it included by default

### Profile Naming Rules

- Lowercase alphanumeric + hyphens only: `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$`
- 2–64 characters
- No leading or trailing hyphens
- Must not collide with existing built-in names

### Supported Effect Types

LivePitchShift, PitchShift, Gain, Reverb, Chorus, Distortion, Delay, Compressor, Limiter, NoiseGate, HighpassFilter, LowpassFilter, HighShelfFilter, LowShelfFilter, PeakFilter, LadderFilter, Phaser, Bitcrush, Clipping, Resample, GSMFullRateCompressor, Invert

Unknown effect types are skipped with a warning, so profiles remain forward-compatible.

## Bug Fixes

Small bug fixes can skip the full speckit workflow. Just:

1. Create a branch: `git checkout -b fix/<description>`
2. Write a failing test
3. Fix the bug
4. Confirm all tests pass: `pytest`
5. Lint: `ruff check src/ tests/`
6. Open a PR

## Running Tests

```bash
# Full suite
pytest

# Just unit tests
pytest tests/unit/

# With coverage
pytest --cov=voicechanger
```

## Code Style

- Python 3.11+
- Enforced by ruff (config in `pyproject.toml`)
- Type hints checked by mypy (`mypy src/`)

## Project Structure

```
specs/                  Feature specifications (speckit artifacts)
src/voicechanger/       Python package
tests/                  Unit, contract, and integration tests
profiles/               Built-in and user profile JSON files
native/patches/         C++ patches for Pedalboard
deploy/                 systemd service unit
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
