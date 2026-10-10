# Desarrollo y verificación

[English](DEVELOPMENT.md) · [Documentación](README.es.md)

## Pruebas acotadas

Usa Python 3, Node.js 22+ y las herramientas de fixtures requeridas. Trabaja en rama y con imágenes/USB virtuales sintéticos, nunca discos del propietario.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests
npm ci --prefix desktop
npm test --prefix desktop
npm test --prefix server
python3 scripts/audit-public.py
```

La auditoría revisa archivos del árbol de trabajo registrados por Git y patrones de secretos/rutas prohibidas; no demuestra detección de todos los secretos posibles. Añade solo fuente/arte revisado, nunca operations, evidencias QA, perfiles privados ni builds. CI añade herramientas nativas Linux y pruebas Windows: [workflow](../.github/workflows/ci.yml).

## Fuentes web y regeneración

Ocho idiomas revisados en `server/locales/`. Conserva comandos, identificadores, marca, límites y procedencia de capturas. `launch-*.json` aporta la nueva edición; `server/public/docs.html` es fuente española histórica expandida, no ruta `/docs` servida.

Regeneración completa, en este orden:

```sh
python3 scripts/build-site-locales.py
python3 scripts/build-launch-pages.py
npm test --prefix server
```

Para cambiar solo contenido launch basta el segundo generador. Ejecutar solo el antiguo sustituiría la edición nueva. Compara hashes/diffs antes de guardar; los manuales Markdown retenidos son referencias históricas, mientras primeros pasos y documentación web launch describen 0.9.9.

`server/tests/launch-ui-qa.mjs` usa Playwright existente indicado por `AGUJA_PLAYWRIGHT` y Chromium. Comprueba ocho idiomas a 1440/375/320 px, FAQ por teclado, planes, checklist, búsqueda, copia alternativa, zoom/foco y lectura sin JS. `AGUJA_QA_BASE` prueba sitio desplegado; omitirlo inicia servidor efímero loopback. `AGUJA_QA_ROOT` guarda evidencia fuera de producción. Copia exitosa se simula; no prueba hardware físico ni cuentas IA. [Notas editoriales](../server/LAUNCH-EDITORIAL.md).

## Builds Rescue e Imager

Lee [build-rootfs.sh](../scripts/build-rootfs.sh), [build-image.sh](../scripts/build-image.sh), [Imager](../desktop/README.es.md) y [publicación](PUBLISHING.md) antes de builds privilegiadas. Rootfs necesita herramientas Debian, red y espacio importante. Empaquetar exige actualmente `--personal` y valida runtime/clientes instalados, propietarios y ausencia de estado tailnet privado. No elimines guardas ni deduzcas derechos de redistribución de un build correcto. [Condiciones externas](../NOTICE.md).

Publica solo fuente revisada y assets estáticos permitidos. Conserva runtime, catálogos, releases anteriores, privacidad e imágenes inmutables versionadas salvo otro encargo explícito. Registra línea base, rollback y evidencia HTTP/navegador live: QA local no es despliegue.

QA del edge: Cloudflare ya añade beacon/challenge al HTML público, también en privacidad intacta. Se verifican hashes exactos en origen y transformaciones públicas por separado. QA pública exige `AGUJA_QA_EXPECT_EDGE_BEACON=1`; rechaza otros destinos externos. Bloques de comandos usan comentarios documentados `email_off` para conservar ejemplos SSH sin JavaScript. No se cambia configuración de zona ni CSP.
