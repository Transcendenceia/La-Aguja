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

On-demand Xorg sessions do not inherit the console keymap applied by setupcon.
Both normal Desk/browser and native OAuth sessions explicitly apply the validated
layout and variant from `/etc/default/keyboard` before opening applications,
using `gui_session.apply_keyboard`. Keyboard choice is independent of UI language;
do not hard-code Spanish or infer a keyboard from LANG. The build explicitly
includes `x11-xkb-utils` for setxkbmap. Applying a locale preference updates
setupcon and every active local Xorg server through the same configuration file,
so changing it from Settings or the CLI also updates applications already open.

Bulk updates must respect actual constraints: a complete Rescue image cannot run only in RAM and is staged without activation before component updates in a separate derived generation. All RAM skips only the complete image and explains why. Activate only the final verified generation.

## Acceptance and evidence

- Agent guidance is English, accurately states Internet/no-local-model scope and operational ODD; managed pointers preserve owner instructions.
- No hardware JSON dump in the user menu. Hardware command remains for agents. Browser/files/cloud/tailnet actions are reachable.
- All RAM / all persistent / clear are visible; invalid release combinations cannot be applied silently.
- File browser supports mounted host files and explicit read-only target mounting; never automatically mount internal disks. Preview/edit/open use native tools and preserve permission boundaries.
- Cloud forms allow provider-appropriate manual fields and explicit file/directory import; no token values in status/logs. Tailscale supports manual URL/auth key, native browser enrollment, route/exit-node/DNS/SSH choices with control-plane limitations stated.
- Candidate can be built without replacing the prior image. Record exact paths/hashes, source/rootfs agreement, interface observations and what was not checked. No claim of real cloud OAuth, provider inference, physical driver certification or public release.

## State / next action

The initial 1.1.1 candidate passed isolated USB BIOS/UEFI checks, but failed the owner's real CD/no-DATA boot. Do not treat those earlier checks as coverage of the CD path. The 1.1.2 correction below supersedes that delivery. Research is in ignored operations/rescue-desk-20261023/research; source links retained in product docs.

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

## Owner VM regression / 1.1.2 correction (2026-10-23)

Owner: Angie. Scope: reproduce and fix the failure in the running CachyOS
virt-manager VM, then boot the corrected artifact in that same VM. Exclusions:
no mounted target disks, USB/Imager changes, real account enrollment or transfers.
The original domain XML and previous image are retained for rollback.

Observed on the actual SPICE viewer: G/Enter immediately returned to text.
The VM used UEFI, VirtIO/virgl and the 1.1.1 IMG as read-only CD. Xorg initialized
successfully; GTK crashed constructing its Files page because Python 3.13
`Path('/data/workspace').exists()` raised `PermissionError` on private DATA.
All pages were constructed eagerly, so this prevented every graphical entry.
The previous USB/profile QA had an accessible DATA directory and missed this.

Correction: choose DATA only if traversable/readable by the owner, then the
owner workspace/home. Reuse the choice for mission notes without relaxing DATA
permissions. Keep normal-user applications and browser sandbox unchanged.
Report graphical launch failure as such instead of incorrectly claiming SSH.
Give suggested-action labels explicit dark text on their paper background.

Before rebuilding, the RAM hotfix was exercised in the owner's same VM:
Helium opened the live documentation over HTTPS; Yazi opened AGENTS.md in
Mousepad; a synthetic SFTP destination was saved through the GUI and removed;
Cloud/NAS, tailnet and bulk RAM update selection were interactive. No actual
remote account was authorized, no updates applied, no target disks mounted.

Candidate 1.1.2 IMG SHA-256:
`bd80eb20a74cdbee236a629c323ddded8e3509ce0ce7f79813e0a21bcddb1277`.
The final image boot, actual-viewer captures and delivery record are tracked in
`operations/rescue-vm-review-20261023` in the shared workspace; do not substitute
RAM-hotfix observations for that final boot check.

Final artifact verification completed: the exact 1.1.2 hash above booted as CD
in the owner's existing UEFI/VirtIO/virgl VM and in an isolated BIOS CD VM.
Both completed panel → GTK → Helium/Yazi → normal panel return → new SSH.
The owner VM also exercised R from the cockpit, the native directory chooser,
Cloud/NAS controls and both bulk-update selections (selection only, no apply).
All 52 compared runtime/version/style files in the live guest matched source.
Focused regressions: 72 passed / 4 skipped; the three permission/path regressions
also passed under Debian's Python 3.13 as the normal owner. The BIOS smoke
recorded nine successful checks and terminated its own QEMU process.

The owner VM is left running 1.1.2 with Desk open. Only its read-only CD source
was changed; XML comparisons confirmed unchanged target-disk and video settings,
and live mount listings showed no target disks mounted. The previous CD image
and pre-change domain XML remain available for rollback. IMG, ISO and IMG.ZST
are in `~/Aguja/rescue-desk-fix-20261023/` on CachyOS with SHA256SUMS. Real
OAuth/enrollment, provider inference, cloud transfers, persistent update apply
and physical hardware remain separate, unexercised checks.
