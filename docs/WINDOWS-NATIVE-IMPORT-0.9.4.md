# Flash Imager 0.9.4 — importación nativa de Windows

Importa la sesión existente del mismo usuario que ejecuta el Imager:

- **Antigravity:** su entrada exacta del Administrador de credenciales de Windows; solo los campos OAuth portables.
- **Codex:** selección `file`/`keyring`/`auto`, `CODEX_HOME` personalizado, credenciales UTF-16 y el almacén age cifrado con clave nativa. Exporta exclusivamente autenticación y configura el destino portable basado en archivo.
- **Claude Code / OpenCode:** archivos nativos y carpetas configuradas, con normalización de codificación.

No se modifica el perfil original. El puente es de lectura; los tokens no aparecen en argumentos, recibos del renderer ni archivos temporales en texto plano. Solo se consulta la entrada del proveedor elegido, sin enumerar otras credenciales. Una reimportación fallida invalida la aprobación anterior. Linux conserva su comportamiento de importación.

## Validación

- 97 pruebas de escritorio aprobadas en Linux, 10 omitidas específicas de Windows; 153 de Python aprobadas y 1 omitida; 8 de servidor aprobadas.
- 9/9 pruebas nativas en Windows, incluida creación/lectura/retirada de entradas temporales aisladas sin sobrescribir entradas existentes.
- GUI empaquetada en Windows: cuatro botones de importación, ambos formatos de llavero Codex, generación de imagen cifrada, fuente sin modificar, exclusión de otros secretos e invalidación de reimportación fallida.
- El runtime Python de Aguja acepta y valida el perfil cifrado generado en Windows.
- ASAR idéntico en Linux y Windows; contenedor portable Windows comprobado con 7z.
- CI Linux y Windows correctas.

Las pruebas usan datos sintéticos, no cuentas reales del propietario. No se escribió un USB físico ni se afirma vigencia de tokens de una cuenta real. Imagen de rescate 0.9.0 y Agent Skill 1.0.0 sin cambios.
