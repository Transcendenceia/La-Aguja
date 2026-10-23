# Sourced by live-boot; called after the selected media is mounted, before root.
aguja_verify_generation() {
 generation=''
 expected=''
 verification=quick
 for parameter in $(cat /proc/cmdline); do
  case "$parameter" in
   aguja.generation=*) generation=${parameter#*=} ;;
   aguja.sha256=*) expected=${parameter#*=} ;;
   aguja.verify=*) verification=${parameter#*=} ;;
  esac
 done
 [ -n "$generation" ] || return 0
 case "$generation" in gen-*) ;; *) panic 'Invalid LA AGUJA update generation' ;; esac
 [ "${#generation}" = 36 ] || panic 'Invalid LA AGUJA generation length'
 identifier=${generation#gen-}
 case "$identifier" in *[!a-f0-9]*) panic 'Invalid LA AGUJA generation identifier' ;; esac
 [ "${#expected}" = 64 ] || panic 'Invalid LA AGUJA root digest'
 case "$expected" in *[!a-f0-9]*) panic 'Invalid LA AGUJA root digest' ;; esac
 [ "${LIVE_MEDIA_PATH}" = "/updates/$generation/live" ] || panic 'LA AGUJA media path mismatch'
 [ -r "$1${LIVE_MEDIA_PATH}/filesystem.squashfs" ] || panic 'LA AGUJA root image unavailable'
 image="$1${LIVE_MEDIA_PATH}/filesystem.squashfs"
 # Downloads, writes and activation verify full content before committing.
 # Normal boot validates the selection without rereading the entire USB image.
 # An explicit diagnostic boot can still detect corruption since activation.
 case "$verification" in
  quick) ;;
  full) ;;
  *) panic 'Invalid LA AGUJA verification mode' ;;
 esac
 if [ "$verification" = full ]; then
  actual=$(sha256sum "$image")
  actual=${actual%% *}
  [ "$actual" = "$expected" ] || panic 'LA AGUJA update damaged; select factory or previous generation in GRUB'
 fi
 case " $(cat /proc/cmdline) " in
  *' aguja.snapshot=1 '*)
   # This runs before live-boot's own squashfs loop setup. cryptsetup needs
   # loop devices now, not only once the normal root scan starts.
   modprobe loop || panic 'LA AGUJA encrypted snapshot requires loop support'
   modprobe dm_crypt || panic 'LA AGUJA encrypted snapshot requires dm-crypt'
   # Reuse live-boot's device setup (including udev settlement). Opening a
   # block device avoids libcryptsetup's implicit autoclear-loop requirement.
   snapshot_loop=$(setup_loop "$image" 0 '-r')
   [ -b "$snapshot_loop" ] || panic 'LA AGUJA snapshot loop unavailable'
   # Our graphical splash has no password widget. Reveal the real local
   # console before asking, rather than accepting input behind a blank splash.
   if command -v plymouth >/dev/null 2>&1; then plymouth quit || true; fi
   # The encrypted ext4 payload holds a regular squashfs. Bind that file over
   # the container path before live-boot inspects it; no plaintext DATA copy.
   cryptsetup isLuks "$snapshot_loop" || panic 'LA AGUJA encrypted snapshot is invalid'
   unlocked=no
   for attempt in 1 2 3; do
    if /lib/cryptsetup/askpass 'LA AGUJA · Desbloquear cambios guardados: ' | cryptsetup open --readonly --key-file - "$snapshot_loop" aguja-snapshot-root; then
     unlocked=yes
     break
    fi
   done
   [ "$unlocked" = yes ] || panic 'LA AGUJA snapshot unlock failed; select factory or previous generation'
   mkdir -p /run/live/aguja-snapshot
   mount -t ext4 -o ro,noload /dev/mapper/aguja-snapshot-root /run/live/aguja-snapshot || panic 'LA AGUJA snapshot filesystem failed'
   [ -f /run/live/aguja-snapshot/system.squashfs ] || panic 'LA AGUJA snapshot root missing'
   mount --bind /run/live/aguja-snapshot/system.squashfs "$image" || panic 'LA AGUJA snapshot root unavailable'
   ;;
 esac
}
