#!/bin/bash
# Verify all four executable clients with an empty, disposable HOME and no credentials.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT=${AGUJA_ROOT:-$PROJECT/build/rootfs}
[[ $EUID == 0 && -f "$ROOT/etc/debian_version" && $(realpath "$ROOT") != / ]] || { echo 'Rootfs Debian aislada requerida'; exit 1; }
# Never introduce rootfs mounts into the host/service namespaces.
if [[ ${AGUJA_VERIFY_NAMESPACE:-0} != 1 ]]; then
    exec unshare --mount --pid --fork --propagation private /usr/bin/env AGUJA_VERIFY_NAMESPACE=1 AGUJA_PROJECT="$PROJECT" AGUJA_ROOT="$ROOT" bash "$0"
fi
mount --make-rprivate /
VERIFY_HOME=$(mktemp -d "$ROOT/tmp/aguja-cli-check.XXXXXX")
OWN_MOUNTS=()
cleanup() {
    for ((i=${#OWN_MOUNTS[@]}-1; i>=0; i--)); do umount -R "$ROOT/${OWN_MOUNTS[i]}"; done
    rm -rf -- "$VERIFY_HOME"
}
trap cleanup EXIT
# Native clients require a normal Linux /dev (random/null/PTY) as well as proc.
# Bind only in this isolated rootfs; never pack host mounts or detach foreign ones.
if mountpoint -q "$ROOT/dev" || mountpoint -q "$ROOT/proc"; then echo 'Raíz con montajes ajenos; usa una copia limpia'; exit 1; fi
mount -t tmpfs -o mode=755,nosuid tmpfs "$ROOT/dev";OWN_MOUNTS+=(dev)
for name in null zero random urandom; do
    touch "$ROOT/dev/$name";mount --bind "/dev/$name" "$ROOT/dev/$name"
done
python3 - "$ROOT" "$PROJECT/config/harnesses.json" <<'PYCODEX'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);expected=json.loads(Path(sys.argv[2]).read_text())['codex']
metadata=json.loads((root/'opt/aguja/agents/codex/package.json').read_text())
assert metadata.get('name')=='@openai/codex' and metadata.get('version')==expected,'Codex executable/package mismatch'
PYCODEX
mount -t proc proc "$ROOT/proc";OWN_MOUNTS+=(proc)

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
