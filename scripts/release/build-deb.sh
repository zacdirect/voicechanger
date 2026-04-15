#!/bin/bash
# Build Debian package for voicechanger.
#
# Bundles pre-installed Python packages, the systemd service unit,
# and post-install / pre-remove scripts into a single .deb.
# No pip or venv is needed on the target system.
#
# Prerequisites: fpm (installed by the CI workflow),
#                dist/lib/ populated by `pip install --target`.
#
# Usage:
#   ./build-deb.sh <arch> <python-version>
#
# Example:
#   ./build-deb.sh aarch64 3.12

set -euo pipefail

ARCH="${1:?Usage: build-deb.sh <arch> <python-version>}"
PYVER="${2:?Usage: build-deb.sh <arch> <python-version>}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="$PROJECT_ROOT/dist"
STAGE="$PROJECT_ROOT/dist/deb-staging"
LIB="$DIST/lib"

# Short Python tag for filenames (e.g. "3.12" -> "py312")
PYTAG="py${PYVER//./}"

# ── Map to Debian architecture names ──
case "$ARCH" in
  x86_64)  DEB_ARCH="amd64" ;;
  aarch64) DEB_ARCH="arm64" ;;
  *)       echo "ERROR: unsupported arch: $ARCH (supported: x86_64, aarch64)" >&2; exit 1 ;;
esac

# ── Verify pre-installed lib exists ──
if [[ ! -d "$LIB" ]]; then
  echo "ERROR: pre-installed lib directory not found at $LIB" >&2; exit 1
fi
if [[ ! -d "$LIB/voicechanger" ]]; then
  echo "ERROR: voicechanger package not found in $LIB" >&2; exit 1
fi

# Extract version from the installed package metadata
VERSION=$(python3 -c "
from pathlib import Path
for d in Path('$LIB').glob('voicechanger-*.dist-info'):
    for line in (d / 'METADATA').read_text().splitlines():
        if line.startswith('Version:'):
            print(line.split(': ',1)[1]); break
")
echo "Building .deb  arch=$DEB_ARCH  version=$VERSION  python=$PYVER"

# ── Stage files ──
rm -rf "$STAGE"
mkdir -p "$STAGE/opt/voicechanger"
mkdir -p "$STAGE/etc/systemd/system"
mkdir -p "$STAGE/usr/local/bin"

# Pre-installed Python packages (the entire lib tree)
cp -a "$LIB" "$STAGE/opt/voicechanger/lib"

# flet 0.84 checks for flet-web at import time even when not using web mode.
# flet-web has no aarch64 wheel and needs fastapi/etc we don't want to ship.
# Bundle a minimal stub that satisfies the version check only.
FLET_VERSION=$(python3 -c "
from pathlib import Path
for d in Path('$LIB').glob('flet-*.dist-info'):
    for line in (d / 'METADATA').read_text().splitlines():
        if line.startswith('Version:'):
            print(line.split(': ',1)[1]); break
" 2>/dev/null || echo "0.84.0")
if [[ "$ARCH" == "aarch64" ]]; then
  # ── aarch64 (Raspberry Pi): web mode ──
  # Pi 3's VideoCore IV GPU only supports OpenGL 2.1 / ES 2.0.  Flutter's Skia
  # backend requires GL 3.3+, so the native flet-desktop binary crashes.  Ship
  # the real flet-web package + fastapi/uvicorn to serve the UI in a browser.
  pip install --target "$STAGE/opt/voicechanger/lib" \
      "flet-web==$FLET_VERSION" --no-deps --quiet
  pip install --target "$STAGE/opt/voicechanger/lib" \
      "fastapi>=0.115" "uvicorn[standard]>=0.35" --quiet
  echo "Installed flet-web + fastapi + uvicorn for aarch64 web mode"

  # Download and extract the pre-built Flutter web runtime bundle.
  FLET_WEB_TARBALL="$DIST/flet-web.tar.gz"
  FLET_WEB_URL="https://github.com/flet-dev/flet/releases/download/v${FLET_VERSION}/flet-web.tar.gz"
  echo "Downloading Flutter web bundle from $FLET_WEB_URL"
  curl -sL -o "$FLET_WEB_TARBALL" "$FLET_WEB_URL"
  mkdir -p "$STAGE/opt/voicechanger/lib/flet_web/web"
  tar xzf "$FLET_WEB_TARBALL" -C "$STAGE/opt/voicechanger/lib/flet_web/web"
  echo "Extracted Flutter web bundle ($(du -sh "$STAGE/opt/voicechanger/lib/flet_web/web" | cut -f1))"

  # Still need flet-desktop as a stub — flet core imports it at startup.
  pip install --target "$STAGE/opt/voicechanger/lib" \
      "flet-desktop==$FLET_VERSION" --no-deps --quiet
  echo "Installed flet-desktop $FLET_VERSION (stub for import)"
else
  # ── x86_64: native desktop mode ──
  # flet-web stub satisfies the import check without pulling in fastapi/uvicorn.
  mkdir -p "$STAGE/opt/voicechanger/lib/flet_web"
  printf '' > "$STAGE/opt/voicechanger/lib/flet_web/__init__.py"
  printf 'version = "%s"\n' "$FLET_VERSION" > "$STAGE/opt/voicechanger/lib/flet_web/version.py"
  echo "Bundled flet_web stub version=$FLET_VERSION"

  # flet-desktop is needed for the native GUI window.
  pip install --target "$STAGE/opt/voicechanger/lib" \
      "flet-desktop==$FLET_VERSION" --no-deps --quiet
  echo "Installed flet-desktop $FLET_VERSION"
fi

# Built-in profiles
cp -a "$PROJECT_ROOT/profiles" "$STAGE/opt/voicechanger/profiles"

# Built-in hardware hints
cp -a "$PROJECT_ROOT/hardware" "$STAGE/opt/voicechanger/hardware"

# Systemd unit
cp "$PROJECT_ROOT/deploy/voicechanger.service" "$STAGE/etc/systemd/system/"

# Wrapper scripts — use PYTHONPATH, no venv needed
cat > "$STAGE/usr/local/bin/voicechanger" <<WRAPPER
#!/bin/bash
export PYTHONPATH=/opt/voicechanger/lib
exec python${PYVER} -m voicechanger "\$@"
WRAPPER
chmod 755 "$STAGE/usr/local/bin/voicechanger"

cat > "$STAGE/usr/local/bin/voicechanger-gui" <<WRAPPER
#!/bin/bash
export PYTHONPATH=/opt/voicechanger/lib
exec python${PYVER} -m voicechanger gui "\$@"
WRAPPER
chmod 755 "$STAGE/usr/local/bin/voicechanger-gui"

# ── Build .deb with fpm ──
fpm \
  -s dir \
  -t deb \
  -n "voicechanger-${PYTAG}" \
  -v "$VERSION" \
  -a "$DEB_ARCH" \
  --description "Real-time voice changer for Raspberry Pi using Pedalboard (Python $PYVER)" \
  --url "https://github.com/zac/voicechanger" \
  --license "MIT" \
  --depends "python${PYVER}" \
  --depends "libsndfile1" \
  --depends "libasound2" \
  --depends "pipewire-alsa" \
  --conflicts "voicechanger-py312" \
  --conflicts "voicechanger-py313" \
  --conflicts "voicechanger-py314" \
  --after-install "$PROJECT_ROOT/scripts/release/post-install.sh" \
  --before-remove "$PROJECT_ROOT/scripts/release/pre-remove.sh" \
  --package "$DIST/voicechanger_${VERSION}_${PYTAG}_${DEB_ARCH}.deb" \
  -C "$STAGE" \
  .

echo ""
echo "✅ .deb built:"
ls -lh "$DIST"/*.deb
