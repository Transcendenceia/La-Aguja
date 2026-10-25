# Flash Imager · Linux / Windows · 2026-10-24

## Objetivo y pedido relevante
Alinear ambos Imagers con Rescue actual, aplicar STYLE.md, NAS/cloud, tailnet ampliada, múltiples Wi-Fi, contraseña común, variables de entorno importables y mejorar estabilidad/rendimiento/interacción.

Propietario: Angie. Fuentes base: 5d41641, Rescue público 1.1.0 e Imager 1.0.0.
Escritura: desktop/, runtime/perfil y red, scripts de perfil/imagen, documentación/pruebas y artefactos candidatos de este worktree.
Fuera de alcance: publicación, cuentas/credenciales reales, USB/discos físicos y servicios de infraestructura. Marlon autorizó posteriormente usar la VM `win11` de CachyOS para QA nativa; cambios temporales de arranque y dispositivos sintéticos se revierten.
Rollback: worktree aislado feat/imager-rescue-alignment-20261024; base y artefactos publicados intactos.

## Criterios observables
- UI y perfil comunes para ambos sistemas; estilo grafito/espectro, Agujita preservada, navegación accesible/adaptable.
- Hasta 16 Wi-Fi ordenadas; importar sin sobrescribir otras; todas aplicables al Rescue.
- Opciones tailnet equivalentes al Desk: DNS, rutas, nodo salida/acceso LAN, tags, shields, anuncio/forwarding/netfilter; validación y sin activación desde el PC.
- NAS/cloud manual e importación rclone portable, secretos privados, sin contactar servicios al importar/preparar.
- Contraseña común para SSH/perfil/desbloqueo por defecto; opción explícita de separar; nunca alterar claves de terceros.
- Variables personalizadas manuales/importadas como datos literales, sin ejecutar shell ni importar entorno completo del PC.
- Exportar/abrir perfil, preparar Linux/Windows y editar USB conservan todos los ajustes.
- Compatibilidad explícita: ajustes nuevos necesitan Rescue con capacidad anunciada; nunca descartarlos en silencio en Rescue antiguo.
- Pruebas deterministas de validación, roundtrip/cifrado, aplicación runtime y GUI. Paquetes de ambas plataformas, hashes y limitaciones documentadas.

## Estado
Implementación y candidatos completados. QA Windows nativa autorizada posteriormente por Marlon, terminada; VM apagada y XML original restaurado byte a byte. BitLocker activo/cifrado al 100 %, sin cambiar sus protectores.

## Implementación comprobable
- Extensión opcional `extensions` de schema1, capacidad `imager-profile-v2`; base sin extensiones sigue siendo compatible. Imager1.1.0 / Rescue candidato1.2.0, sin publicación.
- NAS/cloud usa rclone nativo del Rescue. Configuración manual e importación limitada a siete familias sin hooks de shell; archivos de credenciales portables solo desde la carpeta seleccionada. La preparación nunca contacta cuentas.
- `.env`/JSON literal, máximo128variables; no lectura masiva del entorno del anfitrión. Variables entregadas a agentes; claves API de las tarjetas prevalecen.
- Hasta16Wi-Fi con prioridades NM descendentes. Tailnet usa las opciones nativas del Desk, con interruptores explícitos y sin activación desde Imager.
- Nuevos textos ES/EN. Los siete idiomas de interfaz existentes mantienen su contenido previo; textos nuevos sin traducción específica usan fallback inglés explícito. No se afirma traducción nueva completa a siete idiomas.
- La cápsula generada conserva AES-GCM para interoperabilidad Linux/Windows; Rescue ofrece conversión explícita a LUKS. No se presenta AES como LUKS.
- Primeras regresiones:143Node,133aprobadas/10omitidas Windows;291Python en Debianlive,290aprobadas/1omitida GPT/FAT (se cubre desde el anfitrión). Linux Electron real y perfiles cifrados verificados. Hito inicial, superado por el cierre siguiente.

## Cierre de implementación y evidencia
- Imager1.1.0 Linux (.AppImage/.deb/.tar.gz) y Windows (.exe portable), Rescue1.2.0 candidato (.img/.iso), sin publicación.
- Final tras QA Windows:149Node en Linux,138aprobadas/11omitidas Windows; suite nativa Windows109,94aprobadas/15omitidas Linux/Python/symlink;291Python/291aprobadas en Debian aislado. Cuatro rutas FAT extendidas Linux/Windows × claro/cifrado, negativas de compatibilidad, cifrado y lector runtime real.
- Electron Linux real: regresión38, preparación de imágenes claras/cifradas, rechazo disco interno, editorUSB simulado, roundtripnuevo y los siete idiomas de interfaz. GUI nueva repetida sobre el paquete Linux construido, no solo checkout. 11archivos críticos ASAR y9recursos por plataforma idénticos a fuentes.
- IMG1.2.0 exacta: BIOS perfil automático y UEFI perfil cifrado con contraseña por tecladoQMP; SSH indisponible antes de desbloquear. Ambos arrancan y aplican dosWi-Fi/prioridades/permisos, variables literales, NASsin contacto, opciones tailnet/forwarding y launcherCodex. Solo discos de archivo; ninguna cuenta real ni USB físico.
- Windows11 Pro nativo: portable final lanzado, paquete real con perfil ampliado/FAT claro y cifrado, siete idiomas/640px, editor y resultados; helpers PowerShell/Credential Manager/ACL/progreso/consola. USB virtual8GiB: RAW y GPT grabados con UAC real y readback SHA completo de imagen sintética96MiB, metadatos de otros discos intactos. Sin USB físico ni cuentas reales.
- Entrega canónica de candidatos en CachyOS `~/Aguja/imager-next-20261024/final/`; Imagers y IMG también en `operations/imager-next-20261024/final/` de este worktree. Informe RESULTADO.md y hashes por artefacto. Fuentes estables/publicación/pendrive conservados. VM apagada y XML/media/orden originales restaurados exactamente tras QA; carpeta y tarea temporales retiradas.

Referencias de implementación: [Tailscale up](https://tailscale.com/docs/reference/tailscale-cli/up), [rclone obscure](https://rclone.org/commands/rclone_obscure/). Obscure es formato rclone reversible, no cifrado del perfil; la protección de la cápsula es independiente.

## Hallazgo y corrección nativa
`Get-Partition -ErrorAction Stop` rechaza un USB RAW sin particiones. El grabador ahora consulta volúmenes solo si el disco tiene particiones; fallos de enumeración en discos poblados siguen siendo fatales. Regresión nativa RAW/GPT vacíos + error de enumeración y dos grabaciones reales sobre disco de archivo virtual, con identidad exacta y sin mock del writer. Ambos Imagers reconstruidos; Rescue no cambia.

Las pruebas compartidas distinguen bits POSIX, privilegio de symlink y lector Python Linux de las comprobaciones nativas. No se habilitó Developer Mode ni se cambió UAC. Evidencia privada en `operations/imager-next-20261024/windows-native/`; `result7.json`, `final-flash.json`, `raw-flash.json`, `portable-smoke.json` y restauración/hash XML.

## Diagnóstico Linux · selección incompatible
El error de preparación con ajustes ampliados y la IMG pública1.1.0 se ocultaba por el manejador genérico del helper Python. La capacidad `imager-profile-v2` falta en esa imagen y está presente en la candidata1.2.0. El helper ahora devuelve un recibo público explícito antes de materializar imports o crear una copia privada. No se relaja el rechazo de compatibilidad ni se descartan campos. La lectura de opciones booleanas de la app real confirmó DNS aceptado y anuncio de nodo de salida; sin valores secretos en evidencia.
Regresión:23pruebas del módulo de perfil (22aprobadas/1omitida GPT-FATdelCT); prueba Electron Linux empaquetado con imagen FAT sintética, error visible específico, origen intacto, cero escritura USB. Imager corregido entregado por separado, sin cerrar la app actual ni perder los ajustes. Diagnóstico y preparación sobre copia privada no autorizan por sí solos reemplazar el pendrive.
