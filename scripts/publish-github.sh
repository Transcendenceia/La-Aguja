#!/usr/bin/env bash
# Run only for an reviewed release; never force-push or replace published assets.
set -euo pipefail
cd "$(dirname "$0")/.."
ASSETS=$(realpath "${1:?Uso: scripts/publish-github.sh DIRECTORIO_ASSETS}")
VERSION=$(cat VERSION)
REPOSITORY=Transcendenceia/La-Aguja
TAG="v$VERSION"
python3 scripts/audit-public.py
[[ -z $(git status --porcelain) ]] || { echo 'Primero confirma el código revisado en Git.'; exit 1; }
node - "$ASSETS" "$VERSION" <<'JS'
const fs=require('node:fs'),path=require('node:path');const [folder,v]=process.argv.slice(2);
const fixed=new Set(['catalog.json','SHA256SUMS','packages.tsv','harnesses.json','third-party-sources.tsv','imager-dependencies.json','NOTICE.md','LICENSE',`SHA256SUMS-imager-${v}-windows`,`SHA256SUMS-imager-${v}-linux`,`La-Aguja-${v}-source.tar.gz`,`LA-AGUJA-Manual-usuarios-${v}.pdf`]);
for(const name of fs.readdirSync(folder)){
 const file=path.join(folder,name),stat=fs.lstatSync(file);
 const image=name===`aguja-${v}-amd64.iso`||name===`aguja-${v}-amd64.img.zst`||name.startsWith(`aguja-${v}-amd64.img.part`)&&name===`aguja-${v}-amd64.img.part${name.slice(-2)}`&&/^\d{2}$/.test(name.slice(-2));
 const imager=[`aguja-flash-imager-${v}-win-x64.exe`,`aguja-flash-imager-${v}-x86_64.AppImage`,`aguja-flash-imager-${v}-amd64.deb`,`aguja-flash-imager-${v}-linux-x64.tar.gz`].includes(name);
 if(!(fixed.has(name)||image||imager)||!stat.isFile()||stat.isSymbolicLink()||stat.size>=2*1024**3)throw Error('Asset no publicable: '+name);
}
for(const name of ['catalog.json','SHA256SUMS',`aguja-${v}-amd64.img.zst`,`aguja-${v}-amd64.iso`,`aguja-flash-imager-${v}-win-x64.exe`])if(!fs.existsSync(path.join(folder,name)))throw Error('Asset requerido ausente: '+name);
const root=process.cwd();require(root+'/desktop/core.cjs').verifyManifest(JSON.parse(fs.readFileSync(path.join(folder,'catalog.json'))),JSON.parse(fs.readFileSync(root+'/desktop/resources/release-key.json')));
JS
(cd "$ASSETS" && sha256sum --ignore-missing -c SHA256SUMS)
# gh uses its configured broker; never paste tokens or enable shell tracing.
gh api user --jq .login >/dev/null
OWNER_KIND=$(gh api "users/${REPOSITORY%/*}" --jq .type)
if [[ $OWNER_KIND == User ]]; then
 [[ $(gh api user --jq .login | tr '[:upper:]' '[:lower:]') == transcendenceia ]] || { echo 'La credencial no es del propietario seleccionado.'; exit 1; }
fi
# Fail closed on unexpected API/network errors; create only after an actual 404.
if ! gh repo view "$REPOSITORY" --json nameWithOwner >/dev/null 2>&1; then
 response=$(gh api -i "repos/$REPOSITORY" 2>&1 || true)
 [[ $response == *'404'* ]] || { echo 'No se pudo comprobar el destino GitHub; no se crea otro repositorio.'; exit 1; }
 gh repo create "$REPOSITORY" --public --description 'Rescue Disk Linux y Flash Imager abiertos; descargas sin cuentas, SSH por tu LAN/Tailscale/Headscale.' --homepage https://aguja.transcendenceia.net
fi
[[ $(gh repo view "$REPOSITORY" --json visibility --jq .visibility) == PUBLIC ]] || { echo 'El destino existente no es público; revisar antes de cambiar su acceso.'; exit 1; }
git push -u origin main
if ! git rev-parse "$TAG" >/dev/null 2>&1; then git tag "$TAG"; fi
git push origin "$TAG"
if ! gh release view "$TAG" --repo "$REPOSITORY" >/dev/null 2>&1; then
 gh release create "$TAG" --repo "$REPOSITORY" --draft --title "LA AGUJA $VERSION · Open source" --notes-file docs/RELEASE-0.9.0.md
fi
[[ $(gh release view "$TAG" --repo "$REPOSITORY" --json isDraft --jq .isDraft) == true ]] || { echo 'La release ya está publicada; no se reemplazan assets.'; exit 1; }
gh release upload "$TAG" "$ASSETS"/* --repo "$REPOSITORY"
echo 'Release borrador cargada. Comparar assets remotos, publicar la release y después activar la web informativa.'
