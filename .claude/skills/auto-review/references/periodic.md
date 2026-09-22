# Periodic Review

> **Note:** Normally run headless by the scheduled pipeline (`other-files/run-daily-review.sh`) right after the daily review — weekly on Sundays, monthly/quarterly/yearly after the last day of the period. Can also be invoked manually.

Distill the most important content from the review layer below into one note per period.

| Layer | Covers | Reads | Note file | Commit message |
|---|---|---|---|---|
| week | Mon–Sun | daily notes | `weekly-YYYY-Www.md` (in the CW folder of the week's Sunday) | `Weekly review YYYY-Www` |
| month | calendar month | weekly notes (+ tail dailies) | `monthly-YYYY-MM.md` | `Monthly review YYYY-MM` |
| quarter | calendar quarter | monthly notes | `quarterly-YYYY-Qn.md` | `Quarterly review YYYY-Qn` |
| year | calendar year | quarterly notes | `yearly-YYYY.md` | `Yearly review YYYY` |

## Workflow

### 1. Arguments

`/auto-review <week|month|quarter|year> [end-date]` — end-date is the period's **last day** (the scheduler always passes it). If missing, use the most recent completed period end:

```bash
date -d "today - $(( $(date +%u) % 7 )) days" +%F   # week: last Sunday (today if Sunday)
date -d "$(date +%Y-%m-01) - 1 day" +%F             # month: last month end (today if today ends a month)
```

(quarter/year analogous.)

### 2. Output path and period label

```bash
.claude/scripts/periodic-review.sh <layer> <end-date>
```

Prints the note path and creates the directory. Period labels: week `2026-W27` (ISO: `date -d <end> +%G-W%V`), month `2026-07`, quarter `2026-Q3`, year `2026`.

### 3. Determine coverage span

Find the latest existing note of the same layer:

```bash
find periodic-auto-summaries -name 'weekly-*.md' | sort | tail -1   # adjust pattern per layer
```

Coverage start = the day after that note's coverage end (its `date`, or its `span` end). If no such note exists, cover everything since the repo's first commit. If coverage spans more than one period (laptop was off across a boundary), write ONE note for the given end date and declare the span in frontmatter — do not backfill separate notes for skipped periods.

### 4. Read the layer below

1. **week**: daily notes dated within the span (`find periodic-auto-summaries -name 'daily-*.md'`, filter by filename date). A daily may itself have a `span:` reaching slightly before the start — treat that as covered.
2. **month**: weekly notes whose end date falls in the month; for trailing month days after the last such weekly (month ends mid-week), read those daily notes directly. A weekly may also cover a few late days of the previous month — weight by what falls in this month.
3. **quarter**: the 3 monthly notes (the last one was generated minutes earlier in the same pipeline run).
4. **year**: the 4 quarterly notes.
5. Fallback: if an expected lower-layer note is missing, drop one layer deeper (weeklies → dailies) for that stretch. If the vault is simply younger than the period, just state the actual coverage.

(Use `find`/`ls`/`git` directly — `for`/`while` shell loops are not on the scheduled run's allowlist.)

### 5. Write the note

**Frontmatter:**

```yaml
---
date: {end-date}
type: {weekly|monthly|quarterly|yearly}-review
period: {label}
span: {first-label/last-label}   # only when covering more than one period
---
```

**Structure** (title examples: `# Weekly Review — 2026-W27 (Jun 29 – Jul 5)`, `# Monthly Review — July 2026`, `# Quarterly Review — Q3 2026`, `# Yearly Review — 2026`):

```markdown
## Summary

{3–6 sentences: the period's main storyline — what moved, what stalled, notable decisions and milestones.}

## Highlights

1. {Most important item first; wikilink project notes and the lower-layer review notes.}

## Statistics

1. {Coarse aggregation from the lower notes: files changed, most active areas.}
```

**Guidelines:**

1. Distill hard — compression, not concatenation. Rough word budgets: week ≤250, month ≤350, quarter ≤450, year ≤600.
2. Importance ordering: project progress and decisions > vault housekeeping. Drop routine noise (config churn, tooling tweaks) unless it was the period's main activity.
3. Wikilink the lower-layer notes you distilled from and the key project notes.
4. Numbered lists, not bullets. Omit sections with nothing to say.
5. A quiet period still gets a brief note — the scheduler's idempotency guard requires the note to exist and be committed.

### 6. Commit

```bash
git add "<note-path>"
git commit -m "<commit message from the table>" -- "<note-path>"
```

Pathspec commit on purpose: only the review note goes into this commit, even if other changes are lying around (those belong to the next daily snapshot). Never push. Never edit the lower-layer notes.

## Edge cases

1. **Quiet period:** short note, still committed.
2. **Stale uncommitted note for this period** (a previous run died): overwrite it.
3. **Lower layer has gaps** (span notes): say so in the note rather than guessing per-period detail.
