---
name: auto-review
description: Summarizing work that happened in the vault in a given time period. Will only be invoked explicitly.
---

# Auto-Review

Generates the review notes in `periodic-auto-summaries/`. Normally run headless by the scheduled pipeline (`other-files/run-daily-review.sh`, via the `team-vault-daily-review.timer` systemd user unit on the automation host); can also be invoked manually.

Read exactly one reference file, depending on the requested layer, and follow it:

1. `/auto-review daily [YYYY-MM-DD]` — daily review of vault changes since the last snapshot commit → `references/daily.md`
2. `/auto-review <week|month|quarter|year> [end-date]` — weekly/monthly/quarterly/yearly review distilled from the layer below → `references/periodic.md`
