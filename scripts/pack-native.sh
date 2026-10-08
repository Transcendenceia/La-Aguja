#!/bin/bash
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT="$PROJECT/build/rootfs"
ARCHIVE=$(mktemp -d "$PROJECT/build/npm-install.XXXXXX")
mv "$ROOT/usr/local/lib/node_modules" "$ARCHIVE/"
MODULES="$ARCHIVE/node_modules"
AGENTS="$ROOT/opt/aguja/agents"
mkdir -p "$AGENTS"/{codex,opencode}
cp -a "$MODULES/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/." "$AGENTS/codex/"
# Baseline build avoids imposing AVX2 on old rescue targets.
cp -a "$MODULES/opencode-ai/node_modules/opencode-linux-x64-baseline/bin/opencode" "$AGENTS/opencode/opencode"
for pair in 'codex @openai/codex' 'opencode opencode-ai'; do
    read -r name module <<< "$pair"
    for notice in LICENSE LICENSE.md README.md package.json; do
        if [[ -f "$MODULES/$module/$notice" ]]; then cp "$MODULES/$module/$notice" "$AGENTS/$name/$notice"; fi
    done
done
install -m 644 "$PROJECT/licenses/Codex-Apache-2.0.txt" "$AGENTS/codex/LICENSE"
ln -sf /opt/aguja/agents/codex/x86_64-unknown-linux-musl/bin/codex "$ROOT/usr/local/bin/codex"
ln -sf /opt/aguja/agents/opencode/opencode "$ROOT/usr/local/bin/opencode"
mv "$ROOT/usr/local/bin/node" "$ARCHIVE/node"
echo 'Binarios nativos empaquetados; cachés y variantes permanecen fuera del sistema live.'
