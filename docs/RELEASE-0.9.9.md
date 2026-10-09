# LA AGUJA 0.9.9 · Rescue Disk e Imager

La versión que incorpora navegación con la rueda del ratón a las consolas locales, sin añadir un escritorio completo.

## Rescue Disk

- Historial de hasta 10.000 líneas por consola local, en RAM y sin transcripciones guardadas.
- Rueda hacia arriba para revisar respuestas largas; hacia abajo hasta el prompt, o Esc para volver.
- Integrado al arrancar en los agentes, login y consola local; SSH conserva el terminal del cliente.
- Codex local usa salida inline; el navegador OAuth conserva su consola y dispone de barra de desplazamiento.
- Conserva modo Seguro predeterminado, YOLO explícito y acceso sudo completo, perfiles cifrados, idioma/teclado y los cuatro CLI preinstalados.

## Flash Imager

- Detecta falta de espacio antes de copiar la imagen privada y explica cuánto falta.
- En Windows permite elegir otra carpeta de trabajo para preparar y grabar; cancelar no escribe el USB.
- Conserva archivos de destino existentes y la imagen original.

## Descargas

- [Imagen USB comprimida (.img.zst)](https://aguja.transcendenceia.net/releases/aguja-0.9.9-amd64.img.zst)
- [ISO BIOS/UEFI](https://aguja.transcendenceia.net/releases/aguja-0.9.9-amd64.iso)
- [SHA-256 del Rescue](https://aguja.transcendenceia.net/releases/SHA256SUMS-rescue-0.9.9.txt)
- Imagers Windows/Linux y sumas: archivos adjuntos de esta publicación.

Para importación manual, descomprime el .img.zst y elige el .img. El Imager verifica el catálogo firmado, las partes y el hash completo. Instalar el Imager no actualiza un USB ya grabado. Las descargas anteriores permanecen disponibles.

Imagen de fábrica sin cuentas personales. Los componentes externos conservan sus licencias y condiciones: LICENSE, NOTICE.md y packages.tsv. El marcador interno distribution=personal se conserva.

El historial comienza en las nuevas consolas y no recupera texto ya perdido. Las aplicaciones que redibujan o borran su propia pantalla pueden requerir navegación nativa. No se declara compatibilidad universal ni una prueba de USB físico por publicar esta versión.

## Verificación de esta versión

- Cuatro clones independientes: BIOS y UEFI, con y sin perfil cifrado; arranque y reinicio correctos.
- En los cuatro, consola local creada por la imagen de fábrica y rueda virtual QEMU → eventos del kernel → historial; subida de tres líneas y regreso al prompt.
- 171 casos runtime: 170 aprobados con la identidad adecuada, uno omitido; 103 pruebas Imager aprobadas (10 específicas de Windows omitidas en Linux), ocho pruebas del sitio y 38 comprobaciones del Electron Linux empaquetado.
- EXE portátil Windows: contenedores y ASAR coincidentes con la fuente; corrección de espacio probada previamente en el Windows real con la misma implementación. No se reinicia la VM de uso ni se prueba aquí un gesto de ratón humano o un USB físico.
- [Skill 1.0.1 para agentes](https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.zip): motor actualizado y mismo catálogo firmado.

## English

Rescue Disk 0.9.9 integrates mouse-wheel navigation and up to 10,000 RAM-only history lines into local CLI, login and shell sessions. Scroll up to review long output, scroll down to the prompt or press Esc to return. SSH retains its client terminal behaviour. OAuth browser handoff, Safe/YOLO modes and full sudo access are preserved.

Flash Imager 0.9.9 checks available storage before copying private images. Windows can choose another working folder when the default volume is full; cancellation does not start flashing. Existing destination files and original images are preserved. Factory media contain no personal accounts. Previous releases remain available; third-party terms remain in NOTICE.md.
