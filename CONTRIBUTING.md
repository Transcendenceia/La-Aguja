# Contributing to LA AGUJA

[Español](CONTRIBUTING.es.md)

English is the primary repository language; Spanish is also welcome. Open an issue with version, platform, reproduction steps and expected/observed results. Redact secrets and device data before attaching logs. Never upload a private USB image or recovery keys.

For code: create a branch, keep changes focused, add a functional test when a contract changes and open a pull request. Your original contributions are offered under GPL-3.0-or-later; preserve third-party notices.

## Development

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

The website is informational, without accounts, user database or relay. Images and signed catalogue are on the official website; Imager packages are on GitHub. Network/SSH/AI profiles are processed locally. Do not restore mandatory project accounts or upload private configurations.

Translations are reviewed JSON files in `server/locales/`. Run `python3 scripts/build-site-locales.py` → `python3 scripts/build-launch-pages.py` to rebuild pages and repository guides. Preserve commands, identifiers, brand names and technical limits. The extended Spanish manual is retained separately; historical screenshots must keep their actual versions and synthetic-test provenance.

Do not test writing on an owner's disks without explicit authorisation and verified identity. Use synthetic images and virtual USBs for QA.
