#!/bin/bash
# Pinned upstream binaries + Debian-maintained graphical runtime in an isolated root.
set -euo pipefail
PROJECT=${AGUJA_PROJECT:-$(cd "$(dirname "$0")/.." && pwd)}
ROOT=${AGUJA_ROOT:-$PROJECT/build/rootfs}
[[ $EUID == 0 && -f "$ROOT/etc/debian_version" && $(realpath "$ROOT") != / ]] || exit 1
mkdir -p "$PROJECT/build/desktop-downloads" "$ROOT/tmp/aguja-desktop-packages"
for name in helium yazi; do
    url=$(jq -r --arg name "$name" '.[$name].url' "$PROJECT/config/desktop-tools.json")
    digest=$(jq -r --arg name "$name" '.[$name].sha256' "$PROJECT/config/desktop-tools.json")
    package="$PROJECT/build/desktop-downloads/$name.deb"
    if ! [[ -f "$package" ]] || ! printf '%s  %s\n' "$digest" "$package" | sha256sum --check --status; then
        curl --fail --location --retry 3 "$url" --output "$package.pending"
        printf '%s  %s\n' "$digest" "$package.pending" | sha256sum --check
        mv "$package.pending" "$package"
    fi
    install -m 644 "$package" "$ROOT/tmp/aguja-desktop-packages/$name.deb"
done
chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive /bin/bash -e <<'INSTALL'
apt-get update -qq
apt-get install -y --no-install-recommends python3-gi gir1.2-gtk-3.0 librsvg2-common network-manager-gnome \
  file bat fzf fd-find 7zip xxd poppler-utils ffmpegthumbnailer chafa feh zathura zathura-pdf-poppler \
  mpv mousepad xdg-utils shared-mime-info adwaita-icon-theme thunar gvfs gvfs-backends udisks2 eject x11-xserver-utils \
  /tmp/aguja-desktop-packages/helium.deb /tmp/aguja-desktop-packages/yazi.deb
apt-get clean
INSTALL
install -m 644 "$PROJECT/config/desktop-tools.json" "$ROOT/usr/share/aguja/desktop-tools.json"
install -d "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml"
install -m 644 "$PROJECT/runtime/desktop-resources/thunar.xml" "$ROOT/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/thunar.xml"
