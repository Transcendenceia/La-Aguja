#!/bin/bash
set -euo pipefail
PROJECT=$(cd "$(dirname "$0")/.." && pwd)
OUTPUT=${1:?Specify output module path}
# GNU-EFI supplies the standard EFI table layout and Microsoft's x64 ABI.
# This is a GRUB relocatable module, not a separate EFI image or OS loader.
[[ -f /usr/include/efi/efi.h ]] || { echo 'Install gnu-efi to build Continue'; exit 1; }
mkdir -p "$(dirname "$OUTPUT")"
gcc -Os -Wall -Wextra -Werror -ffreestanding -fno-stack-protector \
    -fno-asynchronous-unwind-tables -fno-unwind-tables -fno-pic -fno-pie \
    -mcmodel=large -mno-red-zone -DGNU_EFI_USE_MS_ABI \
    -I/usr/include/efi -I/usr/include/efi/x86_64 \
    -c "$PROJECT/boot/continue.c" -o "$OUTPUT"
readelf -sW "$OUTPUT" | grep -q grub_mod_init
