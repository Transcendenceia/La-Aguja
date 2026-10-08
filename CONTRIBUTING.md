# Contribuir a LA AGUJA

Abre un issue con versión, plataforma, pasos de reproducción y resultados
esperados/observados. Redacta secretos y datos del equipo antes de adjuntar
logs. No publiques una imagen de USB personalizada ni claves de recuperación.

Para contribuir código: crea una rama, limita el cambio, añade una prueba
funcional si cambia un contrato y abre un pull request. Tus contribuciones
propias se ofrecen bajo GPL-3.0-or-later; conserva avisos de terceros.

## Desarrollo

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests
cd desktop
npm ci
npm test
cd ../server
npm test
```

La web es informativa, sin cuentas, base de usuarios ni relay. Las descargas
son assets públicos de GitHub Releases, con sumas y catálogo Ed25519.
Los perfiles de red/SSH/IA se procesan localmente. No reintroducir cuentas
obligatorias ni enviar las configuraciones privadas a la web.

Nunca pruebes la grabación usando discos del propietario sin autorización
expresa e identidad comprobada. Para QA usa imágenes sintéticas y USB virtuales.
