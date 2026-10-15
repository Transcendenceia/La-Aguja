#!/usr/bin/env python3
"""Manifest of public update-manager files eligible for clean generation carryover."""
import hashlib,json,sys
from pathlib import Path
MODULES=['updates.py','update_sources.py','update_tasks.py','update_progress.py','update_ui.py','display.py','cockpit.py','update-root-worker.sh','update-session-worker.sh','locale-catalog.json']
FILES=['usr/lib/aguja/'+n for n in MODULES]+['usr/share/aguja/UPDATES.md','usr/share/aguja/skills/live-updates/SKILL.md']
root=Path(sys.argv[1]);items={}
for name in FILES:
 path=root/name
 if not path.is_file() or path.is_symlink() or path.stat().st_size>2*1024**2:raise ValueError('Invalid public update runtime '+name)
 items[name]=hashlib.sha256(path.read_bytes()).hexdigest()
path=root/'usr/share/aguja/update-runtime.json';path.write_text(json.dumps({'schema':1,'ui_revision':2,'files':items},indent=2)+'\n');path.chmod(0o644)
