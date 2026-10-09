# LA AGUJA 0.9.7 · control, idioma y apoyo

- Centro de rescate es la primera vista, incluso sin red. Consola, herramientas, arneses, desbloqueo, idioma/teclado y apoyo siguen disponibles.
- Cada lanzamiento vuelve a seleccionar Seguro por defecto. YOLO requiere elegir Inseguro. No cambia sudo ni restringe las capacidades de rescate. Los ejecutables directos mantienen sus opciones nativas.
- Seguro usa confirmaciones de herramientas del CLI. Codex 0.160.0 utiliza un hook PreToolUse con canal privado de confirmación humana: una tarea aprobada no autoriza la siguiente, y Enter/Escape/error/EOF deniegan. OpenCode usa ask global, Antigravity reglas ask y Claude permisos ask explícitos. Autenticación e inferencia con cuentas reales son independientes de estas pruebas sintéticas.
- Tareas/Comandos muestran comando, actor, duración, resultado y salida saneada, no «salida privada». Las credenciales, bloques de claves y entrada de contraseñas nunca se publican. El panel conserva una ventana acotada, no un archivo forense ilimitado.
- Imagers: protección cifrada inicial, frase editable `aguja`. Es una contraseña de fábrica pública, no una contraseña personal elegida por el usuario. El arranque directo exige selección expresa.
- La configuración validada de idioma/teclado se importa del equipo creador. Rescue 0.9.7 admite el marcador locale-preunlock-v1 y un archivo público que solo contiene idioma, distribución y variante: se aplica antes de pedir la frase de la cápsula cifrada. El menú permite corregirlo; la elección local guardada prevalece al desbloquear/reiniciar. No se exportan credenciales para aplicar el teclado.
- Apoyo voluntario al Ko-fi https://ko-fi.com/transcendenceia. QR local en Rescue e imagers, apartado web y GitHub FUNDING. Sin clave API en apps, imágenes ni repositorio; no hay conexión a Ko-fi hasta abrir el enlace.
- Trabajos pesados: comprobar memoria disponible, una tarea pesada por host, CPU/RAM/swap/IO acotados y baja prioridad. En CachyOS reservar dos núcleos físicos y al menos 2 GiB fuera del presupuesto de la tarea. No alterar límites de OpenClaw ni aplicaciones del propietario.

La imagen completa incluye clientes externos y conserva distribución personal; esta actualización no publica sus binarios ni regraba ningún pendrive. Preparar, probar en VM y arrancar en hardware son evidencias distintas.

## Validación de la entrega · 9 de octubre

Imagen final SHA-256 `0cefb68bf75118cf290d0381225ebb03341ea11843c355b257587ad2ed6b7e4c` (3.882.876.928 bytes). BIOS y UEFI, con perfil directo y cifrado: cuatro arranques y cuatro reinicios aprobados en clones QEMU/KVM. Incluye versiones de los cuatro CLI sin red, salida de comandos, regreso gráfico del panel y capturas del selector Seguro/donación. En ambos casos cifrados se comprobó el desbloqueo con `aguja`, teclado correcto antes de desbloquear y cambio efectivo de mapa de teclas conservado tras reiniciar.

Runtime: 166 aprobadas y una omitida; escritorio: 99 aprobadas y diez omitidas nativas Windows. Electron Linux empaquetado: 38 comprobaciones; preparación y lectura real de imágenes GPT/FAT directas/cifradas; contenido Windows/Linux coincidente en 28 archivos. EXE Windows compilado y verificado como paquete, no ejecutado nuevamente en Windows en esta entrega. No se realizaron nuevas inferencias con cuentas reales ni grabación física de USB.

Entrega privada en `Descargas/LA-AGUJA-0.9.7`, con imagen, cuatro formatos de imager, capturas, instrucciones y hashes. La candidata previa de esa carpeta se conservó recuperablemente. Donaciones web/GitHub publicadas sin cambiar los enlaces a versiones públicas previas; la imagen personal completa no se publicó como release.
