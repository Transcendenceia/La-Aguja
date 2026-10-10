# Procedimientos de rescate · LA AGUJA

[English](SHOWCASE.md) · [Primeros pasos](GETTING-STARTED.es.md) · [Documentación](README.es.md)

[Más allá del rescate: construir, configurar y experimentar](PLATFORM.es.md).
Estas son **propuestas prácticas y prompts adaptables**, no intervenciones ejecutadas, testimonios ni garantías. Las capturas de [producto real](SCREENSHOTS.es.md) provienen de QA sintético y no demuestran estos resultados. Las herramientas aportan capacidad; tú defines autorización y verificas la entrega.

## Acuerdo antes del primer comando

1. Identifica propietario, equipo, discos, datos permitidos y destino recuperable separado.
2. Define inspección autorizada, escrituras que necesitan aprobación y condiciones de parada.
3. Conserva evidencia y rollback; usa copias cuando corresponda y no escribas datos recuperados en el origen.
4. Pide al agente hechos observados, hipótesis, comandos propuestos y resultados comprobados por separado.
5. Evita enviar archivos personales a IA. Proveedores requieren cuenta, red y cuota propias; un diagnóstico local puede hacerse sin nube.

**Codex Seguro en 0.9.10 añade sandbox workspace-write y confirmación por herramienta. La cuenta aguja mantiene sudo/root completo.** Los prompts son instrucciones, no barreras de acceso. Sustituye nombres y rutas por identidades comprobadas antes de cualquier ejecución.

**0.9.10:** Codex Seguro añade sandbox `workspace-write` y aprobación humana. Las imágenes antiguas 0.9.9 permanecen sin cambios. [Política y alcance](HARNESSES.md#corrección-de-codex-seguro--2026-10-10).

<a id="first-diagnosis"></a>

## 1. Convierte «no arranca» en un diagnóstico

**Prompt**

> Inspecciona este equipo autorizado sin cambiar discos internos. Identifica USB de rescate y cada disco interno por modelo, serie, tamaño y filesystem. Separa hechos observados de hipótesis. Prioriza posibles fallos de arranque y propón la siguiente prueba mínima. No montes ni repares nada antes de mostrarme el plan.

**Herramientas:** aguja status, aguja doctor, lsblk, findmnt, lshw; información smartctl/nvme-cli acotada tras identificar dispositivos.

**Entrega esperada y verificación:** Tabla de roles de discos, modo de arranque observado, incertidumbres y pruebas ordenadas por riesgo. Contrasta cada identidad con el equipo y conserva un informe depurado en destino autorizado.

**Límites y parada:** SMART «correcto» no garantiza salud. Evita pruebas intensivas o escaneos repetidos sobre medios inestables. Sin fsck, reescritura de particiones ni instalación de bootloader automáticos.

<a id="file-rescue"></a>

## 2. Prepara un salvavidas para fotos o proyectos

**Prompt**

> Ayúdame a copiar solo las carpetas Fotos y Proyectos autorizadas desde el origen identificado a otro disco sano. Estima espacio y explica el acceso de solo lectura. Muestra un plan de copia sin borrado ni sincronización de vuelta al origen. Tras aprobarlo, lista archivos ilegibles y verifica muestras en destino. No subas su contenido a servicios IA.

**Herramientas:** lsblk, findmnt, montaje de lectura apropiado al filesystem, rsync, sha256sum sobre copias recuperadas estables.

**Entrega esperada y verificación:** Árbol de carpetas en destino, resumen de copia/errores y apertura de muestras. Los hashes validan bytes legibles, no que una foto o documento esté íntegro semánticamente.

**Límites y parada:** Nunca recuperes sobre el origen. No fuerces escritura en Windows hibernado. Un montaje de lectura tiene matices de journal según filesystem y no sustituye un bloqueador forense. Si aumentan errores, detente y considera imagen primero.

<a id="image-first"></a>

## 3. Dale a un disco averiado un plan de imagen controlado

**Prompt**

> Este origen puede estar fallando. Confirma identidad exacta y capacidad del destino separado. Propón una imagen conservadora con GNU ddrescue, mapa persistente, primera pasada y condiciones de parada. No ejecutes antes de aprobar origen, destino y presupuesto de lecturas. Analiza después la copia; no repares el original.

**Herramientas:** GNU ddrescue, ddrescuelog, lsblk y espacio disponible; TestDisk/PhotoRec después sobre copia de trabajo.

**Entrega esperada y verificación:** Imagen con mapa asociado, correspondencia origen-imagen e informe de rangos recuperados/ilegibles. Conserva el mapa para reanudar; una imagen parcial sigue siendo parcial aunque exista el archivo.

**Límites y parada:** Leer también estresa hardware dañado. No prescribas reintentos ilimitados. El destino necesita capacidad suficiente; el USB de rescate no es adecuado automáticamente. Ruidos mecánicos o inestabilidad creciente pueden requerir especialista.

<a id="remote-workbench"></a>

## 4. Un taller remoto con alguien junto al equipo

**Prompt**

> Ayúdanos con un diagnóstico remoto autorizado. El propietario está en consola. Verifica IP y huella SSH, y conexión desde mi cliente aprobado por LAN o nuestra tailnet. Inspecciona primero y presenta cada cambio de disco al propietario. Conserva una entrega depurada con lo observado, autorizado y realmente verificado.

**Herramientas:** OpenSSH, aguja status, tmux, aguja activity y Tailscale/Headscale propios opcionales; aguja run para tareas etiquetadas.

**Entrega esperada y verificación:** Conexión autenticada real, lista clara de tareas y revisión final de accesos. Verifica desde el cliente remoto, no solo el estado local del nodo.

**Límites y parada:** No requiere relay del proyecto ni abrir puertos públicos. ACL, control plane y autenticación SSH son capas distintas. La identidad tailnet vive en RAM; tmux sobrevive desconexión SSH, no reinicio. El panel de actividad no es auditoría completa persistente y puede mostrar argumentos.

<a id="locked-volume"></a>

## 5. Recupera un volumen bloqueado sin fingir que rompes el cifrado

**Prompt**

> Soy propietario de este volumen BitLocker/LUKS y tengo la clave correcta. Identifica el volumen, explica desbloqueo y copia de lectura y cómo introducir la clave de forma privada. Nunca pongas la clave en argumentos, informes ni prompts de nube. Detente si no corresponde.

**Herramientas:** lsblk, cryptsetup para LUKS o Dislocker para BitLocker, acceso apropiado al filesystem y rsync tras autorización.

**Entrega esperada y verificación:** Mapeo desbloqueado correcto, opciones de montaje comprobadas y archivos autorizados en otro destino. Valida lectura independientemente; registrar una clave no prueba desbloqueo.

**Límites y parada:** Sin fuerza bruta, bypass ni acceso a datos ajenos. Frase del perfil y contraseña SSH no son claves del disco. La cápsula no protege frente a root claves/datos ya cargados.

<a id="rescue-rehearsal"></a>

## 6. Ensaya una reparación de arranque antes de tocar el original

**Prompt**

> Usa una copia de trabajo autorizada de esta imagen para investigar el fallo de arranque. Conserva la base y propón un experimento reproducible en VM aislada de otro host. Registra cambios y compara evidencia de arranque antes/después. No devuelvas el resultado al original sin un plan aprobado aparte.

**Herramientas:** ddrescue/rsync para adquisición autorizada; herramientas filesystem, GRUB/efibootmgr según el caso; host VM e hipervisor aportados aparte.

**Entrega esperada y verificación:** Experimento repetible: identidad de la base, cambios en copia, observaciones de arranque y rollback propuesto. Éxito VM prueba la copia, no certifica firmware físico.

**Límites y parada:** Recorrido avanzado propuesto, no orquestación VM integrada ni rescate demostrado. No se promete hipervisor incluido. No arranques software recuperado no fiable en la red habitual del técnico ni habilites sesiones personales de nube en la VM de prueba.

<a id="migration-plan"></a>

## 7. Planifica una migración limpia en vez de repetir reparaciones frágiles

**Prompt**

> Inventaría este equipo autorizado y ayúdame a elegir reparación o instalación limpia. Prepara checklist de datos, dudas de hardware/controladores y mapa de particiones propuesto para el nuevo destino exacto. Separa USB de rescate y medio instalador. No formatees ni instales antes de verificar copia y aprobar destino.

**Herramientas:** lshw, lsblk, rsync; instaladores oficiales o debootstrap/arch-install-scripts para Linux autorizado por experto; wimlib donde corresponda en Windows.

**Entrega esperada y verificación:** Decisión reparar/reinstalar, copia comprobada, mapa de destino explícito, medios oficiales y condiciones de reversión. Terminar requiere luego arrancar el sistema previsto y comprobar datos/dispositivos.

**Límites y parada:** No es instalador universal automático. Una ISO Windows no se vuelve arrancable usando dd a ciegas; puede necesitar WinPE/bcdboot o medios del fabricante. No incluye licencia Windows, claves ni imagen del fabricante. Consulta la referencia de instalación.

<a id="agent-preparation"></a>

## 8. Pide a tu agente un kit de rescate repetible

**Prompt**

> Usa Flash Imager Agent Skill para preparar una imagen privada nueva desde la base 0.9.10 verificada. Pregunta idioma, teclado, clave pública SSH autorizada y red opcional. Mantén secretos fuera de chat/logs y usa protección cifrada con mi frase. Conserva la base, verifica salida e informa solo ajustes depurados y hashes. No grabes USB.

**Herramientas:** Flash Imager Agent Skill 1.0.1, Node.js 22+, arnés con archivos/terminal, IMG base verificada y espacio suficiente.

**Entrega esperada y verificación:** IMG privada nueva, verificación y checklist de grabación humana separado. Consulta la interfaz JSON real de la skill en vez de inventar opciones. Mantén imágenes y plantillas privadas fuera de repositorios públicos.

**Límites y parada:** Sin grabación USB automática ni reconstrucción de distro. Compatibilidad de formato no prueba todos los arneses/OS. Perfil cifrado no significa HOME persistente cifrado. Los perfiles reutilizables necesitan sesiones y claves tailnet vigentes.

## Plantilla de entrega

- Objetivo autorizado y versión de imagen.
- Origen, destino y permisos, sin secretos ni datos personales innecesarios.
- Estado inicial, acciones aprobadas y cambios realmente realizados.
- Evidencia observable: archivos legibles, rangos no recuperados, conexión o arranque comprobado.
- Copias conservadas, riesgos pendientes y siguiente paso concreto.
- Accesos temporales retirados y tokens persistentes revisados.

[Skill e interfaz real](../skills/flash-imager/SKILL.md) · [Instalación de sistemas](INSTALL.md) · [Actividad y privacidad](ACTIVITY.md) · [Solución de problemas](TROUBLESHOOTING.es.md)
