# La Aguja Rescue Disk 1.1.2

Maintenance release over 1.1.1. Public factory images contain no owner profile,
provider sessions, SSH host keys, tailnet node identity or credentials.

- Retain encrypted tailnet identity checkpoints when applying the same extended
  preferences imported by Flash Imager. Verify saved bytes before reporting saved.
- Display tailnet connectivity separately from saved/pending/error/RAM identity.
- On a fixed/SCSI-presented boot medium, defer automatic DATA expansion and boot
  with its existing capacity instead of failing after profile unlock. Never
  repartition a non-removable boot disk automatically; removable USB guards remain.
- Include the current disk-recovery and live-update agent guidance already aligned
  in source with extended profiles and persist/power operations.

Flash Imager remains 1.1.0 and its Agent Skill remains 1.2.0; use the new signed
image catalog. Existing releases remain available. The backup-destination menu
redesign is a reviewed proposal, not a new automatic backup feature in this patch.

Final artifact hashes, test coverage and download verification accompany this
release in VALIDATION-1.1.2.md and SHA256SUMS. Physical Wi-Fi/GPU coverage is not
implied by virtual BIOS/UEFI tests.
