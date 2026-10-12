# LA AGUJA · Virtualización y herramientas bajo demanda

La Aguja es un entorno live de rescate con agentes IA, no una instalación en el
sistema interno. La imagen incluye una base operativa; **este catálogo opcional
no descarga ni preinstala las herramientas sugeridas**. No es una lista cerrada:
investiga alternativas si una herramienta falla o no resuelve la misión.

## Primero: estado y presupuesto

```sh
aguja status
aguja doctor
aguja tools
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
free -h
df -h / /tmp /aguja/data
```

La raíz escribible es un overlay en RAM. Instalar, extraer firmware, generar
volcados o construir imágenes puede consumirla. Usa un destino de datos con
capacidad comprobada, limita trabajos/CPU y reserva RAM para el sistema anfitrión.
No confundas una ruta en `/tmp` o el overlay con almacenamiento persistente.
Verifica destino exacto, espacio libre, permisos, conectividad y limpieza de
intermedios propios antes de descargar. No borres respaldos o procesos ajenos.

## Virtualización incluida, sin descargar paquetes

Incluidos: `qemu-system-x86_64`, interfaz gráfica de QEMU, `qemu-img`, `qemu-nbd`,
firmware **OVMF (UEFI)** y **SeaBIOS (BIOS)**. No se inicia ninguna VM automáticamente.
Comprueba el inventario con `aguja tools` y versiones con `--version`.

- KVM requiere soporte de CPU/firmware y `/dev/kvm` utilizable; **no se garantiza
  en todo equipo**. La pertenencia al grupo `kvm` permite usarlo al usuario `aguja`.
- Si no hay KVM, QEMU funciona mediante TCG, más lento. No habilites opciones de
  virtualización del firmware ni reinicies el equipo sin coordinación.
- Preferir **imágenes/copias** sobre discos físicos. Un overlay qcow2 o `-snapshot`
  no sustituye el respaldo y no prueba que el disco original sea sano.
- No exponer un mismo sistema de archivos simultáneamente a la VM y al anfitrión.
  Desmonta también vistas BitLocker/Dislocker y loops antes de dar escritura a una VM.
- Para firmware OVMF usa CODE **de solo lectura** y una **copia privada de VARS**;
  no reutilices las variables de otra VM. Consulta los archivos realmente instalados:
  `dpkg -L ovmf | rg 'CODE|VARS'`. BIOS es la opción predeterminada de QEMU x86.

Ejemplo sin disco físico, adaptando RAM/CPU al presupuesto medido:

```sh
# ISO e imagen de laboratorio propios, en un destino con espacio verificado.
qemu-img create -f qcow2 /aguja/data/lab.qcow2 20G
qemu-system-x86_64 -accel kvm -m 2048 -smp 2 \
  -drive file=/aguja/data/lab.qcow2,format=qcow2 \
  -cdrom /aguja/data/lab.iso -boot d -nic user
# Si KVM no está disponible, sustituye -accel kvm por -accel tcg.
```

No uses este ejemplo para arrancar un disco Windows físico sin adaptar firmware,
controladores, exclusividad de acceso y recuperación BitLocker. Desbloquear con
una clave de recuperación **no equivale a descifrar** ni autoriza redimensionar
una vista NTFS: usa herramientas compatibles con el cifrado real del volumen.
Referencia de uso: <https://www.qemu.org/docs/master/system/index.html>.

## Ideas de herramientas opcionales — no vienen instaladas por esta guía

| Necesidad | Proyecto oficial | Criterio de uso |
| --- | --- | --- |
| Ingeniería inversa asistida por agentes/MCP | [REA](https://github.com/morluto/rea) | Binarios, JavaScript/Electron, .NET y firmware; escoger backend y dependencias según objetivo. |
| Ingeniería inversa en consola | [Rizin](https://github.com/rizinorg/rizin) | Inspección estática de ejecutables; no hace falta ejecutar el archivo. |
| Extraer firmware y contenedores | [Unblob](https://github.com/onekey-sec/unblob) | Usar copia y controlar expansión/espacio; extracción no implica reparación. |
| Análisis de volcados de memoria | [Volatility 3](https://github.com/volatilityfoundation/volatility3) | Trabaja sobre un volcado adquirido; símbolos y dependencias pueden necesitar red. |
| CPU/RAM/procesos | [btop](https://github.com/aristocratos/btop) | Visibilidad del presupuesto del anfitrión antes de cargas pesadas. |
| Logs correlacionados | [lnav](https://github.com/tstack/lnav) | Diagnóstico sobre logs copiados o montados en solo lectura. |
| Trazado Linux | [bpftrace](https://github.com/bpftrace/bpftrace) | Depende de kernel, BTF y permisos; comprobar compatibilidad, no asumirla. |
| Pruebas acotadas de hardware | [stress-ng](https://github.com/stress-ng/stress-ng) | Limitar duración/carga y observar temperaturas; no estresar un disco fallando. |
| Respaldos verificables | [restic](https://github.com/restic/restic) | Elegir repositorio/destino y comprobar restauración, no solo salida exitosa. |
| Inspección de datos tabulares | [VisiData](https://github.com/saulpw/visidata) | Revisar CSV/JSON e inventarios sin programar un visor nuevo. |

Para recuperación de sectores, SMART, particiones, cifrado, redes e instalación
ya hay una base incluida: `ddrescue`, TestDisk/PhotoRec, `smartctl`, `nvme`,
`cryptsetup`, `dislocker`, `wimlib-imagex`, `nmcli` y más. `aguja tools` distingue
lo disponible de lo que falte; no deduzcas instalación de esta tabla.

### REA: preparación optativa, no ejecución automática

Lee el README oficial vigente antes de instalar. REA requiere Node/npm:
Node 22 >=22.19, 24 >=24.11 o 26+, según su documentación consultada para esta
versión. La Aguja incluye Node para sus arneses, pero **no garantiza npm/npx**.
Comprueba `node --version` y `command -v npm npx`; instala los requisitos que
falten solo dentro del presupuesto y alcance de la misión.

`npx rea-agents setup` es el flujo de configuración publicado por REA: revisa los
cambios de configuración del arnés/MCP antes de aplicarlos y reinicia ese arnés
cuando corresponda. No lo ejecutes a ciegas en una cuenta ajena. Ghidra, Hopper,
IDA, herramientas de firmware y otros backends tienen requisitos/licencias
propios; una instalación de REA no los proporciona todos. Los resultados de
análisis que se envíen a un modelo siguen la política de datos de ese proveedor.

## Cuando lo incluido no basta

1. Define qué evidencia falta y qué parte del problema no resuelve la herramienta.
2. Investiga documentación/repositorios oficiales actuales; verifica plataforma,
   arquitectura, dependencias, licencia y procedencia del artefacto.
3. Prueba sobre una copia o caso mínimo; no conviertas la búsqueda en reparaciones
   especulativas sobre el original. Recuerda las autorizaciones del propietario.
4. Para paquetes Debian: `sudo apt-get update` y después instalación **selectiva**
   del paquete elegido. No instalar todo este catálogo ni actualizar todos los
   arneses durante una recuperación. Prefiere un venv o directorio aislado para
   dependencias externas; revisa scripts antes de ejecutarlos.
5. Registra herramienta/versión, objetivo, destino, prueba y resultado; elimina
   solo temporales propios que ya no tengan consumidores. Comprueba la reparación
   en el sistema real cuando la misión lo permita: una VM no prueba el hardware.

Las descargas requieren Internet; las herramientas ya incluidas permiten trabajo
local sin red. Los agentes pueden investigar otras opciones: esta guía ofrece
puntos de partida, **no prohíbe herramientas nuevas**.
