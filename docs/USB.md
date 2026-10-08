# Grabar y recuperar el USB

Para el recorrido guiado Windows/Linux, empieza en el [manual con capturas](https://aguja.transcendenceia.net/docs#primer-usb). Lo siguiente es el recorrido CLI avanzado en Linux, no la interfaz Windows.

Usa la **IMG**, no la ISO, para tener AGUJA_CFG editable y AGUJA_DATA persistente.
La grabación reemplaza TODO el USB. Primero identifica modelo, serie, tamaño y TRAN=usb/RM=1.

```sh
lsblk -b -o PATH,SIZE,MODEL,SERIAL,TRAN,RM,FSTYPE,LABEL,MOUNTPOINTS
sha256sum dist/aguja-0.9.0-amd64.img
sudo python3 scripts/flash-usb.py dist/aguja-0.9.0-amd64.img /dev/USB_EXACTO \
  --serial SERIE_REAL --sha256 HASH_REAL \
  --backup-dir /ruta/en/otro/disco \
  --confirm FLASH:SERIE_REAL
```

El script rechaza un disco interno, una serie distinta, particiones montadas, un destino de
backup en el mismo USB, falta de espacio o checksum incorrecto. Respalda el **dispositivo completo**
con zstd, compara el hash de la copia descomprimida y solo entonces escribe. Lee de vuelta la IMG,
repara ubicación de la GPT secundaria y expande exclusivamente la partición de datos del USB.
Requiere lsblk, findmnt, zstd, dd, blockdev, sgdisk, partprobe, udevadm, e2fsck y resize2fs.

Monta AGUJA_CFG, edita aguja.conf, guarda y desmonta antes de arrancar. `sync` antes de retirar.
No se reinicia el PC automáticamente: el usuario decide cuándo arrancar desde USB.

## Actualizar LA AGUJA conservando configuración y datos

Para un USB que ya contiene LA AGUJA, usa el actualizador en lugar de una grabación
limpia. Requiere AGUJA_CFG y AGUJA_DATA únicas en el dispositivo exacto y un DATA
limpio; se detiene antes de escribir si no puede comprobar o respaldar el original.

```sh
sudo python3 scripts/upgrade-usb.py dist/aguja-0.9.0-amd64.img /dev/USB_EXACTO \
  --serial SERIE_REAL --sha256 HASH_REAL \
  --backup-dir /ruta/en/otro/disco \
  --confirm FLASH:SERIE_REAL
```

Guarda la configuración y un archivo de datos privado, compara ambos con el
original y realiza además el respaldo completo verificado del grabador. Tras
grabar/restaurar, comprueba de nuevo la configuración, los datos y la región live.
Solo actualiza guías de agentes generadas por 0.1.1 que sigan exactamente sin
editar; las personalizadas se conservan. Los informes no imprimen credenciales.
El respaldo completo también conserva el estado previo para rollback.

## Rollback

El informe JSON contiene serie, tamaño y hash SHA256 original y confirma backup verificado.
Vuelve a identificar exactamente el USB y desmonta sus particiones. Con autorización de restauración:

```sh
zstd -dc /ruta/backup.img.zst | sudo dd of=/dev/USB_EXACTO bs=16M conv=fsync status=progress
```

Comprueba el hash completo del dispositivo contra original_sha256. Esto devuelve la tabla de
particiones y todos los bytes anteriores; también reemplaza cualquier dato nuevo de LA AGUJA.

## Secure Boot y compatibilidad

La imagen actual no ofrece una cadena Secure Boot firmada universal. Comprueba firmware y política del propietario antes de cambiar su configuración; conserva las claves de recuperación si el sistema interno usa cifrado. No modifica claves del firmware al arrancar.
UEFI 64-bit y BIOS x86-64 están previstos; UEFI 32-bit/ARM no están soportados.
Un puerto USB lento penaliza arranque y herramientas: USB 3 mejora la experiencia. RAM y capacidad se comprueban para la imagen y la carga reales; no se certifica todo hardware por superar una cifra.
