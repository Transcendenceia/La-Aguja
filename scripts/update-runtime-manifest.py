#!/usr/bin/env python3
"""Manifest of public update-manager files eligible for clean generation carryover."""
import hashlib,json,sys
from pathlib import Path
MODULES=['tailnet_config.py', 'gui_session.py', 'desk.py', 'desk_backend.py', 'desk_i18n.py', 'web.py', 'file_open.py', 'file_manager.py', 'persistence.py', 'power.py', 'profile_vault.py', 'hardware.py', 'storage.py', 'agent_context.py', 'secret_inventory.py', 'recovery_state.py', 'i18n.py', 'updates.py', 'update_sources.py', 'update_tasks.py', 'update_progress.py', 'update_ui.py', 'update_jobs.py', 'tailnet_identity.py', 'tailscale_service.py', 'profile_cli.py', 'boot.py', 'profile.py', 'profile_extensions.py', 'network.py', 'display.py', 'cockpit.py', 'update-root-worker.sh', 'update-session-worker.sh', 'snapshot-initrd.sh', 'locale-catalog.json']
FILES=["usr/lib/aguja/"+n for n in MODULES]+['usr/share/aguja/capabilities.json', 'usr/share/aguja/ODD.md', 'usr/share/aguja/MISSIONS.md', 'usr/share/aguja/BACKUP.md', 'usr/share/aguja/AGENT-CONTEXT.md', 'usr/share/aguja/SSH-WELCOME.txt', 'etc/systemd/system/aguja-boot.service', 'usr/share/aguja/UPDATES.md', 'usr/share/aguja/skills/live-updates/SKILL.md', 'usr/lib/live/boot/9999-aguja-update.sh', 'etc/initramfs-tools/hooks/aguja-update', 'etc/systemd/system/aguja-tailscale.service', 'etc/systemd/system/aguja-tailscaled.service', 'etc/systemd/system/aguja-tailnet-save.service', 'etc/systemd/system/aguja-tailnet-save.path', 'etc/systemd/system/aguja-tailnet-save.timer', 'etc/systemd/system/aguja-update-check.service', 'etc/systemd/system/aguja-update-check.timer', 'etc/systemd/system/aguja-update-job@.service']
root=Path(sys.argv[1]);items={}
for name in FILES:
 path=root/name
 if not path.is_file() or path.is_symlink() or path.stat().st_size>2*1024**2:raise ValueError('Invalid public update runtime '+name)
 items[name]=hashlib.sha256(path.read_bytes()).hexdigest()
path=root/'usr/share/aguja/update-runtime.json';path.write_text(json.dumps({'schema':1,'ui_revision':4,'files':items},indent=2)+'\n');path.chmod(0o644)
