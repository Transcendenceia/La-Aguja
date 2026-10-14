# Claves de recuperación y credenciales privadas · 0.9.15

La Aguja se puede preparar desde un PC distinto al que se rescatará. En el Imager Linux/Windows, añade entradas manuales **BitLocker o LUKS**, con etiqueta del equipo/disco e identificador opcional. El sistema del preparador y su cifrado no determinan qué entradas puedes guardar.

Elige protección cifrada para transportar claves. La contraseña de la imagen protege también el resguardo de recuperación. BitLocker exige 48 dígitos válidos; LUKS conserva espacios y Unicode exactos. No se admiten keyfiles binarios ni todos los formatos de cifrado Linux. Una clave de formato válido no demuestra que abra el disco.

## Dentro del live

```sh
aguja secrets --json
sudo aguja recovery status --json
aguja profile unlock
sudo aguja recovery list --json
sudo aguja recovery open INDICE /dev/disk/by-uuid/UUID-EXACTO
```

`secrets` muestra ubicaciones y presencia, sin valores. La cápsula está en `/config/aguja-recovery.json`. Tras desbloquear el perfil compatible, las claves se materializan en `/run/aguja-recovery/keys.json`: RAM privada, root, archivo 0600/directorio 0700. Si el resguardo usa otra contraseña, `sudo aguja recovery unlock` permite abrirlo por separado desde consola interactiva. En modo sin cifrar, las claves se cargan en RAM al arrancar, pero siguen legibles en el propio USB.

`list --json` muestra índices/tipos/etiquetas/IDs, nunca las claves. `open` exige el dispositivo exacto y abre un mapping de solo lectura por defecto; no monta, repara, descifra permanentemente ni modifica protectores. Un UUID LUKS configurado debe coincidir. `--writable` requiere alcance explícito de escritura. No uses el USB de arranque como destino ni pruebes claves sobre otros discos. Cierra los mappings después de detener sus consumidores.

Los agentes consultan la [guía de ubicaciones](../runtime/SECRETS.md) y la [skill de recuperación](../skills/disk-recovery/SKILL.md). Esa guía distingue perfil protegido, INI legado, API y sesiones nativas, Wi-Fi, tailnet e identidad SSH. No implica que todos existan o sean válidos. Las instrucciones del dueño se conservan fuera del bloque gestionado en AGENTS.md/CLAUDE.md/GEMINI.md.

Nunca vuelques claves, perfiles, tokens, passwords o archivos OAuth a conversación, logs, capturas, DATA o GitHub. Para usarlos, pasa únicamente el campo necesario al destino dentro de un proceso privado mediante entrada soportada, sin incluirlo en argv. Los launchers y servicios nativos ya consumen sus credenciales. Reiniciar borra la caché RAM y vuelve a bloquear las cápsulas cifradas.

En Rescue antiguo compatible (incluido 0.9.11), sigue disponible el auxiliar `/config/aguja-recovery.py` que acompaña la preparación; no tiene la integración nativa nueva. Actualizar la skill o publicar otra imagen no cambia un USB ya grabado ni un live en ejecución. [Contrato detallado en inglés](DISK-RECOVERY.md).
