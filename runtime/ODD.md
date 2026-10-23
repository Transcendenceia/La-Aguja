# Operational ODD for LA AGUJA

This is a scoped adaptation of Gentleman Programming's **Organic Driven
Development** to an AI-agent rescue disk, not an installation of Gentle AI.
Canonical instructions are English. Reply in the operator's requested language,
otherwise the configured live locale (`locale`, `/etc/default/locale`). Keep
commands, paths and identifiers literal. This applies to installed agents and
external agents working through SSH, MCP or an operator's console.

## Match work to authority

A question or investigation authorizes reading, not arbitrary modifications.
For an authorized intervention, explore current state, make routine reversible
choices, and continue to an observable result. Ask only for missing decisions
or new irreversible/destructive scope. Respect already-granted authorization.
Findings do not silently expand the mission. Keep the owner's permissions and
native agent Safe/Unsafe choice; this workflow grants no additional authority.

## Scale the method

Small understood work needs no task bureaucracy. For substantial work, create
**one** `<workspace>/odd/tasks/<mission>.md` before making target changes. Include:

- Operator goal, current owner, exact target identities and allowed surfaces.
- Exclusions and observable acceptance criteria.
- Measured baseline, backup alternatives and agreed rollback/retention.
- Tasks with status, evidence (commands/results, sanitized paths and hashes).
- Blocker, if any, and the next exact action.

Use `/data/workspace` when DATA is mounted; otherwise HOME/workspace is RAM.
Before resuming, reread the task and inspect the live target: a previous note
is not current state. Accept operator corrections and update affected tasks.
Never import someone else's personal memory into this platform. Engram and
external memory are optional, not installed or enabled by this workflow.

## Observe → protect → act → verify → hand over

1. Read AGENT-CONTEXT.md, MISSIONS.md, BACKUP.md and SECRETS.md in this directory.
   Use `aguja status --json`, `aguja hardware --json`, `aguja plan --json`, lsblk
   and findmnt. Identify the live USB separately from internal target disks.
2. Compare feasible backup options by measured capacity, health, downtime,
   connectivity and restoration path. A same-disk copy is not protection from
   disk failure. No backup is an explicit operator decision for the exact work.
3. Work incrementally; keep recoverable state before delicate changes. Never
   mount internal volumes, upload data, partition or reboot merely to explore.
4. For software with an existing runnable deterministic check, reproduce the
   relevant failure and verify the correction. For operational changes, use
   proportional functional checks and readback. Do not fabricate tests for
   cosmetic work. Distinguish command success from a restored service or boot.
5. Preserve owner files and credentials. Keep evidence free of passwords,
   tokens and keys. Record what was verified, not merely attempted; label
   simulated checks and physical checks separately. Summarize the next step.

Use focused local commits when appropriate in a source repository. Push,
publication, paid services and third-party messages remain separate actions.
Delegation is optional and bounded; the parent owns integration and evidence.
No global hooks, forced review system, alternate model/provider or memory
synchronization is installed implicitly. Existing project instructions remain.

Sources: [Gentle AI intended usage](https://github.com/Gentleman-Programming/gentle-ai/blob/v4.2.0/docs/intended-usage.md),
[ODD details](https://github.com/Gentleman-Programming/gentle-ai/blob/v4.2.0/docs/usage.md#organic-driven-development-odd).
