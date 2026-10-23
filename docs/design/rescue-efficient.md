# Rescue eficiente — menú único y herramientas directas

Owner: Angie. Baseline: 8053273 / 1.1.2. Scope: Rescue runtime, build cache,
new candidate and the owner's existing test VM. No Imager/USB/publication,
no target filesystem mounting, real account enrollment or provider inference.

Request: remove the redundant graphical hub, group harnesses and settings,
open the root file explorer directly, stabilize mouse/video/browser, open
native OAuth automatically and return copied codes to the same native PTY,
make update installation and real progress obvious. Prefer task completion
over extra configuration screens.

Design: one framebuffer cockpit; Agents, Connections, Tools and Settings
submenus use the same renderer. Browser and root Yazi go directly to their
native windows. Cloud/network forms construct only the requested form, with
no hub/sidebar. Updates use the existing framebuffer controller with a fixed
installation footer and measured progress. Keep browser sandbox unprivileged.

Observed failure: RAM update installed system packages, then failed its harness
space check. Failed session caches remained; public status discarded the error.
Preflight the selected operation before mutation, clean only updater-owned
RAM archives, retain bounded receipts and report partial completion accurately.
Stop full menu font/layout rendering on every idle mouse poll.

Acceptance: actual VM menu → direct browser and root explorer → return;
grouped harnesses preserve Safe/Unsafe choice; automatic native OAuth opening
and synthetic copied-code return to the original PTY without keyboard shortcut;
update button and progress always visible, real small RAM package installation
verified by dpkg, failures show reason and no false success; CPU/latency before
and after measured. Final boot on delivered hash, source/runtime agreement,
BIOS/UEFI smoke and no host disks touched.

Rollback: retain 1.1.2 artifact and original domain XML. RAM prototypes are not
final delivery; rebuild and boot new version before closure.

Implemented in 1.2.0. One menu with eight entries, native grouped pickers,
direct browser/root Yazi, single-purpose connection forms, fixed native update
footer and measured progress. Window manager readiness gates fast applications;
input polls at 20 ms while panel composition is cached and mouse writes only
its dirty rectangle. Network refresh runs outside input handling. Regular
browsing reuses one RAM profile with bounded cache; OAuth uses its own short-lived
private profile.

Measured RAM prototype in the owner's VM: idle menu CPU 20.2% → 7.4% of one
core (5/8-second process CPU deltas, not ps lifetime averages). Synthetic browser
code copy reached the original CLI PTY automatically once, without a shortcut;
normal close returned to text. Root Yazi navigated /tmp, previewed a synthetic
file and opened it in a root editor. No target volume was mounted.

264 automated checks: 263 passed, 1 omitted (environment-specific integration).
Initial candidate BIOS hash a521f12a235d17158daf56e1418b6d88b03c784e6c578f922e26dcc38059ae0a:
menu, Agents submenu, direct browser/root explorer, single Tailscale form and
normal returns/SSH passed. Final owner UEFI boot has all 54 runtime/source
files compared; only sdb CD source changed in domain XML. The owner's two disk
sources and video configuration remain unchanged.

The RAM prototype's All update installed all four harnesses successfully and
removed archive caches. UEFI All update on the first 1.2.0 candidate installed
10 system packages and all four harnesses; dpkg/native versions and empty
archive caches were independently verified. Browser code-copy fixture returned
the synthetic code to the original native CLI PTY automatically.

Final correction: GTK chooser calls show_all and starts in an accessible home;
D-Bus machine-id is a symlink to /etc/machine-id so each boot shares the valid
system identity. Only desk.py changed among the 54 previously recorded runtime
files; updater/OAuth hashes remained identical. Final IMG SHA-256:
bf1e8b105a035a08e599bb8d2047d565ced83ab3ef5128a021b46f1d22dc231e.
Final BIOS smoke passed; owner VM booted this hash under UEFI with D-Bus valid,
62 source/rootfs/squashfs/live files matching, successful directory selection
and synthetic rclone import, HTTPS browsing and root Yazi preview/edit.

264 checks in Debian rootfs: 263 passed, one environment-specific integration
omitted. Mount /proc and /dev with devpts in a private namespace for the full
suite; a prior chroot run without them failed PTY/process-identity checks and
is preserved separately rather than counted as passing.

Final deliverables are on CachyOS:
/home/jmarlonb/Aguja/rescue-efficient-20261023/final/.
IMG/ISO/ZST and two manifests verify 5/5 SHA-256 entries; the ZST decompresses
exactly to the tested IMG. Earlier local dist-efficient/ is superseded and
is not the final image. A local full copy failed for disk space; transfer and
compression processes later exited 137. Those attempts were not counted as
successful; destination artifacts were checked independently. No USB writes,
publication, Imager changes, target disk mounts or real account enrollment.
Full result: /home/angie/clawd/operations/rescue-efficient-20261023/DELIVERY.md.


