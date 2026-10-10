# Web editorial 0.9.9 — edición estática 0.9.9

## Archivos de producción
- `public/{en,es,fr,de,pt,it,nl,zh}/{index,docs}.html`: 16 páginas SSR, 26 capítulos por guía, navegación de idiomas existente conservada.
- `public/launch-20261009-v1.css` y `public/launch-20261009-v1.js`.
- Capturas aportadas por el integrador: `public/docs-images/099/{imager,rescue-dashboard,rescue-console,rescue-wheel,rescue-safe-mode}.png`.
- Hero existente sin cambiar: `hero-recovery-20261009-v1.webp`.

No se tocó app.mjs, CSP, rutas, paquetes, runtime, desktop, runtime del repositorio. La integración y publicación se verifican por separado en la evidencia de operaciones. Privacidad y otros assets heredados se conservan. No cambiar política de idioma: / conserva el routing vigente de main, incluido ES para crawlers y Accept-Language español; cada idioma mantiene sus rutas/canonical/hreflang.

## Fuentes y regeneración
`python3 scripts/build-launch-pages.py` genera todos los idiomas; acepta códigos como argumentos para revisión parcial. Usa `server/locales/launch-*.json` para contenido nuevo y `server/locales/*.json` para capítulos y etiquetas existentes. La guía española extensa se extrae de `server/public/docs.html`, preservando tablas, pasos y comandos; ese archivo es fuente histórica, NO la ruta /docs servida. Ejecutar este generador DESPUÉS de build-site-locales.py si se regenera todo el sitio. No ejecutar el generador antiguo únicamente: sustituiría la nueva edición.

Interacciones: selector de cuatro planes, checklist efímera, búsqueda de capítulos, copiar texto con selección manual si clipboard falla, zoom con dialog/Escape/restauración de foco e impresión. No se ejecutan comandos, no se conecta a equipos, no hay API de red ni almacenamiento. Sin JS todos los planes/capítulos son legibles y las capturas enlazan al PNG.

Capturas: interfaz española y QA sintética 0.9.9, Rescue en VM e Imager en Linux. El fotograma de historial no acredita movimiento de rueda ni modo copy activo. No login real, recuperación lograda ni hardware universal. Las capturas adicionales imager-*-en no son requeridas por estas páginas.

## Pruebas
`npm test --prefix server`. Si el entorno impone proxy Node, ejecutar con variables HTTP(S)/ALL_PROXY retiradas y NODE_USE_ENV_PROXY=0 para las conexiones de prueba a loopback.

QA navegador (Playwright ya disponible, sin instalar dependencias):
`AGUJA_PLAYWRIGHT=file:///home/angie/clawd/projects/aguja-windows-import-20261009/desktop/node_modules/playwright/index.mjs AGUJA_QA_ROOT=server/qa-evidence node server/tests/launch-ui-qa.mjs`

Prueba 8 idiomas × landing/docs × 1440/375/320 px, no overflow ocultado, cajas de acciones, decode de imágenes, selector, checklist/reset, búsqueda, zoom/Escape/foco, copia con clipboard simulado y fallback real de selección. Verifica cero requests externos, cookies, almacenamiento, errores JS y respuestas fallidas. Sin JS: ocho guías y sus planes visibles. No prueba login de proveedor, escritura USB ni hardware físico.

`server/qa-evidence/` contiene evidencia local para revisión; NO incluir en el paquete de producción. No es certificación completa de accesibilidad. Revisar capturas y realizar comprobación final en dominio desplegado a cargo del integrador.

Edge QA: Cloudflare already injects a beacon/challenge into public HTML (also on unchanged privacy pages). Origin checks remain byte-exact; public checks record these transformations separately. Live browser QA must explicitly set `AGUJA_QA_EXPECT_EDGE_BEACON=1`; all other external destinations remain rejected. Command blocks use Cloudflare’s documented `email_off` comments so SSH examples remain readable without JavaScript. No zone settings or CSP are changed.
