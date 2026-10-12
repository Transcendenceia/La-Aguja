#!/bin/bash
# Verify all four executable clients with an empty, disposable HOME and no credentials.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT=${AGUJA_ROOT:-$PROJECT/build/rootfs}
[[ $EUID == 0 && -f "$ROOT/etc/debian_version" && $(realpath "$ROOT") != / ]] || { echo 'Rootfs Debian aislada requerida'; exit 1; }
VERIFY_HOME=$(mktemp -d "$ROOT/tmp/aguja-cli-check.XXXXXX")
OWN_MOUNTS=()
cleanup() {
    for ((i=${#OWN_MOUNTS[@]}-1; i>=0; i--)); do umount -R "$ROOT/${OWN_MOUNTS[i]}"; done
    rm -rf -- "$VERIFY_HOME"
}
trap cleanup EXIT
# Native clients require a normal Linux /dev (random/null/PTY) as well as proc.
# Bind only in this isolated rootfs; never pack host mounts or detach foreign ones.
for virtual in dev proc sys; do
    if ! mountpoint -q "$ROOT/$virtual"; then
        mount --rbind "/$virtual" "$ROOT/$virtual"
        mount --make-rslave "$ROOT/$virtual"
        OWN_MOUNTS+=("$virtual")
    fi
done
chown "$(chroot "$ROOT" id -u aguja):$(chroot "$ROOT" id -g aguja)" "$VERIFY_HOME"
for binary in codex agy claude opencode; do
    version=$(timeout 45 chroot "$ROOT" /usr/bin/env -i HOME="${VERIFY_HOME#"$ROOT"}" PATH=/usr/local/bin:/usr/bin:/bin TERM=dumb \
        /usr/sbin/runuser -u aguja -- "/usr/local/bin/$binary" --version)
    case "$binary" in
        codex) expected="codex-cli $(jq -er .codex "$PROJECT/config/harnesses.json")" ;;
        agy) expected=$(jq -er .antigravity.version "$PROJECT/config/harnesses.json") ;;
        claude) expected="$(jq -er .claude "$PROJECT/config/harnesses.json") (Claude Code)" ;;
        opencode) expected=$(jq -er .opencode "$PROJECT/config/harnesses.json") ;;
    esac
    [[ $version == "$expected" ]] || { echo "CLI no coincide con su versión bloqueada: $binary"; exit 1; }
    printf '%s\n' "$version"
done
