#!/usr/bin/env bash
# daily-review.sh — Print the output path for a daily review note.
#
# Usage:
#   .claude/scripts/daily-review.sh              # today
#   .claude/scripts/daily-review.sh 2026-07-04   # specific date
#
# Prints the absolute path where the daily review note for the given
# date should be written. Creates the parent directory if missing.
# Called by the /auto-review skill (references/daily.md) to resolve where to save the note.

set -euo pipefail

VAULT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DATE="${1:-$(date +%Y-%m-%d)}"

YEAR=$(date -d "$DATE" +%Y)
QUARTER=$(( ($(date -d "$DATE" +%-m) - 1) / 3 + 1 ))
MONTH_NUM=$(date -d "$DATE" +%m)
MONTH_NAME=$(LC_ALL=en_US.UTF-8 date -d "$DATE" +%B)
WEEK=$(date -d "$DATE" +%V)

OUTDIR="${VAULT_ROOT}/periodic-auto-summaries/${YEAR}/Q${QUARTER}/${MONTH_NUM}-${MONTH_NAME}/CW-${WEEK}"
OUTFILE="${OUTDIR}/daily-${DATE}.md"

mkdir -p "$OUTDIR"
echo "$OUTFILE"
