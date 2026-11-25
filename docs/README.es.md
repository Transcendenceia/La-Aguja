# Documentación

[English](README.md) · [Primeros pasos](GETTING-STARTED.es.md) · [20 misiones](PLATFORM.es.md) · [IoT ESP32](IOT.es.md) · [Rescate](SHOWCASE.es.md) · [Problemas](TROUBLESHOOTING.es.md) · [Capturas](SCREENSHOTS.es.md)

Inglés es el idioma principal del repositorio y español el secundario. La web y la guía operativa de 26 capítulos están disponibles en **ocho idiomas**.

**Versiones vigentes:** **Flash Imager 1.2.0** (Linux y Windows, USB + ESP32 IoT) · **Rescue Disk 1.1.2** (Linux live x86-64 + IA) · **LA AGUJA IoT v1.4.0** (11 placas ESP32) · **Agent Skill 1.3.0** (`.img` + NVS v2 ESP32 sin GUI).

**Un puesto de mando portátil, no solo un disco de rescate:** arranca cualquier PC x86-64 desde hardware limpio ([veinte misiones Linux y Windows](PLATFORM.es.md)), despliega nodos ESP32 de bolsillo en tu tailnet ([LA AGUJA IoT](IOT.es.md)) o deja que tus agentes IA preparen imágenes y particiones NVS verificadas ([Agent Skill 1.3.0](../skills/flash-imager/SKILL.md)).

## Guías y referencias vigentes

- **Guía web interactiva (26 capítulos):** [aguja.transcendenceia.net/es/docs](https://aguja.transcendenceia.net/es/docs) (búsqueda, copiar comandos, zoom e impresión a PDF) · [Manual Markdown](es/USER-GUIDE.md)
- **Flash Imager 1.2.0:** [Guía](../desktop/README.es.md) · [Notas de versión](RELEASE-IMAGER-1.2.0.md)
- **LA AGUJA IoT (ESP32 v1.4.0):** [Resumen técnico](IOT.es.md) · [Módulo IoT](../iot/README.es.md) · [Registro de placas](../iot/boards.json) · [Diseño en Imager](design/iot-imager-integration.md)
- **Agent Skill 1.3.0:** [SKILL.md](../skills/flash-imager/SKILL.md) · [Interfaz](../skills/flash-imager/references/interface.md) · [Referencia IoT](../skills/flash-imager/references/iot.md) · [Arneses](../skills/flash-imager/references/harnesses.md) · [Notas de versión](RELEASE-SKILL-1.3.0.md)
- **Rescue Disk 1.1.2:** [Notas 1.1.2](RELEASE-1.1.2.md) · [1.1.1](RELEASE-1.1.1.md) · [Actualizaciones](../runtime/UPDATES.md) · [Recuperación de discos](DISK-RECOVERY.es.md) · [Compatibilidad de perfiles](PROFILE-COMPATIBILITY.md)
- **Desarrollo y publicación:** [Desarrollo](DEVELOPMENT.es.md) · [Publicación](PUBLISHING.md) · [Lenguaje de marca](BRAND-LANGUAGE.md)
- **Referencias técnicas detalladas:** [USB](USB.md) · [Rescue](RESCUE.md) · [Instalación](INSTALL.md) · [Agentes](HARNESSES.md) · [Actividad](ACTIVITY.md)

Edita las fuentes en `server/locales/` y regenera con `python3 scripts/build-site-locales.py` seguido de `python3 scripts/build-launch-pages.py`. No traduzcas comandos, claves, rutas ni LA AGUJA/Agujita.
