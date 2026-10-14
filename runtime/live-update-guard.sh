# Sourced by live-boot; called after the selected media is mounted, before root.
aguja_verify_generation() {
 generation=''
 expected=''
 for parameter in $(cat /proc/cmdline); do
  case "$parameter" in
   aguja.generation=*) generation=${parameter#*=} ;;
   aguja.sha256=*) expected=${parameter#*=} ;;
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
 actual=$(sha256sum "$1${LIVE_MEDIA_PATH}/filesystem.squashfs")
 actual=${actual%% *}
 [ "$actual" = "$expected" ] || panic 'LA AGUJA update damaged; select factory or previous generation in GRUB'
}
