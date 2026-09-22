#!/usr/bin/env bash
# Detached self-relay for handoffs. Two modes (env RELAY_MODE):
#
#   fresh-bg (DEFAULT) — spawn a FRESH session as a background agent
#     (`claude --bg`, cwd = vault root) with the prompt file as its prompt.
#     No transcript surgery (fresh context by construction). The wrapper then
#     (a) resolves the new session id via `claude agents --json`,
#     (b) fabricates a Claudian meta.json in .claudian/sessions/ so the chat
#         appears in Claudian when the chat list is next opened (history
#         dropdown / /resume rescan patch; reload also works),
#     (c) runs an idle-stop watchdog: a finished bg session idles forever and
#         while alive blocks `--resume` ("still running as a background
#         agent"), so once it is idle+done with a quiet transcript for
#         RELAY_IDLE_GRACE_S it gets `claude stop`ped → resumable in Claudian.
#         Empirically (CC 2.1.218) status stays busy/working while background
#         tasks (workflows) are in flight even between turns, so the watchdog
#         does not kill sessions with pending work; CLAUDE_CODE_PRINT_BG_WAIT_
#         CEILING_MS is irrelevant here (bg sessions do not exit on turn end).
#     In-place vault editing requires `"worktree": {"bgIsolation": "none"}` in
#     .claude/settings.json (checked below; watchdog also warns if a hop's cwd
#     leaves the vault root — see the isolation comments further down).
#
#   surgery — legacy same-session relay: wait for quiescence, run
#     handoff_surgery.py (synthetic compaction appended to THIS session's
#     jsonl), then resume the SAME session headless with the prompt.
#
# Usage: handoff_respawn.sh SESSION_ID PROMPT_FILE HOPS_REMAINING [MODEL] [PERMISSION_MODE] [SUMMARY_FILE] [TITLE]
#   SESSION_ID: the CALLING session (quiescence-wait + model-inherit source;
#     in surgery mode also the session being resumed).
#   MODEL default "inherit": reuse the model of the calling session's last
#     assistant turn (read from its transcript after quiescence); "-" = same.
#   PERMISSION_MODE default "auto"; "-" = auto.
#   SUMMARY_FILE: surgery mode only (triggers the surgery); ignored in
#     fresh-bg mode (the prompt file already contains the handoff note).
#   TITLE: fresh-bg only — Claudian chat title (default: relay: <prompt stem>).
# Env: RELAY_MODE=fresh-bg|surgery (default fresh-bg)
#      CLAUDE_EFFORT — inherited reasoning effort (fallback max)
#      RELAY_IDLE_GRACE_S (default 20), RELAY_WATCHDOG_MAX_H (default 48)
#
# Refuses if .claude/handoffs/STOP exists or HOPS_REMAINING <= 0.
# Hop log: .claude/handoffs/relay.log
set -u
SID="${1:?session id}"
PF="${2:?prompt file}"
HOPS="${3:?hops remaining}"
MODEL="${4:-inherit}"; [ "$MODEL" = "-" ] && MODEL="inherit"
PERM="${5:-auto}"; [ "$PERM" = "-" ] && PERM="auto"
SUMMARY="${6:-}"
TITLE="${7:-}"
MODE="${RELAY_MODE:-fresh-bg}"
EFFORT="${CLAUDE_EFFORT:-max}" # inherit the launching session's effort; fall back to max if unset
IDLE_GRACE="${RELAY_IDLE_GRACE_S:-20}"
WD_MAX_H="${RELAY_WATCHDOG_MAX_H:-48}"

BASE="$(cd "$(dirname "$0")/.." && pwd)" # .claude
VAULT="$(cd "$BASE/.." && pwd)"          # vault root
CLAUDIAN_SESS="$VAULT/.claudian/sessions"
HDIR="$BASE/handoffs"
SURG="$BASE/scripts/handoff_surgery.py"
mkdir -p "$HDIR"
LOG="$HDIR/relay.log"
ts() { date '+%F %T'; }

case "$MODE" in fresh-bg|surgery) ;; *) echo "unknown RELAY_MODE=$MODE" >&2; exit 2 ;; esac
if [ -f "$HDIR/STOP" ]; then
  echo "$(ts) [$SID] STOP file present — not respawning" | tee -a "$LOG" >&2
  exit 3
fi
if [ "$HOPS" -le 0 ]; then
  echo "$(ts) [$SID] hop budget exhausted — not respawning" | tee -a "$LOG" >&2
  exit 4
fi
JSONL=$(ls "$HOME"/.claude/projects/*/"$SID".jsonl 2>/dev/null | head -1)
if [ -z "$JSONL" ]; then
  echo "$(ts) [$SID] transcript not found — not respawning" | tee -a "$LOG" >&2
  exit 5
fi
if [ ! -f "$PF" ]; then
  echo "$(ts) [$SID] prompt file $PF not found" | tee -a "$LOG" >&2
  exit 6
fi
PF="$(cd "$(dirname "$PF")" && pwd)/$(basename "$PF")" # absolutize: fresh-bg cds to vault root before reading it
if [ "$MODE" = "surgery" ] && [ -n "$SUMMARY" ] && [ ! -f "$SUMMARY" ]; then
  echo "$(ts) [$SID] summary file $SUMMARY not found" | tee -a "$LOG" >&2
  exit 7
fi
if [ "$MODE" = "fresh-bg" ] && [ -n "$SUMMARY" ]; then
  echo "$(ts) [$SID] note: summary file given but RELAY_MODE=fresh-bg — no surgery, summary arg ignored (set RELAY_MODE=surgery for same-session relay)" | tee -a "$LOG" >&2
fi
# CC (≥2.1.218) guards Edit/Write in background sessions inside a git repo:
# without the repo-level opt-out `"worktree": {"bgIsolation": "none"}` in
# .claude/settings.json, the first Edit/Write is blocked ("Call EnterWorktree
# first"), the hop isolates into .claude/worktrees/<name>/ and its edits never
# land in the vault (transcript moves to the worktree's project slug too).
# This is INDEPENDENT of permission mode, and the guard cannot be disabled from
# here: CLAUDE_BG_ISOLATION in the spawning env is not forwarded to the bg
# session (the daemon controls that variable). The settings key is the fix —
# verified empirically 2026-07-24 (CC 2.1.218/219).
if [ "$MODE" = "fresh-bg" ] && ! python3 -c "
import json,sys
s=json.load(open(sys.argv[1]))
sys.exit(0 if s.get('worktree',{}).get('bgIsolation')=='none' else 1)" "$BASE/settings.json" 2>/dev/null; then
  echo "$(ts) [$SID] WARNING: .claude/settings.json lacks \"worktree\": {\"bgIsolation\": \"none\"} — CC will force this bg hop's Edit/Write into a git worktree (any permission mode), so its edits will NOT land in the vault. Restore that settings key." | tee -a "$LOG" >&2
fi
[ -z "$TITLE" ] && TITLE="relay: $(basename "$PF" .md)"

export SID PF MODEL PERM SUMMARY EFFORT JSONL LOG HDIR SURG MODE TITLE VAULT CLAUDIAN_SESS IDLE_GRACE WD_MAX_H
nohup setsid bash -c '
  ts() { date "+%F %T"; }
  # Quiescence: transcript mtime unchanged across a 4s poll AND >=15s old (max ~20 min).
  # In fresh-bg mode this is not about transcript safety (nothing is mutated) —
  # it prevents predecessor and successor editing the vault concurrently.
  quiet=0
  for i in $(seq 1 300); do
    a=$(stat -c %Y "$JSONL" 2>/dev/null || echo 0)
    sleep 4
    b=$(stat -c %Y "$JSONL" 2>/dev/null || echo 0)
    if [ "$a" = "$b" ] && [ "$b" != 0 ]; then
      age=$(( $(date +%s) - b ))
      if [ "$age" -ge 15 ]; then quiet=1; break; fi
    fi
  done
  if [ "$quiet" -ne 1 ]; then
    echo "$(ts) [$SID] transcript never went quiet within ~20 min — aborting relay (no respawn)" >>"$LOG"
    exit 9
  fi
  if [ -f "$HDIR/STOP" ]; then
    echo "$(ts) [$SID] STOP appeared during quiescence wait — aborting" >>"$LOG"
    exit 3
  fi
  if [ "$MODE" = "surgery" ] && [ -n "$SUMMARY" ]; then
    out=$(python3 "$SURG" "$SID" "$SUMMARY" 2>&1)
    echo "$(ts) [$SID] surgery: $out" >>"$LOG"
    case "$out" in
      OK*) ;;
      *) echo "$(ts) [$SID] surgery failed — aborting hop" >>"$LOG"; exit 8 ;;
    esac
  fi
  if [ "$MODEL" = "inherit" ]; then
    MODEL=$(python3 -c "
import json,sys
m=\"\"
for line in open(sys.argv[1]):
    try: d=json.loads(line)
    except: continue
    if d.get(\"type\")==\"assistant\":
        x=d.get(\"message\",{}).get(\"model\")
        if x and not x.startswith(\"<\"): m=x  # skip <synthetic> API-error placeholder entries
print(m)" "$JSONL" 2>/dev/null)
  fi
  MODELFLAG=""
  [ -n "$MODEL" ] && [ "$MODEL" != "inherit" ] && MODELFLAG="--model $MODEL"
  EFFORTFLAG=""
  [ -n "$EFFORT" ] && EFFORTFLAG="--effort $EFFORT"

  if [ "$MODE" = "surgery" ]; then
    echo "$(ts) [$SID] respawning same-session (model=${MODEL:-harness-default} perm=$PERM effort=$EFFORT prompt=$PF)" >>"$LOG"
    # CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0: wait indefinitely for background
    # tasks (workflows) after turn end. Without it, -p kills them after 600s —
    # observed 2026-07-19 orphaning an overnight run with in-flight background
    # workflows. A hop process with
    # tasks in flight thus lingers until they notify, runs the continuation turn,
    # and exits once a turn ends with nothing pending. Corollary kept elsewhere:
    # never hand off (respawn a successor) while workflows are still in flight,
    # or old and new hop could run turns on the same session concurrently.
    env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_ENTRYPOINT \
      CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 \
      claude -p --output-format json $EFFORTFLAG $MODELFLAG --permission-mode "$PERM" --resume "$SID" \
      <"$PF" >>"$LOG" 2>&1
    rc=$?
    # NB: claude exits 0 even when the hop was functionally blocked — task success
    # is judged by the successor (and the JSON result line above), not this code.
    echo "$(ts) [$SID] hop process finished (exit $rc)" >>"$LOG"
    exit 0
  fi

  # ---- fresh-bg mode ----
  cd "$VAULT" || { echo "$(ts) [$SID] cannot cd to vault — aborting" >>"$LOG"; exit 10; }
  echo "$(ts) [$SID] spawning fresh bg hop (model=${MODEL:-harness-default} perm=$PERM effort=$EFFORT prompt=$PF title=$TITLE)" >>"$LOG"
  SPAWNOUT=$(env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_ENTRYPOINT \
    claude --bg $EFFORTFLAG $MODELFLAG --permission-mode "$PERM" "$(cat "$PF")" 2>&1)
  SHORTID=$(printf "%s\n" "$SPAWNOUT" | sed -n "s/^backgrounded[^0-9a-f]*\([0-9a-f]\{8\}\).*/\1/p" | head -1)
  if [ -z "$SHORTID" ]; then
    echo "$(ts) [$SID] bg spawn failed — output: $SPAWNOUT" >>"$LOG"
    exit 11
  fi
  # Resolve full session id (short id = first 8 chars of the session uuid).
  NEWSID=""
  for i in $(seq 1 12); do
    NEWSID=$(claude agents --json 2>/dev/null | python3 -c "
import json,sys
sid=\"\"
for e in json.load(sys.stdin):
    if e.get(\"kind\")==\"background\" and e.get(\"id\")==sys.argv[1]:
        sid=e.get(\"sessionId\",\"\")
print(sid)" "$SHORTID" 2>/dev/null)
    [ -n "$NEWSID" ] && break
    sleep 5
  done
  if [ -z "$NEWSID" ]; then
    echo "$(ts) [$SID] bg hop $SHORTID spawned but session id not resolvable — no meta.json, no watchdog" >>"$LOG"
    exit 12
  fi
  # Fabricate the Claudian meta.json (chat appears when the chat list is next opened).
  META=$(NEWSID="$NEWSID" MODEL="$MODEL" TITLE="$TITLE" CLAUDIAN_SESS="$CLAUDIAN_SESS" python3 <<"PYEOF"
import json, os, time, glob, random, string
d = os.environ["CLAUDIAN_SESS"]
os.makedirs(d, exist_ok=True)
now = int(time.time() * 1000)
cid = "conv-%d-%s" % (now, "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(9)))
model = os.environ.get("MODEL", "")
sel = ""
if model and model != "inherit":
    # Reuse an existing meta selectedModel that embeds this model string
    # (recovers decorations like the [1m] context suffix); newest first.
    for f in sorted(glob.glob(os.path.join(d, "conv-*.meta.json")), key=os.path.getmtime, reverse=True)[:40]:
        try:
            sm = json.load(open(f)).get("selectedModel", "")
        except Exception:
            continue
        if model in sm and sm.startswith("claude-code/"):  # only current-format values (old metas may hold bare aliases like "sonnet")
            sel = sm
            break
    if not sel:
        sel = "claude-code/" + model
else:
    fs = sorted(glob.glob(os.path.join(d, "conv-*.meta.json")), key=os.path.getmtime, reverse=True)
    for f in fs[:10]:
        try:
            sel = json.load(open(f)).get("selectedModel", "")
        except Exception:
            continue
        if sel:
            break
    if not sel:
        sel = "claude-code/claude-fable-5[1m]"
meta = {
    "id": cid,
    "providerId": "claude",
    "title": os.environ["TITLE"],
    "titleGenerationStatus": "success",
    "createdAt": now,
    "updatedAt": now,
    "lastResponseAt": now,
    "sessionId": os.environ["NEWSID"],
    "selectedModel": sel,
    "providerState": {"providerSessionId": os.environ["NEWSID"]},
}
p = os.path.join(d, cid + ".meta.json")
json.dump(meta, open(p, "w"), indent=2)
print(p)
PYEOF
)
  echo "$(ts) [$SID] bg hop live: sid=$NEWSID short=$SHORTID meta=${META:-FAILED}" >>"$LOG"
  # ---- idle-stop watchdog ----
  NEWJSONL=$(ls "$HOME"/.claude/projects/*/"$NEWSID".jsonl 2>/dev/null | head -1)
  deadline=$(( $(date +%s) + WD_MAX_H * 3600 ))
  strikes=0
  gone=0
  bstrikes=0
  blocked_logged=0
  stray_logged=0
  while [ "$(date +%s)" -lt "$deadline" ]; do
    sleep 60
    ROW=$(claude agents --json 2>/dev/null | python3 -c "
import json,sys
for e in json.load(sys.stdin):
    if e.get(\"sessionId\")==sys.argv[1]:
        print(e.get(\"status\",\"\"), e.get(\"state\",\"\"), e.get(\"cwd\",\"\")); break" "$NEWSID" 2>/dev/null)
    ENTRY=$(printf "%s" "$ROW" | cut -d" " -f1-2)
    HOPCWD=$(printf "%s" "$ROW" | cut -d" " -f3-)
    if [ -z "$ENTRY" ]; then
      gone=$((gone + 1))
      # two consecutive misses before concluding it is gone (tolerates a
      # transient daemon/agents-json hiccup)
      if [ "$gone" -ge 2 ]; then
        echo "$(ts) [$SID] watchdog: bg hop $SHORTID no longer registered (stopped externally?) — exiting" >>"$LOG"
        exit 0
      fi
      continue
    fi
    gone=0
    # LOUD warning if the hop escaped the vault: cwd changes to
    # .claude/worktrees/<name> the moment a bg hop isolates into a worktree
    # (its Edit/Write output then never reaches the vault; recover it from the
    # worktree BEFORE claude rm, which deletes the worktree).
    if [ "$stray_logged" -eq 0 ] && [ -n "$HOPCWD" ] && [ "$HOPCWD" != "$VAULT" ]; then
      echo "$(ts) [$SID] watchdog: WARNING — bg hop $SHORTID cwd is $HOPCWD, NOT the vault root: the hop got isolated into a git worktree, its Edit/Write edits are NOT landing in the vault. Recover them from that path before claude rm. Ensure .claude/settings.json keeps \"worktree\": {\"bgIsolation\": \"none\"}." >>"$LOG"
      stray_logged=1
    fi
    # re-resolve when unset OR stale — the transcript relocates to another
    # project slug if the hop enters a worktree (forced isolation when the
    # bgIsolation=none settings opt-out is missing)
    { [ -z "$NEWJSONL" ] || [ ! -f "$NEWJSONL" ]; } && NEWJSONL=$(ls "$HOME"/.claude/projects/*/"$NEWSID".jsonl 2>/dev/null | head -1)
    mt=$(stat -c %Y "$NEWJSONL" 2>/dev/null || echo 0)
    age=$(( $(date +%s) - mt ))
    if [ "$ENTRY" = "idle done" ] && [ "$mt" != 0 ] && [ "$age" -ge "$IDLE_GRACE" ]; then
      strikes=$((strikes + 1))
    else
      strikes=0
    fi
    # A hop stuck on a permission prompt (e.g. haiku falls back to manual mode
    # — auto unavailable for that model) shows status=waiting/state=blocked.
    # Flag it once immediately; stop it if still blocked after ~1h so it does
    # not block Claudian resume for the whole watchdog lifetime.
    if [ "$ENTRY" = "waiting blocked" ]; then
      if [ "$blocked_logged" -eq 0 ]; then
        echo "$(ts) [$SID] watchdog: bg hop $SHORTID is BLOCKED on an approval prompt — claude attach $SHORTID to unblock; auto-stop if still blocked after ~1h" >>"$LOG"
        blocked_logged=1
      fi
      if [ "$mt" != 0 ] && [ "$age" -ge 3600 ]; then bstrikes=$((bstrikes + 1)); else bstrikes=0; fi
      if [ "$bstrikes" -ge 2 ]; then
        claude stop "$SHORTID" >>"$LOG" 2>&1
        echo "$(ts) [$SID] watchdog: stopped BLOCKED bg hop $SHORTID (never approved) — hop did not complete" >>"$LOG"
        exit 0
      fi
    else
      bstrikes=0
    fi
    if [ "$strikes" -ge 2 ]; then
      claude stop "$SHORTID" >>"$LOG" 2>&1
      echo "$(ts) [$SID] watchdog: stopped idle bg hop $SHORTID (transcript quiet ${age}s) — resumable in Claudian" >>"$LOG"
      if [ -n "$META" ] && [ -f "$META" ]; then
        MT_MS=$((mt * 1000)) META="$META" python3 -c "
import json, os
p = os.environ[\"META\"]
m = json.load(open(p))
m[\"updatedAt\"] = int(os.environ[\"MT_MS\"])
m[\"lastResponseAt\"] = int(os.environ[\"MT_MS\"])
json.dump(m, open(p, \"w\"), indent=2)" 2>/dev/null
      fi
      exit 0
    fi
  done
  echo "$(ts) [$SID] watchdog: lifetime cap (${WD_MAX_H}h) hit with bg hop $SHORTID still alive — leaving it running" >>"$LOG"
' >/dev/null 2>&1 &

echo "respawn scheduled for $SID (mode=$MODE hops_remaining=$HOPS; surgery=${SUMMARY:-none}; log: $LOG)"
