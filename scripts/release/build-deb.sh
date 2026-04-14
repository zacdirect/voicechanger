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
