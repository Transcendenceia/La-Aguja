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

## Download and use

Use Flash Imager 1.1.0 and the signed catalogue to prepare a USB. For manual
import, decompress IMG.ZST first; alternatively concatenate all three IMG parts
in numerical order and verify the complete IMG SHA-256. Never flash one part
as a whole image. The ISO is the standalone live/VM format, not the configurable
Imager IMG. Factory SSH is `aguja` / `aguja`; provision personal access in Imager.
LUKS protects the profile vault, not all DATA. Keep snapshot phrases outside the
USB. AI clients require Internet and your own provider authorization.

## Correcciones / Español

- Se conserva la configuración que permite guardar la identidad tailnet cifrada
  al aplicar las preferencias ampliadas del mismo perfil. La interfaz distingue
  conexión activa de identidad guardada, pendiente, con error o solo en RAM.
- Un medio de arranque presentado como fijo/SCSI usa su capacidad existente y
  pospone la ampliación de DATA, sin modificar automáticamente su particionado ni
  volver al diálogo de contraseña por un fallo posterior al desbloqueo.
- Se incorporan las guías vigentes de recuperación de discos y persistencia.
  Flash Imager continúa en 1.1.0 y su Agent Skill en 1.2.0.
- «Planificar respaldo» no se ha convertido en un programador o copiador; el
  cambio de nombre/ubicación sigue siendo una propuesta pendiente.

La imagen pública es de fábrica: sin cuentas, sesiones, claves SSH, Wi-Fi ni
identidad tailnet del propietario. Descarga mediante el catálogo firmado o
verifica las sumas antes del uso manual. Las pruebas BIOS/UEFI son virtuales;
no certifican Secure Boot ni compatibilidad universal con hardware físico.
