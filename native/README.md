# Native Patches

## LivePitchShift Patch

### Rationale

Pedalboard's built-in `PitchShift` plugin wraps RubberBand via a `PrimeWithSilence` delay line that adds ~1 second of silence before any audio is returned. This is intentional for sample-accurate offline processing but makes it unusable for real-time voice monitoring where latency must be ≤50 ms.

GitHub issue [spotify/pedalboard#350](https://github.com/spotify/pedalboard/issues/350) — "Very High Latency when using AudioStream with PitchShift on the PedalBoard" — was opened July 2024 and remains open with no upstream fix.

The `LivePitchShift` C++ class extends `RubberbandPlugin` directly, bypassing `PrimeWithSilence`. This reduces latency from ~1000 ms to RubberBand's own algorithmic latency (~2–100 ms depending on buffer configuration). The tradeoff is a short fade-in on the first few buffers — inaudible in a live monitoring context.

### Patch Details

- File: `patches/0001-add-LivePitchShift.patch`
- Scope: Adds a new `LivePitchShift` class alongside the existing `PitchShift` in `PitchShift.h`
- Diffstat: ~80 lines of C++
- Does **not** modify any existing Pedalboard code

### Build Instructions

```bash
# 1. Initialize submodule
git submodule update --init --recursive

# 2. Apply the patch
cd vendor/pedalboard
git apply ../../native/patches/0001-add-LivePitchShift.patch

# 3. Build and install
pip install .

# 4. Return to project root
cd ../..
```

### Cross-Compilation (aarch64)

For Raspberry Pi deployment, use the GitHub Actions workflow `.github/workflows/build-native.yml` which cross-compiles the patched wheel for aarch64.

### Re-evaluation

If Pedalboard upstream closes issue #350 with a native low-latency pitch shift mode, re-evaluate whether this patch is still needed.
