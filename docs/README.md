# Documentation

[Español](README.es.md) · [Getting started](GETTING-STARTED.md) · [20 Missions](PLATFORM.md) · [IoT ESP32](IOT.md) · [Workflow ideas](SHOWCASE.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Real captures](SCREENSHOTS.md)

English is primary; Spanish is secondary. The website and 26-chapter operational guide support **eight languages**.

**Current versions:** **Flash Imager 1.2.0** (Linux & Windows, USB + ESP32 IoT) · **Rescue Disk 1.1.2** (x86-64 live Linux + AI) · **LA AGUJA IoT v1.4.0** (11 ESP32-family boards) · **Agent Skill 1.3.0** (headless `.img` + ESP32 NVS v2).

**A portable operations command, not just a rescue disk:** boot any x86-64 PC from clean hardware ([twenty Linux and Windows missions](PLATFORM.md)), drop pocket ESP32 tailnet nodes into local networks ([LA AGUJA IoT](IOT.md)), or let AI agents prepare verified media ([Agent Skill 1.3.0](../skills/flash-imager/SKILL.md)). [Recovery workflows](SHOWCASE.md) remain a specialist reference, not the whole scope.

| Language | Interactive web guide | Repository guide |
| --- | --- | --- |
| English | [aguja.transcendenceia.net/en/docs](https://aguja.transcendenceia.net/en/docs) | [User guide](en/USER-GUIDE.md) |
| Español | [aguja.transcendenceia.net/es/docs](https://aguja.transcendenceia.net/es/docs) | [Extended manual](es/USER-GUIDE.md) |
| Français | [aguja.transcendenceia.net/fr/docs](https://aguja.transcendenceia.net/fr/docs) | [Guide](fr/USER-GUIDE.md) |
| Deutsch | [aguja.transcendenceia.net/de/docs](https://aguja.transcendenceia.net/de/docs) | [Anleitung](de/USER-GUIDE.md) |
| Português | [aguja.transcendenceia.net/pt/docs](https://aguja.transcendenceia.net/pt/docs) | [Guia](pt/USER-GUIDE.md) |
| Italiano | [aguja.transcendenceia.net/it/docs](https://aguja.transcendenceia.net/it/docs) | [Guida](it/USER-GUIDE.md) |
| Nederlands | [aguja.transcendenceia.net/nl/docs](https://aguja.transcendenceia.net/nl/docs) | [Handleiding](nl/USER-GUIDE.md) |
| 简体中文 | [aguja.transcendenceia.net/zh/docs](https://aguja.transcendenceia.net/zh/docs) | [指南](zh/USER-GUIDE.md) |

The interactive website guides cover 26 workflow stages with instant search, command copying, image zoom and print-to-PDF in all eight languages.

## Current releases & technical references

- **Flash Imager 1.2.0:** [Overview](../desktop/README.md) · [Español](../desktop/README.es.md) · [Release notes](RELEASE-IMAGER-1.2.0.md)
- **LA AGUJA IoT (ESP32 v1.4.0):** [Overview](IOT.md) · [Español](IOT.es.md) · [Module](../iot/README.md) · [Board registry](../iot/boards.json) · [Imager IoT design](design/iot-imager-integration.md)
- **Agent Skill 1.3.0:** [SKILL.md](../skills/flash-imager/SKILL.md) · [Interface](../skills/flash-imager/references/interface.md) · [IoT reference](../skills/flash-imager/references/iot.md) · [Harnesses](../skills/flash-imager/references/harnesses.md) · [Release notes](RELEASE-SKILL-1.3.0.md)
- **Rescue Disk 1.1.2:** [Release notes](RELEASE-1.1.2.md) · [1.1.1](RELEASE-1.1.1.md) · [1.1.0](RELEASE-1.1.0.md) · [Live updates](../runtime/UPDATES.md) · [Disk recovery](DISK-RECOVERY.md) · [Profile compatibility](PROFILE-COMPATIBILITY.md)
- **Operations & build:** [Development](DEVELOPMENT.md) · [Publishing](PUBLISHING.md) · [Brand language](BRAND-LANGUAGE.md)
- **Deep technical references (Spanish):** [USB](USB.md) · [Rescue](RESCUE.md) · [Installation](INSTALL.md) · [AI harnesses](HARNESSES.md) · [Activity](ACTIVITY.md)
- **Historical release evidence:** [1.0.2](RELEASE-1.0.2.md) · [1.0.1](RELEASE-1.0.1.md) · [1.0.0](RELEASE-1.0.0.md) · [0.9.11](RELEASE-0.9.11.md) · [0.9.10](RELEASE-0.9.10.md) · [0.9.9](RELEASE-0.9.9.md)

Update reviewed locale sources in `server/locales/` and rebuild using `python3 scripts/build-site-locales.py` **followed by** `python3 scripts/build-launch-pages.py`. Never translate commands, identifiers, filenames or keys.
