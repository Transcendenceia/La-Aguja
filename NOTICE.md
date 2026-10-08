# Licensing and distribution

[Español](NOTICE.es.md)

Copyright © 2026 Transcendence IA and LA AGUJA contributors.

Project-owned code, documentation and artwork in this edition are **GPL-3.0-or-later**; see `LICENSE`. Previous MIT grants remain valid and their text is retained in `licenses/MIT-previous-releases.txt`. Earlier rights are not revoked.

This does not change the licences of Debian, Linux, firmware, libraries, Electron/Chromium, Tailscale or third-party clients/models. LA AGUJA is not an official product of AI providers or Tailscale/Headscale.

## External components

| Component | Licence evidence / handling |
| --- | --- |
| Electron and Imager npm dependencies | Preserve Electron LICENSE and package LICENSES.chromium.html; dependency inventory accompanies releases. |
| Debian and Linux kernel | Per-package `/usr/share/doc/*/copyright`; obtain corresponding sources from the Debian repositories for the built version. |
| Codex CLI | Apache-2.0 in the original project; preserve original notices. |
| OpenCode | Licence of the pinned version in its upstream project; preserve LICENSE. |
| Tailscale | Client code BSD-3-Clause; preserve notices. Headscale is managed by the user, not hosted by LA AGUJA. |
| Hardware firmware | Per-package licences; do not label the entire medium GPL or entirely free software. |
| Claude Code | Anthropic software, not GPL. Redistribution must be authorised. https://github.com/anthropics/claude-code/blob/main/LICENSE.md |
| Antigravity | Google software/service under its terms; download availability is not a redistribution grant. https://www.antigravity.google/terms |

Providers may require their own accounts/API and quotas. These are not LA AGUJA accounts: downloads, opening the Imager and preparing a USB do not require LA AGUJA registration.

## Publishing media and corresponding sources

Never release a private working image or customised USB. Build from public code, inventory licences/dependencies, include checksums and corresponding tagged source. Components without established redistribution rights are installed from their provider at the user's request, not included in public media by default. Do not publish tokens, profiles, private signing keys, operations records or private histories.

The LA AGUJA/Agujita brand identifies the project. Code/artwork permission does not imply official endorsement of forks or providers.
