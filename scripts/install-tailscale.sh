#!/bin/bash
# Build-time only: fixed official archive, pinned SHA-256, isolated destination.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT=${AGUJA_ROOT:-$PROJECT/build/rootfs}
[[ $EUID == 0 && -f "$ROOT/etc/debian_version" && $(realpath "$ROOT") != / ]] || { echo 'Rootfs Debian aislada requerida'; exit 1; }
VERSION=$(jq -r .version "$PROJECT/config/tailscale.json")
HASH=$(jq -r .sha256 "$PROJECT/config/tailscale.json")
URL=$(jq -r .url "$PROJECT/config/tailscale.json")
[[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && $HASH =~ ^[0-9a-f]{64}$ && $URL == "https://pkgs.tailscale.com/stable/tailscale_${VERSION}_amd64.tgz" ]] || { echo 'Lock de Tailscale no válido'; exit 1; }
mkdir -p "$PROJECT/build/downloads"
ARCHIVE="$PROJECT/build/downloads/tailscale_${VERSION}_amd64.tgz"
if ! printf '%s  %s\n' "$HASH" "$ARCHIVE" | sha256sum -c - >/dev/null 2>&1; then
    TEMP=$(mktemp "$PROJECT/build/downloads/.tailscale-XXXXXX")
    trap 'rm -f "$TEMP"' EXIT
    curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 "$URL" -o "$TEMP"
    printf '%s  %s\n' "$HASH" "$TEMP" | sha256sum -c -
    mv "$TEMP" "$ARCHIVE"
    trap - EXIT
fi
WORK=$(mktemp -d "$PROJECT/build/.tailscale-XXXXXX")
trap 'rm -rf "$WORK"' EXIT
PREFIX="tailscale_${VERSION}_amd64"
tar --extract --gzip --file "$ARCHIVE" --directory "$WORK" --no-same-owner \
    "$PREFIX/tailscale" "$PREFIX/tailscaled"
install -d "$ROOT/usr/bin" "$ROOT/usr/sbin" "$ROOT/usr/share/aguja"
install -m 755 "$WORK/$PREFIX/tailscale" "$ROOT/usr/bin/tailscale"
install -m 755 "$WORK/$PREFIX/tailscaled" "$ROOT/usr/sbin/tailscaled"
install -m 644 "$PROJECT/licenses/Tailscale-BSD-3-Clause.txt" "$ROOT/usr/share/aguja/tailscale-LICENSE"
install -m 644 "$PROJECT/config/tailscale.json" "$ROOT/usr/share/aguja/tailscale-lock.json"
"$ROOT/usr/bin/tailscale" version | head -1 | grep -Fx "$VERSION"
echo "Tailscale $VERSION verificado e incluido; el arranque no instala paquetes."
