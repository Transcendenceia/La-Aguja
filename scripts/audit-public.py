#!/usr/bin/env python3
"""Audit exactly the staged Git tree; print paths/reasons, never credential values."""
import json
import re
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
findings=[]
patterns={
 'private-key':rb'(?m)^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'github-token':rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
 'provider-key':rb'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{30,}\b',
 'tailnet-key':rb'\btskey-(?:auth|api)-[A-Za-z0-9_-]{20,}\b',
}
for name in filter(None,names):
 p=root/name
 if p.is_symlink():findings.append({'path':name,'reason':'symlink'});continue
 if p.suffix in ('.pem','.key','.pfx','.p12','.aguja') or '.env' in p.name or any(x in ('operations','private','node_modules','build','dist') for x in Path(name).parts):findings.append({'path':name,'reason':'private-or-generated-path'})
 if p.stat().st_size>25*1024**2:findings.append({'path':name,'reason':'large-file'});continue
 data=p.read_bytes()
 for label,pattern in patterns.items():
  if re.search(pattern,data):findings.append({'path':name,'reason':label})
print(json.dumps({'ok':not findings,'tracked_files':len(list(filter(None,names))),'findings':findings},indent=2))
raise SystemExit(bool(findings))
