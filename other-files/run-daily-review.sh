#!/usr/bin/env bash
# run-daily-review.sh — Nightly review pipeline via headless Claude.
#
# Runs /auto-review daily, then any due higher-layer reviews — weekly (week ends
# Sunday), monthly/quarterly/yearly (last day of the period) — each as its own
# claude session, in ascending order so each layer can read the layer below.
#
# Designed for a systemd user timer with Persistent=true: safe to fire late
# (catch-up after suspend/boot), idempotent per layer (a layer is skipped iff
# its review note is already committed), and self-healing (a run killed
# mid-way is resumed by session ID, else rerun from scratch).
#
# Catch-up semantics: per layer, only the MOST RECENT completed period is
# considered. Periods missed entirely (laptop off across a boundary) get
# folded into the next note of that layer as a span — mirroring daily span
# notes. Suspend mid-run is normally harmless: the claude process is frozen,
# not killed; on wake its broken API connection is retried automatically.
#
# Test hooks: DR_FAKE_NOW="YYYY-MM-DD HH" fakes the
# clock, DR_CLAUDE_BIN points at a stub claude, DR_COMPUTE_ONLY=1 prints the
# computed period ends and exits.

set -euo pipefail

# systemd does not source ~/.profile — make the claude launcher findable.
export PATH="$HOME/.local/bin:$HOME/.local/share/claude/versions:/usr/local/bin:/usr/bin:/bin:$PATH"

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$VAULT"

# ---- clock (fakeable for tests) ---------------------------------------------
if [[ -n "${DR_FAKE_NOW:-}" ]]; then
  NOW_DATE="${DR_FAKE_NOW% *}"
  NOW_HOUR="${DR_FAKE_NOW#* }"
else
  NOW_DATE="$(date +%F)"
  NOW_HOUR="$(date +%H)"
fi

# Catch-up runs before noon review the previous day (the 23:00 run that
# couldn't fire because the laptop was asleep/off).
if (( 10#$NOW_HOUR < 12 )); then
  REVIEW_DATE="$(date -d "$NOW_DATE - 1 day" +%F)"
else
  REVIEW_DATE="$NOW_DATE"
fi

# ---- period ends: most recent completed period on or before REVIEW_DATE ----
dow="$(date -d "$REVIEW_DATE" +%u)"                       # 1=Mon .. 7=Sun
WEEK_END="$(date -d "$REVIEW_DATE - $((dow % 7)) days" +%F)"

if [[ "$(date -d "$REVIEW_DATE + 1 day" +%d)" == "01" ]]; then
  MONTH_END="$REVIEW_DATE"
else
  MONTH_END="$(date -d "$(date -d "$REVIEW_DATE" +%Y-%m-01) - 1 day" +%F)"
fi

y="$(date -d "$REVIEW_DATE" +%Y)"
m="$(date -d "$REVIEW_DATE" +%-m)"
q=$(( (m - 1) / 3 + 1 ))
qend="$(date -d "$y-$(printf '%02d' $((q * 3)))-01 + 1 month - 1 day" +%F)"
if [[ "$REVIEW_DATE" == "$qend" ]]; then
  QUARTER_END="$REVIEW_DATE"
else
  QUARTER_END="$(date -d "$y-$(printf '%02d' $(( (q - 1) * 3 + 1 )))-01 - 1 day" +%F)"
fi

if [[ "$REVIEW_DATE" == "$y-12-31" ]]; then
  YEAR_END="$REVIEW_DATE"
else
  YEAR_END="$(( y - 1 ))-12-31"
fi

if [[ -n "${DR_COMPUTE_ONLY:-}" ]]; then
  echo "REVIEW_DATE=$REVIEW_DATE WEEK_END=$WEEK_END MONTH_END=$MONTH_END QUARTER_END=$QUARTER_END YEAR_END=$YEAR_END"
  exit 0
fi

# ---- logging, locking, sanity checks ----------------------------------------
LOG_DIR="other-files/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily-review-$(date +%Y%m%dT%H%M%S).log"
exec > >(tee "$LOG") 2>&1

# Single instance (timer + manual invocation can't overlap).
exec 9>"/tmp/daily-review-pai-shared-vault.lock"
if ! flock -n 9; then
  echo "Another review run is active; exiting."
  exit 0
fi

# ---- unassigned-items check (nightly, pure python, no claude) ----------------
# Here — after the lock, before the git/claude checks and the cleanup's own
# every-2nd-day gate — so it runs exactly once per night whatever else is
# skipped, and a task it files lands in tonight's snapshot. Never fatal.
if [ -f other-files/check-unassigned.py ]; then
  python3 other-files/check-unassigned.py || echo "WARN: unassigned-items check failed — continuing"
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "No git repo in the vault yet (git init + initial commit needed) — skipping."
  exit 0
fi

CLAUDE_BIN="${DR_CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "$CLAUDE_BIN" ]]; then
  echo "ERROR: claude CLI not found on PATH. PATH=$PATH" >&2
  exit 127
fi

# --strict-mcp-config: no MCP servers in scheduled runs (faster startup, smaller surface)
claude_args=(--permission-mode acceptEdits --settings other-files/scheduled-settings.json --strict-mcp-config)

# ---- generic layer runner ----------------------------------------------------
note_committed() {  # note has ever been part of a commit (idempotency guard)
  [ -n "$(git log -1 --format=%H -- "$1" 2>/dev/null)" ]
}

run_layer() {  # $1=slash command, $2=note path, $3=human label
  local cmd="$1" note="$2" what="$3" sid
  if note_committed "$note"; then
    echo "$what: note already committed — skipping."
    return 0
  fi

  sid="$(uuidgen)"
  echo "=== $what: attempt 1 (fresh, session $sid) ==="
  "$CLAUDE_BIN" -p "$cmd" --session-id "$sid" "${claude_args[@]}" || echo "claude exited non-zero"
  note_committed "$note" && { echo "OK — $what committed."; return 0; }

  echo "=== $what: attempt 2 (resume session $sid) ==="
  "$CLAUDE_BIN" -p --resume "$sid" "${claude_args[@]}" \
    "Continue the $cmd run: finish writing the review note at $note and commit it as the skill specifies." \
    || echo "resume exited non-zero"
  note_committed "$note" && { echo "OK — $what committed after resume."; return 0; }

  sid="$(uuidgen)"
  echo "=== $what: attempt 3 (fresh rerun, session $sid) ==="
  "$CLAUDE_BIN" -p "$cmd" --session-id "$sid" "${claude_args[@]}" || echo "claude exited non-zero"
  note_committed "$note" && { echo "OK — $what committed after rerun."; return 0; }

  echo "ERROR: $what produced no committed note after 3 attempts." >&2
  return 1
}

# ---- vault cleanup (every 2nd day; self-gating) -------------------------------
# Runs before staging so any moves land in tonight's snapshot and the review note
# describes them. Never fatal: a failed cleanup must not cost us the review.
if [ -x other-files/run-vault-cleanup.sh ]; then
  other-files/run-vault-cleanup.sh || echo "WARN: vault cleanup failed — continuing with the review"
fi

# ---- daily -------------------------------------------------------------------
DAILY_NOTE="$(.claude/scripts/daily-review.sh "$REVIEW_DATE")"
run_layer "/auto-review daily $REVIEW_DATE" "$DAILY_NOTE" "Daily review $REVIEW_DATE" || {
  echo "ERROR: aborting — higher layers need the daily note." >&2
  exit 1
}

# ---- higher layers (weekly/monthly/quarterly/yearly) --------------------------
# Root commit date: periods that ended before the repo existed are skipped.
GENESIS="$(git show -s --format=%cs "$(git rev-list --max-parents=0 HEAD | tail -1)")"
FAILED=0

maybe_layer() {  # $1=layer keyword, $2=period end date
  local layer="$1" end="$2" note pretty
  if [[ "$end" < "$GENESIS" ]]; then
    return 0   # period predates the repo — nothing to review
  fi
  case "$layer" in
    week)    pretty="Weekly" ;;
    month)   pretty="Monthly" ;;
    quarter) pretty="Quarterly" ;;
    year)    pretty="Yearly" ;;
  esac
  note="$(.claude/scripts/periodic-review.sh "$layer" "$end")"
  run_layer "/auto-review $layer $end" "$note" "$pretty review (ending $end)" \
    || FAILED=$((FAILED + 1))
}

maybe_layer week    "$WEEK_END"
maybe_layer month   "$MONTH_END"
maybe_layer quarter "$QUARTER_END"
maybe_layer year    "$YEAR_END"

if (( FAILED > 0 )); then
  echo "ERROR: $FAILED higher-layer review(s) failed." >&2
  exit 1
fi
echo "All due reviews done."
