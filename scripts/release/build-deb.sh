#!/bin/bash
# Build Debian package for voicechanger.
#
# Bundles the voicechanger wheel, the patched pedalboard wheel, the systemd
# service unit, and post-install / pre-remove scripts into a single .deb.
#
# Prerequisites: fpm (installed by the CI workflow), wheels already in dist/.
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

# Short Python tag for filenames (e.g. "3.12" -> "py312")
PYTAG="py${PYVER//./}"

# ── Map to Debian architecture names ──
case "$ARCH" in
  x86_64)  DEB_ARCH="amd64" ;;
  aarch64) DEB_ARCH="arm64" ;;
  *)       echo "ERROR: unsupported arch: $ARCH (supported: x86_64, aarch64)" >&2; exit 1 ;;
esac

# ── Verify wheels exist ──
VC_WHEEL=$(find "$DIST" -maxdepth 1 -name 'voicechanger-*.whl' | head -1)
PB_WHEEL=$(find "$DIST" -maxdepth 1 -name 'pedalboard-*.whl' | head -1)

if [[ -z "$VC_WHEEL" ]]; then
  echo "ERROR: voicechanger wheel not found in $DIST" >&2; exit 1
fi
if [[ -z "$PB_WHEEL" ]]; then
  echo "WARNING: pedalboard wheel not found — .deb will not include it" >&2
fi

VERSION=$(echo "$(basename "$VC_WHEEL")" | cut -d'-' -f2)
echo "Building .deb  arch=$DEB_ARCH  version=$VERSION  python=$PYVER"

# ── Stage files ──
rm -rf "$STAGE"
mkdir -p "$STAGE/opt/voicechanger/wheels"
mkdir -p "$STAGE/etc/systemd/system"
mkdir -p "$STAGE/usr/local/bin"

# Bundle ALL wheels (voicechanger + pedalboard + transitive deps like numpy, flet, sounddevice)
cp "$DIST"/*.whl "$STAGE/opt/voicechanger/wheels/"

# Systemd unit
cp "$PROJECT_ROOT/deploy/voicechanger.service" "$STAGE/etc/systemd/system/"

# Wrapper scripts (installed to PATH)
cat > "$STAGE/usr/local/bin/voicechanger" <<'WRAPPER'
#!/bin/bash
exec /opt/voicechanger/venv/bin/python -m voicechanger "$@"
WRAPPER
chmod 755 "$STAGE/usr/local/bin/voicechanger"

cat > "$STAGE/usr/local/bin/voicechanger-gui" <<'WRAPPER'
#!/bin/bash
exec /opt/voicechanger/venv/bin/python -m voicechanger gui "$@"
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
  --depends "python3 (>= $PYVER)" \
  --depends "python3-venv" \
  --depends "libsndfile1" \
  --depends "libasound2" \
  --conflicts "voicechanger-py312" \
  --conflicts "voicechanger-py314" \
  --after-install "$PROJECT_ROOT/scripts/release/post-install.sh" \
  --before-remove "$PROJECT_ROOT/scripts/release/pre-remove.sh" \
  --package "$DIST/voicechanger_${VERSION}_${PYTAG}_${DEB_ARCH}.deb" \
  -C "$STAGE" \
  .

echo ""
echo "✅ .deb built:"
ls -lh "$DIST"/*.deb
