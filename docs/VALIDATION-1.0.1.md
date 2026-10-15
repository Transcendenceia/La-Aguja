# LA AGUJA Rescue Disk 1.0.1 · validation

Flash Imager stays at 1.0.0; the standalone preparation skill stays at 1.1.0. This patch changes the live updater and its illustrated documentation, not provider authentication.

## Update manager

- Full runtime suite: **215 tests, 214 passed, one environment skip**, run as the live user in the clean release root. Focused update suite: 31 passed (a subset, not additional tests).
- 70 synthetic rendering checks: seven runtime languages, five workflow states, 1280×800 and 800×600; no measured text overflow.
- Actual framebuffer captures visually compared against the SPICE desktop. Check, per-row No / Yes RAM / Yes persistent, review, measured download, saving, verification, activation and final result observed.
- A synthetic local APT package upgraded 1.0.0 → 1.1.0 through Yes RAM. Exact installed version checked; package and test source retired afterward. Temporary worker uses private minimal devices plus a private devpts instance.
- For native QA, the official checksum-verified Codex 0.162.0 binary was temporarily selected in RAM so the real 0.162.1 upstream update could be listed, downloaded, verified and saved. The original RAM binary was restored after the test. No credentials or provider sessions were used.
- That saved component generation booted successfully on the provided VM/USB. Its 12 public updater-manifest files matched their hashes, Codex reported 0.162.1, the synthetic APT package was absent and no reboot remained pending.
- The prior saved generation's files retained their hashes; 11 non-boot-pointer CFG files and all four workspace file paths/sizes were unchanged. Profile remained locked. Internal disks were not written.
- Direct local VT, local PTY/history relay and terminal fallback checked. Direct-VT identity is preserved across sudo's own PTY; SSH is not promoted to a local framebuffer. Mouse Back exited the completed updater; panel Back returned without a duplicate Enter prompt.

## Release image

Final IMG SHA-256: `9b92419951b3462c99044f0b2f4364a5ad1d03e198b9443b80890d629c60027f`.

Final ISO SHA-256: `b55238f1ddc882035fd852db6e77450613f0d0ef5675fae042406fb77e2d6a3c`.

The final image is built from a clean public factory root plus installed public runtime files, not from the owner's RAM overlay. The final IMG was prepared with the existing public preparation skill and booted in disposable 2 GiB BIOS and UEFI fixtures. Both verified version 1.0.1, the 12 public runtime-manifest hashes, a live RAM overlay and available CFG/DATA persistence. Firmware boot coverage in this round uses IMG; ISO payload extraction and hashes are checked separately. An earlier candidate was withheld when the direct-VT sudo path was found during reboot QA.

## Documentation and limits

- Eight website languages; 48 local browser views at 1440/375/320, no-JS reading, search, clipboard mock/fallback, image zoom/Escape/focus and print checks passed. Clipboard success is a mock, not a system clipboard integration claim.
- Six new illustrated workflow captures plus an 11-capture QA ZIP with explicit provenance. Historic screenshots remain labelled and unchanged.
- RAM results are temporary. Persistent results require a compatible writable boot USB, sufficient RAM/DATA space and the next boot. Complete Rescue releases are persistent-only and separate from component updates. Failed temporary package operations may be partial.
- Native versions, virtual firmware boots and screenshots do not prove provider login/inference, Secure Boot, universal physical hardware support or a successful customer rescue. No personal capsule was unlocked for QA.
