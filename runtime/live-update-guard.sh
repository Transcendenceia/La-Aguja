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
 # Downloads, writes and activation verify full content before committing.
 # Normal boot validates the selection without rereading the entire USB image.
 # An explicit diagnostic boot can still detect corruption since activation.
 case "$verification" in
  quick) return 0 ;;
  full) ;;
  *) panic 'Invalid LA AGUJA verification mode' ;;
 esac
 actual=$(sha256sum "$1${LIVE_MEDIA_PATH}/filesystem.squashfs")
 actual=${actual%% *}
 [ "$actual" = "$expected" ] || panic 'LA AGUJA update damaged; select factory or previous generation in GRUB'
}
