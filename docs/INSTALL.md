# Instalación de sistemas operativos

Empieza en el [manual de usuarios](https://aguja.transcendenceia.net/docs#casos) y conserva el USB de rescate separado del medio de instalación.

LA AGUJA proporciona control previo al arranque y herramientas; no es un instalador mágico universal.
**No modifica discos internos al inicio.**

## Linux

- Debian/Ubuntu: debootstrap, particionado, chroot, paquetes, kernel y GRUB según documentación de la distro.
- Arch/CachyOS: arch-install-scripts; usa repositorios y documentación oficiales de la distribución elegida.
- Otras distribuciones: descarga su ISO oficial, valida firma/hash y utiliza su instalador o imagen híbrida.
- Puedes crear un segundo USB instalador desde LA AGUJA. Mantén el pendrive de rescate intacto.

Grabar una imagen híbrida sobre un disco borra su contenido: requiere identificación exacta,
respaldo y autorización. **Una ISO no híbrida no se instala simplemente con dd.**

## Windows

Incluye wimlib y soporte NTFS/FAT/BitLocker para inspección y despliegues.
Una ISO Windows necesita su arranque/instalador específico; no se hace arrancable con dd como una ISO Linux híbrida.
Procedimiento recomendado: preparar un segundo USB con el instalador oficial o Ventoy y seguir
la instalación del fabricante. Un despliegue WIM manual requiere GPT/ESP, aplicación de imagen
y configuración del arranque Windows; WinPE/bcdboot siguen siendo necesarios según el caso.
No incluye Windows, WinPE, licencias ni imágenes de fabricantes.

## macOS y hardware no-PC

No se promete instalar macOS en PCs no soportados, arrancar Apple Silicon ni saltar cifrado,
contraseñas de firmware o Secure Boot. ARM requiere una futura imagen específica.

## Antes de reemplazar un OS

Respalda datos y claves de recuperación, confirma disco/modelo/serie y modo UEFI/BIOS,
descarga del fabricante, verifica integridad, define esquema de particiones y un rollback.
Después verifica arranque real; instalar paquetes sin error no equivale a una instalación terminada.
