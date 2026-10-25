/* SPDX-License-Identifier: GPL-3.0-or-later
 * GRUB 2.12 x86_64-efi module: decline this boot option without changing NVRAM.
 * A successful EFI Exit returns OVMF to its menu instead of trying BootOrder's
 * next option. EFI_NOT_FOUND lets the firmware continue its own boot policy.
 * Keep the tiny GRUB ABI surface explicit; EFI structures come from GNU-EFI.
 * References: GRUB include/grub/{command,loader,dl}.h and kern/efi/efi.c.
 */
#include <efi.h>

struct grub_command;
typedef int (*command_fn)(struct grub_command *, int, char **);
extern struct grub_command *grub_register_command_prio(
    const char *, command_fn, const char *, const char *, int);
extern void grub_unregister_command(struct grub_command *);
extern void grub_machine_fini(int);
extern EFI_SYSTEM_TABLE *grub_efi_system_table;
extern EFI_HANDLE grub_efi_image_handle;

static char license[] __attribute__((section(".module_license"), used)) =
    "LICENSE=GPLv3+";
static const char name[] __attribute__((section(".modname"), used)) =
    "aguja_continue";
static struct grub_command *command;

static int continue_boot(struct grub_command *cmd __attribute__((unused)),
                         int argc __attribute__((unused)),
                         char **argv __attribute__((unused)))
{
    /* Same cleanup as grub_exit(), but decline rather than complete the boot.
     * No BootNext, BootOrder, guessed OS path, reset or disk mutation. */
    /* Keep GRUB's pages alive while executing this module's last instructions.
     * They are EFI boot-service memory, reclaimed by the eventual OS loader. */
    grub_machine_fini(1 | 4); /* NORETURN | EFI_KEEP_ALLOCATED_MEMORY */
    grub_efi_system_table->BootServices->Exit(
        grub_efi_image_handle, EFI_NOT_FOUND, 0, NULL);
    for (;;) { __asm__ volatile("pause"); }
    __builtin_unreachable();
}

static void __attribute__((used)) grub_mod_init(void *mod __attribute__((unused)))
{
    command = grub_register_command_prio("aguja_continue", continue_boot, NULL,
        "Continue the firmware boot order without this rescue disk.", 0);
}

static void __attribute__((used)) grub_mod_fini(void)
{
    grub_unregister_command(command);
}
