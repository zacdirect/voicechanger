#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# build-pedalboard.sh — Clone pedalboard, apply LivePitchShift patch,
#                        and build a wheel for the current architecture.
#
# Works on both x86_64 (dev) and aarch64 (Raspberry Pi).
#
# Usage:
#   ./scripts/build-pedalboard.sh              # build for this machine
#   ./scripts/build-pedalboard.sh --clean      # wipe build dir first
#
# Output:  build/wheels/pedalboard-*.whl
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PEDALBOARD_TAG="v0.9.22"
PEDALBOARD_REPO="https://github.com/spotify/pedalboard.git"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCH_FILE="$PROJECT_ROOT/native/patches/0001-add-LivePitchShift.patch"
BUILD_DIR="$PROJECT_ROOT/build/pedalboard-src"
WHEEL_DIR="$PROJECT_ROOT/build/wheels"

# ── Helpers ──────────────────────────────────────────────────────────────────

die()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo ">>> $*"; }

# ── Parse args ───────────────────────────────────────────────────────────────

CLEAN=false
INSTALL=false
for arg in "$@"; do
    case "$arg" in
        --clean)   CLEAN=true ;;
        --install) INSTALL=true ;;
    esac
done

if $CLEAN; then
    info "Cleaning build directory"
    rm -rf "$BUILD_DIR"
fi

# ── System deps (Debian/Ubuntu/Raspberry Pi OS) ─────────────────────────────

check_system_deps() {
    local missing=()
    for pkg in build-essential cmake libasound2-dev libxrandr-dev \
               libxcursor-dev libxinerama-dev libx11-dev; do
        if ! dpkg -s "$pkg" &>/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        info "Installing missing system packages: ${missing[*]}"
        sudo apt-get update -qq
        sudo apt-get install -y "${missing[@]}"
    fi
}

check_system_deps

# ── Clone / update source ───────────────────────────────────────────────────

if [[ ! -d "$BUILD_DIR/.git" ]]; then
    info "Cloning pedalboard $PEDALBOARD_TAG"
    mkdir -p "$(dirname "$BUILD_DIR")"
    git clone --branch "$PEDALBOARD_TAG" --depth 1 \
        "$PEDALBOARD_REPO" "$BUILD_DIR"
else
    info "Using existing checkout at $BUILD_DIR"
    cd "$BUILD_DIR"
    git checkout --force "$PEDALBOARD_TAG" 2>/dev/null || true
fi

cd "$BUILD_DIR"

# ── Submodules ───────────────────────────────────────────────────────────────

info "Initialising submodules"

# pybind11 submodule sometimes uses SSH — force HTTPS
git config submodule.vendors/pybind11.url \
    https://github.com/pybind/pybind11.git 2>/dev/null || true

git submodule update --init --recursive --force

# ── Apply patch ──────────────────────────────────────────────────────────────

[[ -f "$PATCH_FILE" ]] || die "Patch not found: $PATCH_FILE"

# Check if already applied
if git apply --check --reverse "$PATCH_FILE" &>/dev/null; then
    info "Patch already applied"
else
    info "Applying LivePitchShift patch"
    git apply "$PATCH_FILE"
fi

# ── Build wheel ──────────────────────────────────────────────────────────────

ARCH="$(uname -m)"
info "Building wheel for $ARCH (this may take several minutes on a Pi)"

# Use the Python from the project venv if it exists, else system python3
if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="python3"
fi

# Ensure build deps
"$PYTHON" -m pip install --quiet "scikit-build-core>=0.5.0" "pybind11>=2.9.0" build

mkdir -p "$WHEEL_DIR"
"$PYTHON" -m build --wheel --outdir "$WHEEL_DIR" "$BUILD_DIR"

info "Wheel(s) written to $WHEEL_DIR:"
ls -1 "$WHEEL_DIR"/pedalboard-*.whl

# ── Install ──────────────────────────────────────────────────────────────────

if $INSTALL; then
    info "Installing patched pedalboard into venv"
    "$PYTHON" -m pip install --force-reinstall --no-deps "$WHEEL_DIR"/pedalboard-*.whl
    info "Installed.  Verify with:"
    info "  $PYTHON -c \"import pedalboard as pb; print(hasattr(pb, 'LivePitchShift'))\""
else
    echo ""
    info "Architecture: $ARCH"
    info "Done.  Install with:"
    info "  pip install --force-reinstall --no-deps $WHEEL_DIR/pedalboard-*.whl"
    info "Or re-run with --install to auto-install."
fi
