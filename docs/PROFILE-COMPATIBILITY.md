# Extended profiles and the early boot gate

The Imager's optional `extensions` field requires the runtime module
`profile_extensions.py`, the extended validator/materializer in `profile.py`,
and `system_apply()` in `boot.py`. Declare `imager-profile-v2` only when all are
packed; include the module in public-manager updates as well as full images.

LUKS authentication and inner capsule validation are separate operations.
A plain inner capsule with an unsupported schema must fail validation, not
enter a legacy password retry loop. For AES capsules, retry only authentication
failures (`InvalidTag`); do not disguise malformed formats or unsupported fields
as wrong passwords.

An optional local compatibility initrd can replace these public modules before
systemd starts, pinned to the exact factory version and original file hashes.
Preserve executable mode on `boot.py`: its systemd unit launches it directly.
Keep the immutable factory entry and publish the external GRUB pointer last,
after byte verification and real GRUB/multi-initrd boot tests. This does not
replace rebuilding and validating a future distributed image.

Regression coverage: extended plain capsule inside an already-open LUKS vault
does not request an inner password; invalid plain schemas do not ask for a
password; wrong AES phrases still retry. File-backed BIOS/UEFI tests should
also verify SSH gating, extension materialization, payload hashes, relock and
reopening on a second boot. Observe the hidden local prompt before key entry.
