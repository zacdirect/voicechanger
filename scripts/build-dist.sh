#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# build-dist.sh — Build a self-contained dist/ directory for deployment.
#
# Contents of dist/:
#   wheels/          (pedalboard + other deps as .whl files)
#   install.sh       (on-target setup: venv + pip install from wheels/)
#   run.sh           (launch wrapper)
#   profiles/        (built-in profile JSONs)
#   voicechanger.toml
#
# Usage:
#   ./scripts/build-dist.sh                    # x86_64 (local dev/test)
#   ./scripts/build-dist.sh --pi               # cross-downloads aarch64 wheels
#   PYTHON_VERSION=3.11 ./scripts/build-dist.sh --pi
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
WHEEL_DIR="$DIST_DIR/wheels"
BUILD_WHEELS="$PROJECT_ROOT/build/wheels"

# Default Python version for Pi wheel downloads
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
PI_PLATFORM="manylinux2014_aarch64"

# ── Parse args ───────────────────────────────────────────────────────────────

TARGET="local"
if [[ "${1:-}" == "--pi" ]]; then
    TARGET="pi"
fi

die()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo ">>> $*"; }

# ── Pick Python ──────────────────────────────────────────────────────────────

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="python3"
fi

# ── Prepare dist tree ───────────────────────────────────────────────────────

info "Building dist for target: $TARGET"
rm -rf "$DIST_DIR"
mkdir -p "$WHEEL_DIR"

# ── Build the project wheel ─────────────────────────────────────────────────

info "Building voicechanger wheel"
"$PYTHON" -m pip install --quiet build
"$PYTHON" -m build --wheel --outdir "$WHEEL_DIR" "$PROJECT_ROOT"

# ── Runtime data ─────────────────────────────────────────────────────────────

cp -r "$PROJECT_ROOT/profiles" "$DIST_DIR/"
cp "$PROJECT_ROOT/voicechanger.toml" "$DIST_DIR/" 2>/dev/null || true

# Copy systemd unit for Pi deployment
if [[ "$TARGET" == "pi" ]]; then
    mkdir -p "$DIST_DIR/deploy"
    cp "$PROJECT_ROOT/deploy/voicechanger.service" "$DIST_DIR/deploy/" 2>/dev/null || true
fi

# ── Pedalboard wheel (patched) ───────────────────────────────────────────────

if [[ "$TARGET" == "pi" ]]; then
    # For Pi: we need an aarch64 wheel.
    if ls "$BUILD_WHEELS"/pedalboard-*aarch64*.whl &>/dev/null; then
        info "Copying pre-built aarch64 pedalboard wheel"
        cp "$BUILD_WHEELS"/pedalboard-*aarch64*.whl "$WHEEL_DIR/"
    else
        info "NOTE: No aarch64 pedalboard wheel found in build/wheels/."
        info "      Build on the Pi first:  ./scripts/build-pedalboard.sh"
        info "      Then copy the wheel to build/wheels/ and re-run."
        info "      Continuing without patched pedalboard wheel..."
    fi
else
    # Local: grab whatever arch we have
    if ls "$BUILD_WHEELS"/pedalboard-*.whl &>/dev/null; then
        info "Copying local pedalboard wheel"
        cp "$BUILD_WHEELS"/pedalboard-*.whl "$WHEEL_DIR/"
    else
        info "No patched pedalboard wheel found.  Run scripts/build-pedalboard.sh first."
        info "Continuing — install.sh will fall back to PyPI pedalboard (no LivePitchShift)."
    fi
fi

# ── Download other dependency wheels ─────────────────────────────────────────

info "Downloading dependency wheels"

PIP_DOWNLOAD_ARGS=(
    --dest "$WHEEL_DIR"
    --only-binary :all:
)

if [[ "$TARGET" == "pi" ]]; then
    PIP_DOWNLOAD_ARGS+=(
        --platform "$PI_PLATFORM"
        --python-version "$PYTHON_VERSION"
        --implementation cp
        --abi "cp${PYTHON_VERSION//./}"
    )
fi

for dep in numpy sounddevice; do
    "$PYTHON" -m pip download "${PIP_DOWNLOAD_ARGS[@]}" "$dep" 2>&1 | tail -3
done

# ── install.sh (runs on the target) ─────────────────────────────────────────

cat > "$DIST_DIR/install.sh" << 'INSTALL_EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

echo ">>> Creating virtualenv"
python3 -m venv "$VENV"

echo ">>> Installing wheels (offline)"
"$VENV/bin/pip" install --upgrade pip --quiet

# Install patched pedalboard wheel first if present
if ls "$SCRIPT_DIR"/wheels/pedalboard-*.whl &>/dev/null; then
    "$VENV/bin/pip" install "$SCRIPT_DIR"/wheels/pedalboard-*.whl
else
    echo "WARNING: No patched pedalboard wheel — installing from PyPI."
    echo "         LivePitchShift will not be available."
    "$VENV/bin/pip" install pedalboard
fi

# Install voicechanger + remaining deps from bundled wheels, fall back to PyPI
"$VENV/bin/pip" install --no-index --find-links "$SCRIPT_DIR/wheels" \
    "$SCRIPT_DIR"/wheels/voicechanger-*.whl 2>/dev/null \
    || "$VENV/bin/pip" install "$SCRIPT_DIR"/wheels/voicechanger-*.whl

echo ""
echo ">>> Install complete.  Run with:"
echo "    $SCRIPT_DIR/run.sh"
echo "    $SCRIPT_DIR/run.sh serve"
echo "    $SCRIPT_DIR/run.sh gui"
INSTALL_EOF

chmod +x "$DIST_DIR/install.sh"

# ── run.sh (runs on the target) ─────────────────────────────────────────────

cat > "$DIST_DIR/run.sh" << 'RUN_EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [[ ! -x "$VENV/bin/python" ]]; then
    echo "Run install.sh first." >&2
    exit 1
fi

exec "$VENV/bin/voicechanger" "$@"
RUN_EOF

chmod +x "$DIST_DIR/run.sh"

# ── Summary ──────────────────────────────────────────────────────────────────

info "dist/ contents:"
find "$DIST_DIR" -type f | sort | sed "s|$PROJECT_ROOT/||"

WHEEL_COUNT=$(ls "$WHEEL_DIR"/*.whl 2>/dev/null | wc -l)
DIST_SIZE=$(du -sh "$DIST_DIR" | cut -f1)

echo ""
info "Total: $WHEEL_COUNT wheel(s), $DIST_SIZE"
echo ""
if [[ "$TARGET" == "pi" ]]; then
    info "Deploy to Pi:"
    info "  scp -r dist/ pi@<pi-host>:~/voicechanger/"
    info "  ssh pi@<pi-host> 'cd ~/voicechanger && ./install.sh'"
else
    info "Local test:"
    info "  cd dist && ./install.sh && ./run.sh"
fi
