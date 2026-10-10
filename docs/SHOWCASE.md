# Recovery workflows · LA AGUJA

[Español](SHOWCASE.es.md) · [Getting started](GETTING-STARTED.md) · [Documentation](README.md)

[Beyond recovery: build, configure and experiment](PLATFORM.md).
These are **practical proposals and adaptable prompts**, not executed interventions, testimonials or guarantees. The [actual product captures](SCREENSHOTS.md) come from synthetic QA and do not demonstrate these outcomes. Tools provide capability; you define permission and verify the deliverable.

## Agree before the first command

1. Identify owner, computer, disks, permitted data and a separate recoverable destination.
2. Define authorised inspection, writes needing approval and stopping conditions.
3. Preserve evidence and rollback; work on copies when appropriate and never recover onto the source.
4. Ask the agent to separate observed facts, hypotheses, proposed commands and verified results.
5. Avoid sending personal files to AI. Providers require your own account, network and quota; local diagnosis can work without cloud AI.

**In the released 0.9.9 image, Safe confirms tasks but is not a sandbox; [current source adds a Codex sandbox](HARNESSES.md#corrección-de-codex-seguro--2026-10-10). The aguja account retains unrestricted sudo/root.** Prompts are instructions, not access boundaries. Replace names and paths with verified identities before any execution.

<a id="first-diagnosis"></a>

## 1. Turn “it will not boot” into a diagnosis

**Prompt**

> Inspect this authorised computer without changing internal disks. Identify the rescue USB and every internal disk by model, serial, size and filesystem. Separate observed facts from hypotheses. Rank possible boot failures and propose the smallest next test. Do not mount or repair anything before showing me the plan.

**Tools:** aguja status, aguja doctor, lsblk, findmnt, lshw; targeted smartctl/nvme-cli information after device identification.

**Expected deliverable and verification:** A disk-role table, boot-mode observations, uncertainty list and proposed tests ordered by risk. Check each identity against the machine and preserve a redacted report on an approved destination.

**Limits and stopping conditions:** SMART “passed” is not a guarantee. Avoid intensive self-tests or repeated scans on unstable media. No automatic fsck, partition rewrite or bootloader installation.

<a id="file-rescue"></a>

## 2. Build a family-photo or project lifeboat

**Prompt**

> Help me copy only the authorised Photos and Projects folders from the identified source to a different healthy disk. First estimate space and explain the read-only access method. Show a copy plan without deletion or synchronisation back to the source. After approval, list unreadable files and verify representative files at the destination. Do not upload their contents to an AI service.

**Tools:** lsblk, findmnt, filesystem-appropriate read-only mounting, rsync, sha256sum on stable recovered copies.

**Expected deliverable and verification:** A destination folder tree, copy/error summary and sample-open checks. Hash comparisons can validate byte copies where readable; they do not prove a photo or document is semantically intact.

**Limits and stopping conditions:** Never recover onto the source. Do not force a hibernated Windows volume writable. Read-only mounting can involve filesystem-specific journal behaviour and is not a forensic write blocker. Stop if errors grow; image first instead.

<a id="image-first"></a>

## 3. Give a failing disk one controlled imaging plan

**Prompt**

> This source may be failing. Confirm its exact identity and the separate destination capacity. Propose a conservative GNU ddrescue imaging plan with a persistent map file, a first-pass strategy and explicit stop conditions. Do not run it before I approve the source, destination and reading budget. Analyse the copy afterwards, never repair the original.

**Tools:** GNU ddrescue, ddrescuelog, lsblk and destination capacity checks; TestDisk/PhotoRec on a working copy afterwards.

**Expected deliverable and verification:** An image and associated map, source-to-image identification and a report of rescued/unreadable ranges. Preserve the map for resumption; mark partial recovery as partial, not successful just because a file exists.

**Limits and stopping conditions:** Reading itself stresses damaged hardware. Do not prescribe unlimited retries. Destination needs sufficient capacity; the rescue USB is not automatically suitable. Mechanical symptoms or worsening instability may require a specialist.

<a id="remote-workbench"></a>

## 4. A remote workbench with a person at the machine

**Prompt**

> Help us run an authorised remote diagnosis. The owner is at the local console. Verify the live address and SSH fingerprint, then confirm access from my approved client over LAN or our own tailnet. Inspect first; present every proposed disk change to the owner. Keep a redacted handover with what was observed, approved and actually verified.

**Tools:** OpenSSH, aguja status, tmux, aguja activity and optional own Tailscale/Headscale; aguja run for labelled tasks.

**Expected deliverable and verification:** A real authenticated connection, a clear task list and a final connection/access cleanup checklist. Verify from the remote client, not only the local node status.

**Limits and stopping conditions:** No project relay or public-port opening is required. ACLs, control plane and SSH authentication are separate. Tailnet identity is RAM-only; tmux survives SSH disconnect, not reboot. Activity display is not a durable complete audit and command arguments can be visible.

<a id="locked-volume"></a>

## 5. Recover from a locked volume without pretending to break encryption

**Prompt**

> I own this BitLocker/LUKS volume and have the matching recovery key. Identify the correct volume, explain a read-only unlock and copy plan, and tell me how to supply the key privately. Never put the key in command-line arguments, reports or cloud prompts. Stop if the key does not match.

**Tools:** lsblk, cryptsetup for LUKS or Dislocker for BitLocker, filesystem-appropriate access and rsync after explicit approval.

**Expected deliverable and verification:** Confirmation of the correct unlocked mapping, verified mount options and authorised files copied to another destination. Validate readability independently; recording a key is not proof of an unlocked volume.

**Limits and stopping conditions:** No brute force, bypass or access to someone else’s data. The profile phrase and SSH password are not disk recovery keys. Loaded keys/data are not protected from root by the configuration capsule.

<a id="rescue-rehearsal"></a>

## 6. Rehearse a boot repair before touching the original

**Prompt**

> Use an authorised working copy of this disk image to investigate the boot failure. Preserve the baseline and propose a reproducible repair experiment in an isolated VM on a separate host. Record each change and compare before/after boot evidence. Do not write the result back to the original without a separate approved plan.

**Tools:** ddrescue/rsync for authorised acquisition; filesystem, GRUB/efibootmgr tools as appropriate; a separately supplied VM host and hypervisor.

**Expected deliverable and verification:** A repeatable experiment: baseline identity, working-copy changes, boot observations and a proposed rollback. Treat VM success as evidence about the copy, not certification of physical firmware.

**Limits and stopping conditions:** Advanced proposed workflow, not a built-in VM orchestration feature or a demonstrated customer recovery. The hypervisor is not promised as bundled. Never boot untrusted recovered software on the technician’s normal network or enable personal cloud sessions in the test VM.

<a id="migration-plan"></a>

## 7. Plan a clean migration instead of repeating a fragile repair

**Prompt**

> Inventory this authorised machine and help me choose between repair and clean installation. Produce a data-backup checklist, hardware/driver uncertainties and a proposed partition map for the exact new target. Keep the rescue USB separate from installation media. Do not format or install anything until backup verification and target approval are complete.

**Tools:** lshw, lsblk, rsync; official distro installers or debootstrap/arch-install-scripts for expert-approved Linux work; wimlib for applicable Windows workflows.

**Expected deliverable and verification:** A repair-versus-reinstall decision, checked data backup, explicit target map, official media checklist and rollback conditions. Completion later requires booting the intended installed OS and checking data and devices.

**Limits and stopping conditions:** Not an automatic universal OS installer. Windows ISO is not made bootable by blindly using dd; WinPE/bcdboot or vendor media may be required. No Windows licence, recovery key or vendor image is supplied. See the installation reference.

<a id="agent-preparation"></a>

## 8. Ask your agent for a repeatable rescue kit

**Prompt**

> Use the Flash Imager Agent Skill to prepare a new private image from the verified 0.9.9 base. Ask me for language, keyboard, authorised SSH public key and optional network settings. Keep secrets out of chat/logs and use encrypted protection with my chosen phrase. Leave the base untouched, verify the output and report only redacted settings and hashes. Do not write a USB.

**Tools:** Flash Imager Agent Skill 1.0.1, Node.js 22+, file/shell-capable harness, verified base IMG and enough working storage.

**Expected deliverable and verification:** A new private IMG, verification results and a separate human USB-writing checklist. Check the skill’s actual JSON interface instead of inventing command flags. Keep private images and templates out of public repositories.

**Limits and stopping conditions:** No automatic USB flashing or distribution rebuild. Format compatibility is not proof of every harness/OS. An encrypted profile is not encrypted persistent HOME. Reusable profiles still need current provider sessions and tailnet keys.

## Handover template

- Authorised objective and image version.
- Source, destination and permission, without secrets or unnecessary personal data.
- Initial state, approved actions and changes actually made.
- Observable evidence: readable files, unrecovered ranges, verified connection or boot.
- Retained backups, remaining risks and the next concrete step.
- Temporary access removed and persistent tokens reviewed.

[Skill and actual interface](../skills/flash-imager/SKILL.md) · [OS installation](INSTALL.md) · [Activity and privacy](ACTIVITY.md) · [Troubleshooting](TROUBLESHOOTING.md)
