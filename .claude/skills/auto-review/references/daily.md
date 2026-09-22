# Daily Review

> **Note:** This layer is normally run headless by the scheduled job (`other-files/run-daily-review.sh`, triggered by the `team-vault-daily-review.timer` systemd user unit on the automation host). It maintains the vault's git repo: one atomic snapshot commit per run. It can also be invoked manually.

Generate a structured review note summarizing all changes in the shared vault since the last snapshot commit, read from the git diff.

## Workflow

The flow is: **stage → analyze → write note → commit everything as one snapshot**. The review note is included in the same commit as the changes it describes, so there's one atomic commit per run.

### 1. Determine the review date and span

Use the date passed as argument, or default to today. The review covers everything since the last snapshot commit:

```bash
git log -1 --format='%cI %s'    # last snapshot time + subject
```

If the span covers more than one calendar day (laptop was off/asleep), write ONE note dated at the review date that covers the whole span, and state the span explicitly. Do not try to reconstruct per-day changes — without intermediate commits that's impossible.

If the repo has no commits yet (first run), summarize only at a high level (folder-level inventory, not per-file) and note that this is the initial snapshot.

### 2. Get the output path

```bash
.claude/scripts/daily-review.sh [YYYY-MM-DD]
```

Prints the absolute path (`periodic-auto-summaries/YYYY/Qn/MM-Month/CW-ww/daily-YYYY-MM-DD.md`) and creates the parent directory.

If an uncommitted note for this date already exists (a previous run died mid-way), regenerate/overwrite it — do not append.

### 3. Stage and analyze the vault diff

```bash
git add -A
git diff --cached --shortstat
git diff --cached --stat
```

If nothing is staged, write a brief "quiet day" note and still commit it so the daily cadence is preserved.

**Selective deep dive.** Don't read the entire diff at once. Get the file list from `--stat`, then read individual diffs (`git diff --cached -- "path/to/file"`) prioritizing:

1. `projects-tasks-notes/` — projects (`,` prefix), tasks (`!` prefix) and notes (no prefix); these carry the most signal about what the team is working toward
2. Other substantive content files

Deprioritize (skim or skip): `.obsidian/`, `.claude/` config churn, `periodic-auto-summaries/` itself, `other-files/logs`-adjacent noise.

### 4. Write the review note

**Frontmatter:**

```yaml
---
date: {YYYY-MM-DD}
type: daily-review
day: {weekday name}
span: {YYYY-MM-DD/YYYY-MM-DD}   # only when covering more than one day
---
```

**Structure:**

```markdown
# Daily Review — {YYYY-MM-DD} ({weekday})

## Summary

{2–4 sentences. Main themes, how active the day was, notable progress or milestones. If a span: say what period it covers.}

## Vault

1. {Meaningful description of what was done, grouped by project/theme. Wikilink the changed notes.}
2. {Focus on substance: "Reworked the onboarding steps and the property scheme" not "Modified README.md".}

## Statistics

1. **Vault:** {n} files changed, +{a}/−{r} lines; most active areas: {top 2–3 folders}
```

**Writing guidelines:**

1. Describe what was *accomplished*, not which files were touched.
2. Group related changes; keep it scannable.
3. Use numbered lists, not bullet points.
4. Omit empty sections.

### 5. Commit the snapshot

```bash
git add -A
git commit -m "Daily snapshot $DATE"
```

One-line message; if the day had a clear theme you may extend it (e.g. `Daily snapshot 2026-07-04 — daily-review automation setup`). Never push (this repository has no remote).

## Edge cases

1. **No changes anywhere:** short quiet-day note, still committed.
2. **First run / no prior commit:** high-level initial-snapshot note.
3. **Stale uncommitted note from a dead run:** overwrite it.
