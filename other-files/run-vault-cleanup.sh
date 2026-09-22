#!/usr/bin/env bash
# run-vault-cleanup.sh — Periodic vault navigation cleanup via headless Claude.
#
# Points a session at .claude/references/vault-cleanup.md (a plain reference
# file, not a skill, so it costs no context until read): restores the
# projects-tasks-notes/ folder tree from the goal tree, relocates handoffs, and
# patches the path references the moves break.
#
# Chained from run-daily-review.sh BEFORE the review stages and commits, so the
# moves land in that same night's snapshot and the review note can describe them
# with context. Never commits anything itself.
#
# Cadence: at most one run per CADENCE_DAYS (default 2). The gate reads the most
# recent run date out of the log note rather than day-of-month parity, so it is
# self-healing after the laptop is off for a stretch, and never double-runs.
#
# Test hooks: VC_FAKE_NOW="YYYY-MM-DD" fakes the clock, VC_CLAUDE_BIN points at a
# stub claude, VC_FORCE=1 bypasses the cadence gate, VC_GATE_ONLY=1 reports the
# gate decision and exits.

set -euo pipefail

# systemd does not source ~/.profile — make the claude launcher findable.
export PATH="$HOME/.local/bin:$HOME/.local/share/claude/versions:/usr/local/bin:/usr/bin:/bin:$PATH"

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$VAULT"

LOG_NOTE="other-files/vault-cleanup log.md"
CADENCE_DAYS="${CADENCE_DAYS:-2}"
NOW_DATE="${VC_FAKE_NOW:-$(date +%F)}"

# ---- cadence gate ------------------------------------------------------------
# State lives in the log note's `last_run:` frontmatter, so the note's body can
# stay signal-only (genuine ambiguities) without runs needing a visible entry.
LAST=""
if [[ -f "$LOG_NOTE" ]]; then
  LAST="$(grep -m1 -oE '^last_run: *[0-9]{4}-[0-9]{2}-[0-9]{2}' "$LOG_NOTE" \
          | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || true)"
fi

if [[ -n "$LAST" ]]; then
  AGE_DAYS=$(( ( $(date -d "$NOW_DATE" +%s) - $(date -d "$LAST" +%s) ) / 86400 ))
else
  AGE_DAYS=99999   # no log yet — first run
fi

if [[ -n "${VC_GATE_ONLY:-}" ]]; then
  echo "NOW=$NOW_DATE LAST_RUN=${LAST:-none} AGE_DAYS=$AGE_DAYS CADENCE_DAYS=$CADENCE_DAYS"
  exit 0
fi

if [[ -z "${VC_FORCE:-}" ]] && (( AGE_DAYS < CADENCE_DAYS )); then
  echo "Vault cleanup: last run $LAST ($AGE_DAYS d ago) < cadence ${CADENCE_DAYS}d — skipping."
  exit 0
fi

# ---- logging, locking, sanity checks ----------------------------------------
LOG_DIR="other-files/logs"
mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_DIR/vault-cleanup-$(date +%Y%m%dT%H%M%S).log") 2>&1

# Single instance (timer chain + manual invocation must not overlap mid-move).
exec 9>"/tmp/vault-cleanup-team-vault.lock"
if ! flock -n 9; then
  echo "Another cleanup run is active; exiting."
  exit 0
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "No git repo in the vault — the run would have no scope signal; skipping."
  exit 0
fi

CLAUDE_BIN="${VC_CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "$CLAUDE_BIN" ]]; then
  echo "ERROR: claude CLI not found on PATH. PATH=$PATH" >&2
  exit 127
fi

# --strict-mcp-config: no MCP servers in scheduled runs (faster startup, smaller surface)
claude_args=(--permission-mode acceptEdits --settings other-files/cleanup-settings.json --strict-mcp-config)

logged_today() {  # the procedure stamps last_run — that is the success signal
  grep -qE "^last_run: *$NOW_DATE" "$LOG_NOTE" 2>/dev/null
}

# ---- run ---------------------------------------------------------------------
PROCEDURE=".claude/references/vault-cleanup.md"
PROMPT="Read $PROCEDURE and carry out the vault cleanup it describes, following it end to end."

SID="$(uuidgen)"
echo "=== Vault cleanup $NOW_DATE: attempt 1 (fresh, session $SID) ==="
"$CLAUDE_BIN" -p "$PROMPT" --session-id "$SID" "${claude_args[@]}" \
  || echo "claude exited non-zero"

if logged_today; then
  echo "OK — cleanup logged for $NOW_DATE."
  exit 0
fi

# A run killed mid-way may have moved files without logging. Resuming is safer
# than a fresh start: the session knows what it already moved.
echo "=== Vault cleanup: attempt 2 (resume session $SID) ==="
"$CLAUDE_BIN" -p --resume "$SID" "${claude_args[@]}" \
  "Continue the vault cleanup: finish any moves in progress, patch references, and stamp last_run in $LOG_NOTE as $PROCEDURE specifies." \
  || echo "resume exited non-zero"

if logged_today; then
  echo "OK — cleanup logged for $NOW_DATE after resume."
  exit 0
fi

echo "ERROR: cleanup produced no run entry for $NOW_DATE. Check for a half-finished move set." >&2
exit 1
