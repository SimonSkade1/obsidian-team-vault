# Vault cleanup routine

Restores vault navigation: rebuilds the `projects-tasks-notes/` folder tree from the project tree (`parent` properties), moves handoffs to the project folder they serve, moves finished parentless items into `projects-tasks-notes/archived/`, and patches the path-style references the moves break. Members do no folder structuring by hand — this is what puts it back.

## Where things are

1. **Procedure** — `.claude/references/vault-cleanup.md`. A plain reference file rather than a skill, so it costs no context until something reads it. Point a session at it to run a cleanup by hand.
2. **Conventions it enforces** — `.claude/CLAUDE_shared.md` (folder-structure rule, filename prefixes, properties). That is the spec and yours to change; the procedure reads it at each run.
3. **Wrapper** — `other-files/run-vault-cleanup.sh`. Headless runner: cadence gate, lock, retry-by-resume.
4. **Permissions** — `other-files/cleanup-settings.json`. Least-privilege set for scheduled runs: adds `mv`/`rmdir` to the standard scheduled allowlist, denies `rm` and all committing git subcommands.
5. **Open ambiguities** — [[vault-cleanup log]]. Also carries `last_run` in frontmatter, which is the cadence gate's state.
6. **Raw run output** — `other-files/logs/vault-cleanup-*.log` (gitignored).

## How it runs

Chained from `run-daily-review.sh` immediately before that script stages the nightly snapshot, so any moves land in the same commit and the daily review note describes them. Fires at most every 2 days, gated on `last_run` in the log note's frontmatter rather than day-parity — self-healing after the laptop is off, and it can't double-run. A failed cleanup is non-fatal; the review proceeds.

It never commits (the daily review owns the commit cadence) and never deletes.

Two guards keep it from clobbering live work: it skips notes open in an Obsidian tab (`.obsidian/workspace.json`) or touched in the last 30 minutes, and it leaves code/model directories alone. Anything it can't resolve — a `parent` that contradicts its folder, a note that could serve several goals — becomes a log entry instead of a guess.

## Manual use

```bash
VC_FORCE=1 other-files/run-vault-cleanup.sh    # ignore the cadence gate
VC_GATE_ONLY=1 other-files/run-vault-cleanup.sh # report the gate decision, run nothing
CADENCE_DAYS=4 other-files/run-vault-cleanup.sh # override the interval
```

Or point a session at `.claude/references/vault-cleanup.md` — same procedure, with you watching.

Schedule it only on the automation host — the one machine that keeps this vault's `.git` (its scope signal). Its open-file guard reads that host's own `.obsidian/workspace.json`, so it sees only that member's open tabs; the 30-minute mtime guard is what protects everyone else's.
