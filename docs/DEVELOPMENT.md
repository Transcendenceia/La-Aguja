# Develop and verify

[Documentation](README.md) · [Contributing](../CONTRIBUTING.md)

## Focused checks

Use Python 3, Node.js 22+ and the fixture tools required by the tests. Work on a branch; use synthetic images/virtual USBs, never an owner's disk.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests
npm ci --prefix desktop
npm test --prefix desktop
npm test --prefix server
python3 scripts/audit-public.py
```

The audit scans tracked working-tree files for prohibited paths and credential patterns. It is a useful guard, not proof that all possible secrets have been detected. Stage only reviewed source/artwork; never operations, QA captures, private profiles or build outputs. CI adds native Linux fixture tools and native Windows import checks: [workflow](../.github/workflows/ci.yml).

## Website source and regeneration

Eight reviewed locale sets live in `server/locales/`. Preserve commands, identifiers, brand names, factual limits and actual screenshot provenance. The new landing/docs layer uses `launch-*.json`; `server/public/docs.html` remains the historical expanded Spanish source, not the served `/docs` route.

For a full rebuild run both generators, in order:

```sh
python3 scripts/build-site-locales.py
python3 scripts/build-launch-pages.py
npm test --prefix server
```

For changes only to launch content, run `build-launch-pages.py` alone. The older generator alone would replace the new editorial pages. Compare regenerated hashes/diffs before committing; retained Markdown guides are historical references, whereas the new getting-started guides and served launch documentation describe 0.9.9.

`server/tests/launch-ui-qa.mjs` uses an existing Playwright installation supplied by `AGUJA_PLAYWRIGHT` and Chromium. It checks eight languages at 1440/375/320 px, keyboard FAQ, plan selector, checklist, chapter search, copy fallback, zoom/focus and no-JS reading. `AGUJA_QA_BASE` targets an already deployed site; omit it for an ephemeral loopback server. Supply `AGUJA_QA_ROOT` outside production for evidence. Clipboard success is simulated; no physical hardware or provider account is exercised. See [editorial notes](../server/LAUNCH-EDITORIAL.md).

## Rescue and desktop builds

Read [build-rootfs.sh](../scripts/build-rootfs.sh), [build-image.sh](../scripts/build-image.sh), [Imager development](../desktop/README.md) and [publishing](PUBLISHING.md) before running privileged builds. Rootfs builds require Debian tooling, network and substantial disk space. Image packaging currently requires the explicit `--personal` argument and validates the installed factory runtime, clients, ownership and secret-free tailnet state. Do not remove those guards or infer redistribution rights from a successful build. Third-party terms remain in [NOTICE](../NOTICE.md).

Publish only a reviewed source tree and allowlisted static assets. Preserve runtime, catalogues, previous releases, privacy pages and versioned immutable images unless they are the explicit scope of a separate change. Record baseline hashes, rollback and live HTTP/browser evidence; a local test is not a deployed result.
