# Vault cleanup — procedure

Deliberately not a skill: it is needed every couple of days at most, so it stays out of the always-loaded context and is read only when pointed at. Follow it end to end when running a cleanup.

Members do no folder structuring by hand: they create notes wherever is convenient and let structure be restored afterwards. This routine is that restoration. It moves files, never rewrites their content beyond frontmatter and references.

Two things make it safe to run unattended: it only descends into parts of the vault that changed since the last run, and it refuses to touch files anyone may have open. Everything it cannot decide becomes a flag rather than a guess.

**Shared-vault rules.** The vault is synced to several members with Syncthing, where a move is a delete plus a create on every other device, and a member who still has the old path open can resurrect it by saving. So: run this **only on the automation host** (the machine that holds the git repository and runs the summaries) and **only in a quiet hour** — the scheduled slot is the quiet hour; never run it ad hoc while people are working. The open-file check below sees only the host's own Obsidian, which is why the 30-minute modification rule carries most of the weight here. With any Windows member, keep new folder names short: goal folders nest, and path + filename must stay under 260 characters.

The conventions being enforced live in `.claude/CLAUDE_shared.md` (folder-structure rule + filename prefixes + properties). Read it at the start of each run — it is the members' to change, and it wins over anything remembered here. This file is the *procedure*; that one is the *spec*.

Open ambiguities and the `last_run` stamp: `other-files/vault-cleanup log.md`. Setup docs: `other-files/vault-cleanup routine.md`.

Normally this runs headless every 2nd day, chained from `other-files/run-vault-cleanup.sh` just before the nightly review stages its snapshot — so moves land in that night's commit. A member on that host can also point a session at this file directly. Two constraints follow from the scheduled context: shell `for`/`while` loops are not on that run's permission allowlist (batch moves as `mv a b c target/`, or one call per file), and the run must never commit.

## 1. Scope the run

Read the log note's last run date. Then find what changed since:

```bash
git log --since="<last run date>" --name-only --pretty=format: | sort -u
git status --porcelain
```

Never commit — the daily-review automation owns this repo's commit cadence.

Restrict work to the **working set**: changed files, plus every note one goal-tree edge away from them (a note's `parent`, and the notes naming it as `parent`). A change elsewhere can force a move here — a new subgoal means its parent now needs a folder — so neighbors matter even when untouched. Folders with no changed files and no changed neighbors are already in their target state; skip them and say so.

On the first run, or when the log is missing, treat everything as in scope.

## 2. Exclude files someone may be editing

Moving a file out from under an open editor loses work, and other members' open tabs are invisible from here. Skip:

1. Notes open in an Obsidian tab on this machine, from `.obsidian/workspace.json` (`leaf` nodes → `state.state.file`; `lastOpenFiles` is history, not open tabs, and entries ending `.tmp.<digits>.<hex>` are sync artifacts to ignore).
2. Anything modified in the last 30 minutes (`find … -mmin -30`) — modification times are synced, so this is the one check that covers the other members.

Skipped files stay put and are listed in the run log so the next run picks them up. Skipping is cheap; a lost edit is not.

## 3. Build the goal tree

Read the `status` and `parent` properties across `projects-tasks-notes/`. The tree comes from `parent` alone — a project's subtasks are exactly the files pointing at it, which is also what its embedded base shows.

Where a note's `parent` is evident but missing, fill it in. Where `parent` and the existing folder placement disagree and neither is clearly right, **flag it — do not guess** (§6). Terminated items (`done`/`cancelled`/`failed`) stay in the tree as history; the one move a status triggers is archiving (§4, item 4).

## 4. Restore the folder structure

Per the folder-structure rule in `.claude/CLAUDE_shared.md` — reread it rather than working from memory. In outline:

1. A `,` project gets its own folder — named like the note without its `,` prefix — as soon as **any** file names it as `parent`, whatever that child's prefix; the folder holds the project note itself plus its children (recursively). Folders are never collapsed back when children terminate.
2. Notes (no prefix) and `!` tasks go in the folder of the innermost project they are specific to; items serving several projects, or consumed vault-wide by fixed paths in skills and scripts, rise to the nearest common ancestor or the `projects-tasks-notes/` root. Parentless items stay in the `projects-tasks-notes/` root.
3. `handoffs/` subfolders move with their goal folder. A handoff whose goal has no folder (a goal with no subgoals) belongs in the nearest ancestor `handoffs/`, falling back to `projects-tasks-notes/handoffs/`.
4. Finished trees go to `projects-tasks-notes/archived/`: a parentless item whose status is terminal moves there, a project with its folder (if it has one) — but only once every `!` task and `,` project in its tree is terminal too (notes don't count), so open work never disappears from the views. A tree in `archived/` that no longer qualifies moves back out.

Use `mv` (wikilinks are basename-based and survive it). Create folders as needed; `mkdir -p` the whole target path in one go.

**Non-note directories stay put.** Code, data, model, and build directories (`model/`, `scripts/`, `__pycache__/`, `example-graph/`, …) belong to whichever goal folder they already sit in — they are working material, not navigation. Move them only as passengers when their whole goal folder moves, and never reorganize their insides: relative imports and hardcoded paths break in ways a wikilink never does. They are also the likeliest sign of a session working right now, so treat a recently-touched one as a reason to skip that branch entirely this run.

## 5. Patch references the moves broke

Wikilinks survive moves; **path-style references do not**. After every batch of moves, grep the vault and `.claude/` for the old paths and fix them:

```bash
grep -rn "<old path fragment>" --include="*.md" --include="*.mjs" --include="*.sh" --include="*.json" . \
  | grep -v "^\./\.git/" | grep -v "^\./\.claude/projects/" | grep -v "^\./\.stversions/"
```

Two kinds, handled differently:

1. **Path-style wikilinks** (`[[projects-tasks-notes/foo/bar.md]]`) — rewrite to basename form (`[[bar]]`), which survives all future moves.
2. **Code/backtick paths** (reading lists in handoffs, script constants, skill instructions) — rewrite to the new path. These stay paths because headless agents open them directly.

Leave `periodic-auto-summaries/` notes and the files in `archived/` alone: they are records of what the vault looked like then, not live references.

Check skills and scripts specifically — `.claude/skills/`, `.claude/references/`, `.claude/scripts/`, `other-files/` and `CLAUDE.md` — since a stale path there breaks automation rather than just a link.

## 6. Log the run and flag what needs a human

Set `last_run: <today>` in the frontmatter of `other-files/vault-cleanup log.md`. That stamp is the cadence gate's state *and* the wrapper's success signal — a run that moved files without stamping is treated as failed and retried, so stamp it even on a run that changed nothing.

The note's body is **only genuine ambiguities** — things you refused to guess at. Append new ones to the top, one or two sentences each, dated `(MM-DD)`. Don't log what moved, what was skipped, or that a run happened: the git diff already shows the moves, and a routine narrating itself buries the few items that actually need a human. Delete entries members have resolved.

Flag anything the routine cannot resolve on its own:

1. `parent` property and folder placement conflict with no obvious right answer.
2. A note that could belong to several goals.
3. A structural oddity worth a human decision — an unexpectedly deep nesting chain, a goal whose stated independence contradicts its `parent`, a broken reference to a note that no longer exists.

Write flags as questions with a concrete recommendation, so a member can answer in one line.

Finally, report in chat: what moved, what was skipped, what is flagged. Short — a few lines.
