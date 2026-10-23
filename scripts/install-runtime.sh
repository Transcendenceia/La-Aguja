#!/bin/bash
# Install runtime and console assets into an existing, isolated rootfs.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT=${AGUJA_ROOT:-$PROJECT/build/rootfs}
[[ $EUID == 0 && -f "$ROOT/etc/debian_version" && $(realpath "$ROOT") != / ]] || { echo 'Rootfs Debian aislada requerida'; exit 1; }
AGUJA_PROJECT="$PROJECT" AGUJA_ROOT="$ROOT" bash "$PROJECT/scripts/install-tailscale.sh"
install -d "$ROOT/usr/lib/aguja" "$ROOT/usr/share/aguja" "$ROOT/etc/aguja" \
  "$ROOT/etc/skel" "$ROOT/etc/profile.d" "$ROOT/etc/systemd/system" "$ROOT/usr/local/share/zsh/site-functions"
printf '{"schema":1,"features":["early-profile-gate-v1","luks-profile-v1","hardware-preflight-v1","storage-credentials-v1","rescue-desk-v1","operational-odd-v1","bulk-updates-v1"]}\n' > "$ROOT/usr/share/aguja/capabilities.json"
# The factory account is locked until boot's profile gate configures owner access.
chroot "$ROOT" passwd -l aguja
# Persistent update infrastructure, copied only into the isolated factory.
install -m 755 "$PROJECT/runtime/update-root-worker.sh" "$ROOT/usr/lib/aguja/update-root-worker.sh"
install -m 755 "$PROJECT/runtime/update-session-worker.sh" "$ROOT/usr/lib/aguja/update-session-worker.sh"
install -m 644 "$PROJECT/desktop/resources/release-key.json" "$ROOT/usr/share/aguja/release-key.json"
install -m 644 "$PROJECT/config/harnesses.json" "$ROOT/usr/share/aguja/harnesses.json"
install -m 644 "$PROJECT/runtime/update-protocol.json" "$ROOT/usr/share/aguja/update-protocol.json"
install -m 644 "$PROJECT/runtime/UPDATES.md" "$ROOT/usr/share/aguja/UPDATES.md"
install -m 644 "$PROJECT/runtime/MISSIONS.md" "$PROJECT/runtime/BACKUP.md" "$ROOT/usr/share/aguja/"
install -d "$ROOT/usr/share/aguja/branding/fonts"
install -m 644 "$PROJECT/branding/fonts/"* "$ROOT/usr/share/aguja/branding/fonts/"
install -d "$ROOT/usr/share/aguja/skills/live-updates"
install -m 644 "$PROJECT/skills/live-updates/SKILL.md" "$ROOT/usr/share/aguja/skills/live-updates/"
install -m 755 "$PROJECT/runtime/update-initramfs-hook" "$ROOT/etc/initramfs-tools/hooks/aguja-update"
install -m 644 "$PROJECT/runtime/live-update-guard.sh" "$ROOT/lib/live/boot/9999-aguja-update.sh"
python3 - "$ROOT/lib/live/boot/9990-main.sh" <<'PYGUARD'
import sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text();call='\taguja_verify_generation "${livefs_root}"\n'
if call not in s:s=s.replace('\tVerify_checksums "${livefs_root}"',call+'\tVerify_checksums "${livefs_root}"',1)
assert call in s;p.write_text(s)
PYGUARD
install -m 644 "$PROJECT/runtime/aguja-update-check.service" "$PROJECT/runtime/aguja-update-check.timer" "$PROJECT/runtime/aguja-update-job@.service" "$PROJECT/runtime/aguja-tailnet-save.service" "$PROJECT/runtime/aguja-tailnet-save.path" "$PROJECT/runtime/aguja-tailnet-save.timer" "$ROOT/etc/systemd/system/"
install -d "$ROOT/etc/initramfs-tools/conf.d" "$ROOT/etc/NetworkManager/conf.d"
printf 'MODULES=most\n' > "$ROOT/etc/initramfs-tools/conf.d/aguja-portable"
# Avoid unreliable firmware Wi-Fi power-saving during SSH/long transfers.
printf '[connection]\nwifi.powersave=2\n' > "$ROOT/etc/NetworkManager/conf.d/20-aguja-wifi.conf"
# runtime/*.py is the canonical module inventory, also verified by build-image.
install -m 755 "$PROJECT/runtime/"*.py "$ROOT/usr/lib/aguja/"
install -m 644 "$PROJECT/runtime/console-history.conf" "$ROOT/usr/lib/aguja/"
install -m 644 "$PROJECT/runtime/locale-catalog.json" "$ROOT/usr/lib/aguja/"
install -m 755 "$PROJECT/runtime/aguja" "$ROOT/usr/local/bin/aguja"
install -m 755 "$PROJECT/runtime/auth-open" "$ROOT/usr/local/bin/aguja-auth-open"
install -m 644 "$PROJECT/runtime/AGENT-CONTEXT.md" "$PROJECT/runtime/QUICKSTART.md" "$PROJECT/runtime/TOOLBOX.md" "$PROJECT/runtime/SSH-WELCOME.txt" "$ROOT/usr/share/aguja/"
install -m 644 "$PROJECT/runtime/SECRETS.md" "$ROOT/usr/share/aguja/"
install -d "$ROOT/usr/share/aguja/skills/disk-recovery"
install -m 644 "$PROJECT/skills/disk-recovery/SKILL.md" "$ROOT/usr/share/aguja/skills/disk-recovery/"
install -m 644 "$PROJECT/LICENSE" "$PROJECT/NOTICE.md" "$ROOT/usr/share/aguja/"
install -m 644 "$PROJECT/branding/donation/qr.png" "$ROOT/usr/share/aguja/donation-qr.png"
install -m 644 "$PROJECT/VERSION" "$ROOT/usr/share/aguja/VERSION"
install -m 644 "$PROJECT/runtime/zshrc" "$ROOT/usr/share/aguja/zshrc"
install -m 644 "$PROJECT/runtime/locale.sh" "$ROOT/etc/profile.d/aguja-locale.sh"
install -m 644 "$PROJECT/runtime/_aguja" "$ROOT/usr/local/share/zsh/site-functions/_aguja"
install -m 644 "$PROJECT/config/aguja.conf" "$PROJECT/config/harnesses.json" "$ROOT/etc/aguja/"
install -m 644 "$PROJECT/runtime/aguja-boot.service" "$ROOT/etc/systemd/system/"
install -m 644 "$PROJECT/runtime/aguja-activity.service" "$ROOT/etc/systemd/system/"
install -m 644 "$PROJECT/runtime/aguja-tailscale.service" "$ROOT/etc/systemd/system/"
install -m 644 "$PROJECT/runtime/aguja-tailscaled.service" "$ROOT/etc/systemd/system/"
install -m 644 "$PROJECT/runtime/aguja-network-check.service" "$PROJECT/runtime/aguja-network-check.timer" "$ROOT/etc/systemd/system/"
install -m 755 "$PROJECT/runtime/browser-launch" "$ROOT/usr/local/bin/aguja-browser-launch"
install -m 755 "$PROJECT/runtime/browser-session" "$ROOT/usr/lib/aguja/browser-session"
install -m 755 "$PROJECT/runtime/web-launch" "$ROOT/usr/local/bin/aguja-web"
install -m 755 "$PROJECT/runtime/file-open" "$ROOT/usr/local/bin/aguja-open"
install -d "$ROOT/usr/share/aguja/desktop"
cp -a "$PROJECT/runtime/desktop-resources/." "$ROOT/usr/share/aguja/desktop/"
install -m 644 "$PROJECT/runtime/ODD.md" "$ROOT/usr/share/aguja/"
install -m 644 "$PROJECT/config/desktop-tools.json" "$ROOT/usr/share/aguja/desktop-tools.json"
install -d "$ROOT/usr/share/fonts/truetype/aguja" "$ROOT/usr/share/aguja/branding/mascot"
install -m 644 "$PROJECT/branding/fonts/Inter.ttf" "$ROOT/usr/share/fonts/truetype/aguja/"
install -m 644 "$PROJECT/branding/mascot/idle.png" "$ROOT/usr/share/aguja/branding/mascot/"
printf 'source /usr/share/aguja/zshrc\n' > "$ROOT/etc/skel/.zshrc"
touch "$ROOT/etc/skel/.hushlogin"
install -m 644 "$ROOT/etc/skel/.zshrc" "$ROOT/home/aguja/.zshrc"
touch "$ROOT/home/aguja/.hushlogin"
chroot "$ROOT" chown -R aguja:aguja /home/aguja
chroot "$ROOT" usermod -s /bin/zsh aguja
chroot "$ROOT" usermod -a -G video,render,kvm aguja
truncate -s 0 "$ROOT/etc/motd"
for service in ssh avahi-daemon; do
    mkdir -p "$ROOT/etc/systemd/system/$service.service.d"
    printf '[Unit]\nRequires=aguja-boot.service\nAfter=aguja-boot.service\n' > "$ROOT/etc/systemd/system/$service.service.d/aguja.conf"
done
for unit in getty@tty1 serial-getty@ttyS0; do
    mkdir -p "$ROOT/etc/systemd/system/$unit.service.d"
    # shellcheck disable=SC2016
    printf '[Unit]\nRequires=aguja-boot.service\nAfter=aguja-boot.service\n[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin aguja %%I $TERM\n' > "$ROOT/etc/systemd/system/$unit.service.d/autologin.conf"
done
cat > "$ROOT/etc/profile.d/aguja.sh" <<'EOF'
export PATH="$HOME/.local/bin:/usr/local/sbin:/usr/sbin:/sbin:$PATH"
if [ "$(id -un)" = aguja ] && [ -t 0 ] && [ -z "${AGUJA_COCKPIT:-}" ]; then
    export AGUJA_COCKPIT=1
    if [ -n "${SSH_CONNECTION:-}" ]; then aguja welcome --remote; else aguja welcome; fi
fi
EOF
chroot "$ROOT" systemctl enable aguja-boot.service avahi-daemon.service aguja-activity.service aguja-tailscale.service aguja-network-check.timer aguja-update-check.timer aguja-tailnet-save.path aguja-tailnet-save.timer

python3 "$PROJECT/scripts/update-runtime-manifest.py" "$ROOT"
