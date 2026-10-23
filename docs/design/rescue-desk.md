# Rescue Desk · 2026-10-23

Owner: Angie. Baseline candidate: ccb8c3c (Rescue 1.1). Branch: feat/rescue-desk-20261023.

## Request and scope

Marlon's virt-manager feedback: English canonical agent instructions (or configured language), explicit cloud-only AI requiring Internet; remove a hardware menu that only dumps JSON; bulk RAM/persistent update choices; study Gentleman Programming ODD; consistent graphical authentication and everyday browser; useful Yazi/file access; graphical manual/import cloud/NAS credentials; full practical Tailscale/Headscale settings; visual family across submenus.

## Boundaries

Rescue only, original Agujita preserved. No Imager changes, personal USB writes, publication, Dell migration, owner account login, or interruption of the owner's running virt-manager VM. Previous 1.1 image retained. No local model runtime; AI needs Internet and an authorized provider. Root access and native harness Safe/Unsafe remain unchanged. Run proportional checks for changed update/network/auth paths; build checks and visible interface inspection remain distinct from provider/hardware certification.

## Design

Keep the lightweight framebuffer cockpit. A local-only on-demand GTK Rescue Desk supplies actual forms, file pickers and visual navigation; root owns Xorg/VT lifecycle only, applications run as the owner. Persistent credentials live in the unlocked LUKS vault, otherwise RAM. Privileged configuration operations receive JSON through stdin, never secret argv. No HTTP admin server or LAN exposure.

English canonical agent/ODD docs, with instructions to reply in the owner's configured/requested language. ODD is an explicitly adapted operational workflow, not an installation/endorsement of the whole Gentle AI ecosystem, review machinery or global hooks.

Helium + Yazi pinned to official release artifacts and published GitHub SHA-256 digests; Chromium retained for explicit compatibility selection. Browser shell/start page, GTK panels, terminal and Openbox share graphite/Inter/spectrum branding. The same browser opener serves normal navigation and OAuth; existing native CLI PTY/callback ownership stays intact.

Bulk updates must respect actual constraints: a complete Rescue image cannot run only in RAM and is staged without activation before component updates in a separate derived generation. All RAM skips only the complete image and explains why. Activate only the final verified generation.

## Acceptance and evidence

- Agent guidance is English, accurately states Internet/no-local-model scope and operational ODD; managed pointers preserve owner instructions.
- No hardware JSON dump in the user menu. Hardware command remains for agents. Browser/files/cloud/tailnet actions are reachable.
- All RAM / all persistent / clear are visible; invalid release combinations cannot be applied silently.
- File browser supports mounted host files and explicit read-only target mounting; never automatically mount internal disks. Preview/edit/open use native tools and preserve permission boundaries.
- Cloud forms allow provider-appropriate manual fields and explicit file/directory import; no token values in status/logs. Tailscale supports manual URL/auth key, native browser enrollment, route/exit-node/DNS/SSH choices with control-plane limitations stated.
- Candidate can be built without replacing the prior image. Record exact paths/hashes, source/rootfs agreement, interface observations and what was not checked. No claim of real cloud OAuth, provider inference, physical driver certification or public release.

## State / next action

Implementation and isolated BIOS/UEFI validation completed. Candidate Rescue 1.1.1 built and copied to CachyOS with matching hashes. Research is in ignored operations/rescue-desk-20261023/research; source links retained in product docs. No owner VM changes made.

## Browser and native tool decision

Helium 0.20.1.1 (upstream beta) is the default: Chromium compatibility with
minimal browser chrome and a shared launcher for browsing/OAuth; Debian Chromium
remains selectable for compatibility. No webview replacement, remote browser,
root browser or disabled sandbox. Cookies stay in RAM. A graphite theme and
local branded start page are supplied; provider websites keep their own design.
Yazi v26.9.1 supplies terminal navigation/preview, backed by native PDF, image,
text, media, archive and read-only hex viewers. Root exploration remains explicit.

Pinned release assets: config/desktop-tools.json. Sources:
- https://github.com/imputnet/helium
- https://github.com/imputnet/helium-linux/releases/tag/0.20.1.1
- https://github.com/sxyazi/yazi/releases/tag/v26.9.1
- https://tailscale.com/docs/reference/tailscale-cli/up
- https://rclone.org/docs/ and https://rclone.org/commands/rclone_config/
- https://github.com/Gentleman-Programming/gentle-ai/blob/v4.2.0/docs/intended-usage.md

## Current evidence (2026-10-23)

Ten real GTK pages constructed inside the Debian rootfs under isolated Xvfb;
all ten captured. Contrast/layout corrected after visual inspection. Native
backend fixture verifies obscured passwords, private file permissions, imported
relative key copying, blank-field retention, metadata-only status, route/tag
normalization and flags accepted by the bundled tailscale CLI. No real cloud
account used. Focused update/auth/network/boot regressions are recorded in
operations/rescue-desk-20261023. Final image: 62 source/rootfs/squashfs files matched; isolated BIOS and UEFI runs passed real cockpit→Xorg/GTK→Helium/Yazi→normal cockpit return, with SSH preserved. 124 focused regressions: 120 passed, 4 omitted on the host; the six i18n checks passed inside the Debian rootfs. See operations/rescue-desk-20261023/DELIVERY.md and delivery-evidence.json. Real cloud/provider accounts and physical GPU/Wi-Fi remain unverified.
