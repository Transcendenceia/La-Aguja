# Continue the computer's normal boot

## English

`config/grub.cfg` preserves the firmware's boot policy. On BIOS, GRUB `exit`
continues the firmware device sequence. On x86-64 UEFI, `aguja_continue.mod`
performs GRUB's machine cleanup, retaining its allocated boot-service pages until
the command has exited, then calls EFI `Exit` for GRUB with `EFI_NOT_FOUND`.
Returning `EFI_SUCCESS`, as standard GRUB `exit` does, may reopen the firmware
menu instead of attempting the next BootOrder entry. The eventual OS reclaims
boot-service memory normally. The module does not write BootOrder, BootNext or
any other EFI variable, reset the machine, enumerate private filesystems, or
guess an installed OS loader path. Firmware still controls which entry is next;
if none is bootable, its own recovery/boot-selector behavior applies.

Build host: Debian amd64, gcc, binutils, `gnu-efi`, GRUB 2.12 amd64 EFI modules.
`bash scripts/build-continue.sh output/aguja_continue.mod` builds a relocatable
GRUB module, not a standalone EFI application. GNU-EFI headers supply the UEFI
table layout and Microsoft x64 call ABI; only opaque GRUB command handles and
five GRUB 2.12 exported symbols are used. Keep that ABI in mind when upgrading
GRUB. The build uses no network downloads. Source and module are GPL-3.0-or-later.

Acceptance must test the actual final hybrid image with an isolated BIOS guest
and a UEFI guest with private variable storage. Put Rescue first and a distinct
bootable sentinel second, select Continue in the delivered GRUB menu, and require
the sentinel to execute. Exiting to a firmware menu or looping to Rescue is not
a passing result. Do not use a physical owner's disks or NVRAM for this test.
This is not Secure Boot certification.

References: [UEFI boot manager](https://uefi.org/specs/UEFI/2.11/03_Boot_Manager.html),
[GRUB EFI exit](https://github.com/rhboot/grub2/blob/grub-2.12/grub-core/kern/efi/efi.c),
[GRUB loader flags](https://github.com/rhboot/grub2/blob/grub-2.12/include/grub/loader.h).

## Español

Continuar entrega al firmware el siguiente arranque de su configuración, sin
cambiar NVRAM ni buscar rutas privadas de Windows/Linux. BIOS utiliza `exit`;
UEFI devuelve `EFI_NOT_FOUND` desde un módulo mínimo de GRUB para pasar a la
siguiente opción, no declarar un arranque terminado con éxito. Las páginas de
GRUB se conservan hasta salir y el sistema siguiente recupera la memoria EFI.
Si no hay otro destino arrancable, decide el firmware. El ensayo debe demostrar
el arranque de un segundo medio independiente con la imagen definitiva, tanto
en BIOS como en UEFI, nunca usando discos o NVRAM físicos del propietario.
