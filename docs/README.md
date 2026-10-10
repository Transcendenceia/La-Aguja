# Documentation

[Español](README.es.md) · [Getting started](GETTING-STARTED.md) · [Workflow ideas](SHOWCASE.md) · [Troubleshooting](TROUBLESHOOTING.md) · [Real captures](SCREENSHOTS.md)

English is primary; Spanish is secondary. The website and operational guides support eight languages.

**Start with a mission, not a failure:** [twenty Linux and Windows missions: installation, virtual labs, image building, temporary services and multi-host coordination](PLATFORM.md). [Recovery workflows](SHOWCASE.md) remain a specialist reference, not the scope of the whole platform.

| Language | Guide |
| --- | --- |
| English | [User guide](en/USER-GUIDE.md) |
| Español | [Extended manual](es/USER-GUIDE.md) |
| Français | [Guide](fr/USER-GUIDE.md) |
| Deutsch | [Anleitung](de/USER-GUIDE.md) |
| Português | [Guia](pt/USER-GUIDE.md) |
| Italiano | [Guida](it/USER-GUIDE.md) |
| Nederlands | [Handleiding](nl/USER-GUIDE.md) |
| 简体中文 | [指南](zh/USER-GUIDE.md) |

The current [interactive website guides](https://aguja.transcendenceia.net/en/docs) cover 26 workflow stages. Retained Markdown language guides contain historical references; use the website and new getting-started guides for the current 0.9.9 flow. The original Spanish manual includes expanded detail and examples. Website guides provide search, command copying and print-to-PDF in their language. The historical released PDF is Spanish, not a current 0.9.9 or multilingual PDF package.

## Technical references

- [Flash Imager](../desktop/README.md) · [Español](../desktop/README.es.md)
- [Publishing](PUBLISHING.md)
- [USB](USB.md), [rescue](RESCUE.md), [installation](INSTALL.md), [AI harnesses](HARNESSES.md) and [activity](ACTIVITY.md): retained technical references in Spanish.
- [Brand language](BRAND-LANGUAGE.md): preserve LA AGUJA/Aguja and Agujita across all languages.
- [0.9.9](RELEASE-0.9.9.md), [0.9.8](RELEASE-0.9.8.md), [0.9.7](RELEASE-0.9.7.md), [required clients 0.9.6](RESCUE-REQUIRED-CLIS-0.9.6.md): current and recent version evidence.
- [0.9.0](RELEASE-0.9.0.md), [0.9.1](RELEASE-0.9.1.md), [0.9.2](RELEASE-0.9.2.md): version-specific historical evidence, not universal compatibility claims.

Update reviewed locale sources in `server/locales/` and rebuild using `python3 scripts/build-site-locales.py` **followed by** `python3 scripts/build-launch-pages.py`. See [development](DEVELOPMENT.md). Never translate commands, identifiers, filenames or keys.
