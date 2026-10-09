# Flash Imager 0.9.8 · Rescue Disk completo 0.9.7

## Descarga la imagen nueva

Esta actualización del Imager incorpora la nueva clave de firma y un catálogo público que ofrece **Rescue Disk 0.9.7 completo**. El catálogo anterior permanece disponible para los Imagers anteriores; estos continúan ofreciendo Rescue 0.9.0. Actualiza el Imager a 0.9.8 para usar la descarga integrada de la imagen nueva.

- [Imagen USB Rescue 0.9.7 (.img.zst)](https://aguja.transcendenceia.net/releases/aguja-0.9.7-amd64.img.zst)
- [ISO Rescue 0.9.7 BIOS/UEFI](https://aguja.transcendenceia.net/releases/aguja-0.9.7-amd64.iso)
- [Sumas de la imagen Rescue](https://aguja.transcendenceia.net/releases/SHA256SUMS-rescue-0.9.7.txt)
- [Notas completas de Rescue 0.9.7](https://github.com/Transcendenceia/La-Aguja/releases/tag/v0.9.7)

Centro de rescate inicial, tareas con actor/comando/salida, modo Seguro predeterminado y YOLO explícito, idioma/teclado antes del desbloqueo, perfiles cifrados y apoyo voluntario. Codex, OpenCode, Claude Code y Antigravity preinstalados, sin perfiles personales. Los componentes externos conservan sus propias licencias y condiciones: consulta `NOTICE.md`.

La versión del Rescue permanece 0.9.7: no se reconstruye ni se sustituye su imagen ya validada. Los Imagers Windows/Linux 0.9.8 conservan las funciones de 0.9.7 y actualizan únicamente versión, clave pública y dirección del catálogo. No se sobrescriben los paquetes anteriores.

El Imager une las tres partes, verifica cada SHA-256 y el hash de la imagen completa. Para una importación manual, descomprime primero `.img.zst` y selecciona el `.img`; la ISO es una descarga de arranque independiente. Instalar el Imager no actualiza un pendrive ya grabado.

La imagen final pasó arranque y reinicio BIOS/UEFI, con y sin perfiles cifrados. En esta publicación se verifican además los hashes de las descargas públicas completas y el catálogo desde el código del cliente empaquetado. El EXE Windows se compila y verifica; no se realiza otra ejecución nativa en Windows, ni se graba un USB físico ni se reinicia la VM original.

## English

Flash Imager 0.9.8 introduces a new signing key and catalogue offering the **complete Rescue Disk 0.9.7** factory image. Previous packages and their catalogue remain intact. Upgrade the Imager to 0.9.8 for the new integrated download, or manually decompress and import the IMG.

The Rescue image is unchanged from the validated 0.9.7 build. The new Imager verifies the signature, all three download parts and the full image SHA-256. Third-party software retains its own licences and terms; see `NOTICE.md`. Installing the Imager alone does not update an existing USB.
