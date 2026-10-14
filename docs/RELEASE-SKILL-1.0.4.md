# Flash Imager Agent Skill 1.0.4

English first · Español después.

Portable file-image preparation with engine **0.9.15**, without Electron. Accepts explicitly supplied manual BitLocker/LUKS `disk_recovery` entries through private stdin, applies the selected profile protection, verifies every supplemental file, and preserves the original image. The standalone bundle includes its production engine, recovery helper, interfaces, licences and a member-hash manifest. `doctor` reports both skill and engine versions. No physical USB write, disk unlock or live upgrade happens during preparation.

On Rescue 0.9.15+, native `aguja recovery` and the canonical SECRETS.md map provide private RAM access after unlock, metadata-only selection and read-only mappings. The included live disk-recovery skill and agents' context share that contract. Older compatible Rescue uses the standalone CFG helper; don't claim native support there.

Download from this explicit skill tag, not `releases/latest`. Preserve previous skill installations before replacing them. Public packages contain no personal requests, keys or sessions.

## Español

Skill 1.0.4 con motor 0.9.15: claves manuales de otro equipo por stdin privado, protección compartida con la imagen, readback de todos los archivos y origen intacto. Paquete autónomo sin Electron, con versiones y hashes verificables. No graba USB ni abre discos. El live 0.9.15 integra la guía de secretos y `aguja recovery`; en versiones antiguas compatibles se usa el auxiliar independiente. Se preservan las descargas e instalaciones anteriores.
