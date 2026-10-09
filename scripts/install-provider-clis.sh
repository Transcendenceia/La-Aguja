#!/bin/bash
# Install required provider clients into an isolated personal image, never the host.
# This operation does not read profiles, start agents, or authenticate a provider.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT=${AGUJA_ROOT:-$PROJECT/build/rootfs}
[[ $EUID == 0 && -f "$ROOT/etc/debian_version" && $(realpath "$ROOT") != / ]] || { echo 'Rootfs Debian aislada requerida'; exit 1; }
STAGE=$(mktemp -d "$PROJECT/build/provider-clis.XXXXXX")
trap 'rm -rf -- "$STAGE"' EXIT
for provider in antigravity claude_native; do
    url=$(jq -er --arg name "$provider" '.[$name].url' "$PROJECT/config/harnesses.json")
    hash=$(jq -er --arg name "$provider" '.[$name].sha512' "$PROJECT/config/harnesses.json")
    [[ $url == https://* && $hash =~ ^[a-f0-9]{128}$ ]] || { echo 'Lock de CLI inválido'; exit 1; }
    curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 --connect-timeout 20 "$url" -o "$STAGE/$provider.tgz"
    printf '%s  %s\n' "$hash" "$STAGE/$provider.tgz" | sha512sum -c -
done
mkdir -p "$STAGE/claude" "$STAGE/agy"
tar -xzf "$STAGE/claude_native.tgz" -C "$STAGE/claude" package/claude package/package.json package/LICENSE.md package/README.md
tar -xzf "$STAGE/antigravity.tgz" -C "$STAGE/agy" antigravity
install -d "$ROOT/opt/aguja/agents/claude" "$ROOT/opt/aguja/agents/antigravity" "$ROOT/usr/local/bin"
install -m 755 "$STAGE/claude/package/claude" "$ROOT/opt/aguja/agents/claude/claude"
install -m 644 "$STAGE/claude/package/package.json" "$ROOT/opt/aguja/agents/claude/package.json"
install -m 644 "$STAGE/claude/package/LICENSE.md" "$STAGE/claude/package/README.md" "$ROOT/opt/aguja/agents/claude/"
install -m 755 "$STAGE/agy/antigravity" "$ROOT/opt/aguja/agents/antigravity/agy"
ln -sfn /opt/aguja/agents/claude/claude "$ROOT/usr/local/bin/claude"
ln -sfn /opt/aguja/agents/antigravity/agy "$ROOT/usr/local/bin/agy"
printf 'Provider-owned client; see https://github.com/anthropics/claude-code/blob/main/LICENSE.md\n' > "$ROOT/opt/aguja/agents/claude/NOTICE"
printf 'Provider-owned client; see https://antigravity.google/terms\n' > "$ROOT/opt/aguja/agents/antigravity/NOTICE"
echo 'Claude y Antigravity instalados; no se ha iniciado sesión.'
