# Publicación de LA AGUJA

Repositorio previsto: `Transcendenceia/La-Aguja`. No crear repositorios con historia
de operación privada ni subir imágenes personalizadas. La release 0.9.0 es una
candidata hasta verificar y publicar los assets. La web informativa puede abrirse
antes, con las descargas explícitamente pendientes.

## Código, licencias y comprobaciones

1. `git ls-files` debe contener únicamente fuente, documentación, tests y recursos
   públicos. `python3 scripts/audit-public.py` comprueba ese inventario; revisión
   humana y de dependencias complementan el escaneo, no queda certificada la
   ausencia universal de secretos por ejecutar una expresión regular.
2. Runtime: `python3 -m unittest discover -s tests` con `requirements-dev.txt`.
3. Imager: `cd desktop && npm ci && npm test`. Verificar Electron real con
   `xvfb-run -a node tests/electron-e2e.cjs`, y las siete lenguas con
   `node tests/i18n-ui-e2e.cjs`. QA no escribe USB físico ni autoriza proveedores.
4. Web: `cd server && npm test`. `node tests/public-ui-qa.mjs` prueba escritorio,
   móvil y assets reales sin cuenta ni cookies.
5. Preservar LICENSE, NOTICE.md y avisos de terceros. Claude Code/Antigravity
   no se empaquetan en la imagen pública; ver [HARNESSES.md](HARNESSES.md).

## Construcción

```sh
sudo scripts/build-rootfs.sh
sudo scripts/build-image.sh
cd desktop
npm ci
npm run build:linux
npm run build:win
```

La compilación del medio requiere Debian amd64, debootstrap, squashfs-tools,
grub-pc-bin, grub-efi-amd64-bin, xorriso, mtools, gdisk, dosfstools y e2fsprogs.
Las claves/identidades tailnet y los componentes de relay retirados provocan
rechazo antes de empaquetar. No usar una raíz de un dispositivo de usuario.

Cada asset de GitHub debe ser menor de 2 GiB. Publicar ISO, `.img.zst`, Imagers,
sumas, inventario de paquetes y fuentes de la etiqueta. Para el Imager, dividir
la IMG en partes verificables de 1792 MiB y firmar el catálogo:

```sh
node scripts/release-catalog.cjs dist/aguja-0.9.0-amd64.img /ruta/assets /ruta/privada/catalog-signing.pem
```

La clave privada NO va en Git, la web, logs ni los assets. La clave pública
correspondiente se fija en `desktop/resources/release-key.json` **antes** de
empaquetar Imagers. El cliente verifica firma, caducidad, repositorio, cada parte
y SHA-256 total; concatena sin credenciales de LA AGUJA.

Para reconstrucción manual: `cat aguja-0.9.0-amd64.img.part* > aguja-0.9.0-amd64.img`;
en Windows, `cmd /c copy /b aguja-0.9.0-amd64.img.part01+aguja-0.9.0-amd64.img.part02 aguja-0.9.0-amd64.img`.
Comprobar el SHA-256 de la imagen completa; no grabar una parte sola.

## Fuentes de terceros

`packages.tsv` registra versiones exactas Debian; los avisos y copyright se
conservan en `/usr/share/doc`. Añadir `third-party-sources.tsv` con enlaces
versionados a fuentes correspondientes, parches y scripts de construcción,
incluyendo paquetes copyleft. Proporcionar acceso equivalente a esas fuentes
junto a los binarios (GPL sección 6(d)); no reemplazar esto por decir que todo
está bajo GPL ni confiar en enlaces genéricos a ramas cambiantes.

## GitHub y activación web

Crear el repositorio público, subir el código revisado, etiquetar `v0.9.0`, crear
release borrador y cargar assets. Verificar sumas/descarga **sin sesión**; después
publicar la release y habilitar los enlaces del sitio informativo.

Mientras GitHub no esté publicado, arrancar con `AGUJA_GITHUB_PUBLISHED=false`:
portada, documentación y privacidad siguen públicas sin cuenta; los enlaces
GitHub quedan deshabilitados y catálogo/releases devuelven 503 con explicación.
Tras verificar los archivos públicos, retirar ese ajuste o cambiarlo a `true`
y reiniciar el servicio. `AGUJA_QA_BASE_URL=https://tu-dominio` permite probar el
dominio real con `node server/tests/public-ui-qa.mjs` desde la raíz del proyecto.

Servidor `server/index.mjs`: Node >=22, solo loopback, `AGUJA_PORT=8787`.
No necesita base de cuentas, tokens, CORS remoto ni un relay. `/account`, `/auth`,
`/connect` y las antiguas API devuelven 410; no crean sesiones. La compatibilidad
`/v1/catalog` y `/releases/*` redirige a GitHub y no sirve archivos locales.

Para sustituir el despliegue antiguo, respaldar código/estado/configuración
con permisos privados, validar el proxy y cambiar únicamente el host de LA AGUJA.
Conservar datos de cuentas previas fuera de la raíz pública como rollback, no
publicarlos. No cambiar Tailscale/Headscale del propietario. Verificar HTTP
público sin Basic Auth, todas las imágenes/documentos y downloads GitHub, y que
WebSocket/POST no pueden recrear sesiones de relay.
