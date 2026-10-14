#!/usr/bin/env python3
"""Build a portable Agent Skills bundle from an explicit source allowlist."""
import gzip
import hashlib
import io
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
skill_text = (ROOT/'skills/flash-imager/SKILL.md').read_text()
version_match = re.search(r'^  version: "(\d+\.\d+\.\d+)"$', skill_text, re.MULTILINE)
if not version_match:
    raise ValueError('Missing skill metadata.version')
VERSION = version_match.group(1)

def build(output):
    cli_text = (ROOT/'skills/flash-imager/scripts/imager.cjs').read_text()
    cli_match = re.search(r"^const VERSION = '([^']+)';$", cli_text, re.MULTILINE)
    if not cli_match or cli_match.group(1) != VERSION:
        raise ValueError('CLI version differs from skill metadata.version')
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    def add(source, destination):
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing or unsafe bundle source: ' + str(source.relative_to(ROOT)))
        files['flash-imager/' + destination] = source.read_bytes()
    for name in ['SKILL.md','references/interface.md','references/harnesses.md','assets/request.example.json','scripts/imager.cjs','references/recovery.md']:
        add(ROOT/'skills/flash-imager'/name, name)
    for name in ['core.cjs','image-storage.cjs','provisioning.cjs','fat32-writer.cjs','public-download.cjs','resources/release-key.json','disk-recovery.cjs','reusable-profile.cjs','package.json']:
        add(ROOT/'desktop'/name, 'scripts/lib/desktop/' + name)
    add(ROOT/'runtime/recovery_keys.py', 'scripts/lib/runtime/recovery_keys.py')
    add(ROOT/'runtime/locale-catalog.json', 'scripts/lib/runtime/locale-catalog.json')
    add(ROOT/'LICENSE', 'LICENSE')
    add(ROOT/'NOTICE.md', 'NOTICE.md')
    # Pure JS, pinned existing Imager dependency; include its license, no Electron.
    dependency = ROOT/'desktop/node_modules/@iarna/toml'
    package = json.loads((dependency/'package.json').read_text())
    lock = json.loads((ROOT/'desktop/package-lock.json').read_text())
    if package['version'] != lock['packages']['node_modules/@iarna/toml']['version']:
        raise ValueError('Dependency version differs from Imager lockfile')
    for source in sorted(dependency.rglob('*')):
        if source.is_file():
            add(source, 'scripts/lib/desktop/node_modules/@iarna/toml/' + source.relative_to(dependency).as_posix())
    jsonc = ROOT/'desktop/node_modules/jsonc-parser'
    jsonc_package = json.loads((jsonc/'package.json').read_text())
    if jsonc_package['version'] != lock['packages']['node_modules/jsonc-parser']['version']:
        raise ValueError('JSONC dependency differs from Imager lockfile')
    for source in sorted(jsonc.rglob('*')):
        if source.is_file():
            add(source, 'scripts/lib/desktop/node_modules/jsonc-parser/' + source.relative_to(jsonc).as_posix())
    manifest = {'skill_version':VERSION,'engine':'Flash Imager','imager_version':json.loads((ROOT/'desktop/package.json').read_text())['version'],
                'dependency':{'name':'@iarna/toml','version':package['version'],'integrity':lock['packages']['node_modules/@iarna/toml']['integrity']},
                'files':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}}
    files['flash-imager/BUNDLE-MANIFEST.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    base = 'aguja-flash-imager-skill-' + VERSION
    archives = [output/(base+'.zip'), output/(base+'.tar.gz')]
    # Fixed timestamps and order make repeated bundles byte-identical.
    with zipfile.ZipFile(archives[0], 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (2026,10,8,0,0,0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry,data)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w') as archive:
        for name,data in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode, entry.mtime = len(data), 0o644, 0
            archive.addfile(entry,io.BytesIO(data))
    with archives[1].open('xb') as stream:
        stream.write(gzip.compress(raw.getvalue(),mtime=0))
    sums = output/('SHA256SUMS-flash-imager-skill-'+VERSION)
    with sums.open('x') as stream:
        stream.write(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in archives))
    print(json.dumps({'files':len(files),'archives':[str(p) for p in archives],'sums':str(sums)}))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: package-imager-skill.py <new-output-directory>')
    build(Path(sys.argv[1]).resolve())
