# Solución de problemas · 0.9.9

[English](TROUBLESHOOTING.md) · [Primeros pasos](GETTING-STARTED.es.md)

Identifica la capa que falla antes de cambiar nada. Registra versión, plataforma, acción exacta y error depurado. `aguja doctor` correcto no demuestra salud del disco, recuperación lograda ni autenticación del proveedor.

| Síntoma | Primera comprobación | Siguiente acción |
| --- | --- | --- |
| Catálogo/descarga falla | Conectividad, reloj, firma y nombre exacto | Reintenta con catálogo oficial; no omitas fallos de firma/hash |
| ENOSPC al preparar | Espacio para base + copia privada y respaldo completo si está activado | Elige carpeta mayor en Windows u otro filesystem de salida; conserva la base |
| Imagen local rechazada | ¿Sigue comprimida, es ISO o descarga incompleta? | Verifica sumas, descomprime y selecciona IMG |
| USB ausente/rechazado | Modelo/serie/capacidad, conexión y rol del disco en el sistema | Detente ante dudas; no desactives protección de discos internos/sistema |
| UAC/Polkit cancelado | ¿Se aprobó elevación local del grabador? | Reintenta solo tras confirmar USB exacto; cancelar no equivale a grabar |
| Grabación interrumpida | Escritura y lectura completa no terminaron | Conserva evidencia y vuelve a preparar tras diagnóstico; no declares medio listo |
| Firmware no arranca | Arquitectura, menú USB, identidad y lectura verificada | Consulta fabricante; pruebas VM BIOS/UEFI no certifican Secure Boot ni este hardware |
| Frase rechazada | Teclado, mayúsculas y frase del perfil, no contraseña SSH | Introduce localmente con distribución correcta; no se recuperan secretos cifrados sin frase |
| Sin red | Enlace, DHCP, Wi-Fi y NetworkManager | Consulta `ip -br address`; Ethernet simplifica la primera prueba |
| SSH inaccesible | IP real, puerto, desbloqueo, credenciales y huella | Prueba LAN primero; no abras puerto público como solución predeterminada |
| Tailnet ausente tras reinicio | Red/desbloqueo, clave vigente/de un uso y ACL | Usa clave propia válida y limitada; retira nodos obsoletos bajo tu administración |
| IA instalada pero login falla | Cuenta, red, cuota y autenticación nativa | Comprueba login aparte; importar archivos no demuestra sesión válida |
| Callback OAuth falla por SSH | Localhost corresponde a máquina remota | Usa métodos sin pantalla del proveedor; no hay reenvío automático |
| Archivos cifrados/hibernados | Clave del propietario y estado del filesystem | No evadas cifrado ni fuerces montaje de escritura Windows hibernado |
| Aumentan errores de lectura | Inestabilidad física y valor del original | Detén escaneos; considera imagen conservadora ddrescue o especialista |
| Falta historial con rueda | Consola local nueva, RAM, navegación propia de aplicaciones | Baja al prompt o Esc; SSH usa su terminal y no recupera texto perdido |
| Tokens sobreviven reinicio | ¿HOME persistente sin cifrar? | Revisa persistencia; cápsula no cifra todo AGUJA_DATA |

Con perfil cifrado, el runtime fuerza `persistent_home=no`. Configuraciones antiguas/en texto plano pueden conservar HOME sin cifrar. Historial RAM no equivale a informe guardado.

## Comunica un problema reproducible

En [incidencias](https://github.com/Transcendenceia/La-Aguja/issues), indica versiones, sistema, resultado esperado/observado, pasos mínimos y VM o hardware físico. Adjunta solo diagnóstico depurado. Excluye imágenes privadas, perfiles `.aguja`, tokens, contraseñas, claves de recuperación y contenido personal. Conserva originales y respaldos.

[USB](USB.md) · [Evidencia de versión](RELEASE-0.9.9.md) · [Ejemplos](SHOWCASE.es.md)
