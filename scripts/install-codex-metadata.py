#!/usr/bin/env python3
"""Match the native CLI's upstream package metadata in an isolated factory."""
import json
import os
from pathlib import Path
import sys

project = Path(__file__).resolve().parents[1]
root = Path(sys.argv[1]).resolve()
if os.geteuid() != 0 or root == Path('/') or not (root/'etc/debian_version').is_file():
    raise SystemExit('Isolated Debian root required')
sys.path.insert(0,str(project/'runtime'))
import updates
descriptor = json.loads((project/'config/codex-package.json').read_text())
if descriptor['version'] != json.loads((project/'config/harnesses.json').read_text())['codex']:
    raise SystemExit('Codex package lock mismatch')
cache = project/'build/downloads'
cache.mkdir(parents=True,exist_ok=True)
updates.install_codex_metadata(root,descriptor,cache)
