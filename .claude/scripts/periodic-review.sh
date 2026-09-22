#!/usr/bin/env bash
# periodic-review.sh — Print the output path for a periodic review note.
#
# Usage:
#   .claude/scripts/periodic-review.sh week    2026-07-05   # week ending that Sunday
#   .claude/scripts/periodic-review.sh month   2026-07-31
#   .claude/scripts/periodic-review.sh quarter 2026-09-30
#   .claude/scripts/periodic-review.sh year    2026-12-31
#
# Second argument is the LAST DAY of the period. Prints the absolute path
# where the review note should be written and creates the parent directory.
# Called by the /auto-review skill (references/periodic.md) and the scheduled wrapper.

set -euo pipefail

VAULT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LAYER="${1:?usage: periodic-review.sh <week|month|quarter|year> <end-date>}"
END="${2:?usage: periodic-review.sh <week|month|quarter|year> <end-date>}"

YEAR=$(date -d "$END" +%Y)
QUARTER=$(( ($(date -d "$END" +%-m) - 1) / 3 + 1 ))
MONTH_NUM=$(date -d "$END" +%m)
MONTH_NAME=$(LC_ALL=en_US.UTF-8 date -d "$END" +%B)

case "$LAYER" in
  week)
    # ISO week label (%G-W%V); folder follows the end date (Sunday), matching
    # how daily notes are foldered by their own date.
    WEEK_YEAR=$(date -d "$END" +%G)
    WEEK_NUM=$(date -d "$END" +%V)
    OUTDIR="${VAULT_ROOT}/periodic-auto-summaries/${YEAR}/Q${QUARTER}/${MONTH_NUM}-${MONTH_NAME}/CW-${WEEK_NUM}"
    OUTFILE="${OUTDIR}/weekly-${WEEK_YEAR}-W${WEEK_NUM}.md"
    ;;
  month)
    OUTDIR="${VAULT_ROOT}/periodic-auto-summaries/${YEAR}/Q${QUARTER}/${MONTH_NUM}-${MONTH_NAME}"
    OUTFILE="${OUTDIR}/monthly-${YEAR}-${MONTH_NUM}.md"
    ;;
  quarter)
    OUTDIR="${VAULT_ROOT}/periodic-auto-summaries/${YEAR}/Q${QUARTER}"
    OUTFILE="${OUTDIR}/quarterly-${YEAR}-Q${QUARTER}.md"
    ;;
  year)
    OUTDIR="${VAULT_ROOT}/periodic-auto-summaries/${YEAR}"
    OUTFILE="${OUTDIR}/yearly-${YEAR}.md"
    ;;
  *)
    echo "ERROR: unknown layer '$LAYER' (want week|month|quarter|year)" >&2
    exit 2
    ;;
esac

mkdir -p "$OUTDIR"
echo "$OUTFILE"
