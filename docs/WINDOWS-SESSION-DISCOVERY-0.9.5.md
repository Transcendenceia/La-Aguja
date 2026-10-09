# Windows — descubrimiento de sesiones 0.9.5

## Causa comprobada

La 0.9.4 solo consultaba el identificador histórico de Antigravity basado en la ruta del perfil. En la VM real la sesión estaba presente en `gemini:antigravity`. La declaración anterior de que no había sesión fue incorrecta: la búsqueda era incompleta. Las pruebas sintéticas anteriores usaban exclusivamente el identificador histórico y no cubrían este caso.

## Corrección

- Consultar primero el identificador actual y después el histórico del mismo usuario; continuar si una entrada falta o tiene formato inválido.
- Buscar archivos en las ubicaciones configuradas, las raíces del mismo usuario (`USERPROFILE`, `HOME`) y carpetas habituales de AppData. Selección explícita de carpeta conserva su alcance.
- Actualizar `HOME` desde el entorno persistente al volver a comprobar.
- Mantener tokens en el proceso principal; importar exclusivamente OAuth y no modificar el almacén original. Una raíz sintética no accede a la entrada compartida de la cuenta real. Linux conserva su búsqueda original.

## Evidencia del 9 de octubre de 2026

- Linux: 99 pruebas aprobadas; 10 específicas de Windows omitidas; cero fallos.
- Windows como usuario limitado: 11/11 pruebas nativas de importación aprobadas, incluyendo lectura real del almacén, aislamiento y regresiones de ubicaciones.
- Cuatro botones de la GUI empaquetada con sesiones sintéticas: Codex, Claude Code, Antigravity y OpenCode; Codex age, cifrado e invalidación aprobados.
- Sesión REAL de Antigravity en GUI empaquetada: botón aprobado, sin tokens en recibos, sesión importada idéntica dentro de la imagen cifrada y entrada original intacta. Repetido con el paquete definitivo. No se afirma vigencia remota de la cuenta ni se ejecutaron solicitudes facturables al proveedor.
- Contenedor portátil y archivo interior 7z íntegros; EXE y ASAR contenidos idénticos a la aplicación probada.
- SHA-256 del portátil: `37e3d7363cc7c0791709dc1ca3996a3b87ed8c5681ad3a9474816ee5eb7700bb`.
- No se escribió ningún USB ni se sustituyó ningún perfil original.

Una ejecución adicional combinando pruebas generales tuvo un fallo del fixture de enlaces simbólicos: el usuario limitado de la VM no puede crearlos (`EPERM`). No es un fallo de importación; la suite nativa específica completa sí pasó.

Esta reparación se entrega localmente en la VM. No se ha publicado una nueva release durante esta intervención.
