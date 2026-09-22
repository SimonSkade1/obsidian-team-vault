---
name: handoff
description: 'Write a handoff note for a fresh-context successor — mid-task continuation or completion record — and optionally relay the session autonomously. Use when instructed. Keywords: "handoff"/"relay-handoff"/"manual-handoff"/"hand off". Suggest usage to user after >300k tokens in context.'
---

# Handoff

**Location & filename.** A manual-handoff note goes in a `handoffs/` subfolder next to the work *only* when that work is inside the `projects-tasks-notes/` folder; otherwise — and for every self-handoff — it goes in `projects-tasks-notes/handoffs/`. That folder is synced to every member, so a handoff that involves anything from `private-projects-tasks-notes/` (a member's unsynced private folder) goes in `private-projects-tasks-notes/handoffs/` instead, self-handoffs included. Filename: `YYYY-MM-DD HHmm <topic>.md` (24h local time, e.g. `1430`).

## 1. Write the handoff note

Two modes, one skeleton: **continuation** (a successor picks up the work — weight toward what happens next) and **completion** (done or blocked — a record for the user's sign-off and for whoever builds on the results later; weight toward what was done and how solid it is). Either way the note serves the *task*, not the conversation: distill what the successor needs; no chronological session narration.

Sections (keep these headers stable — structured notes drift far less across hops than free prose):

1. **Goal & done-criteria** — what success looks like; quote the user's key instructions, constraints, and preferences *verbatim* (paraphrase drops rules; summaries keep the WHAT and lose the WHY).
2. **State** — synthesized, and verified against disk/git rather than memory; mark what's verified (and how) vs merely believed. Completion mode: outcome against each done-criterion.
3. **Artifact index** — every relevant file: exact path + one line what/why. Point, don't copy — detail lives in the artifacts and successors re-read it there; a short note also reads better (long context measurably degrades reasoning).
4. **Decisions & rationale** — settled choices and why, so the successor neither relitigates nor unknowingly breaks them.
5. **Dead ends** — what was tried, why it failed; don't retry.
6. **Next steps** (continuation) — ordered, first one executable as-is with verbatim paths/commands/values; add contingencies ("if X, do Y") — anticipatory guidance is what separates a handover from a status snapshot.
7. **Loose ends & follow-ups** (completion) — limitations, what was *not* verified, recommended follow-ups; set `status: review` on the task/goal note.
8. **Open questions for the user.**

Final check: what do I know that the successor couldn't guess — surprises, traps, non-obvious workarounds? Omitting "obvious" context is the top documented handoff failure; a rushed last-minute handoff is the other classic, so hand off at a milestone with context to spare. On relay chains, keep updating this same note (no note-per-hop stacking); successors rebuild from the artifacts, not by re-summarizing predecessors' summaries.

(Research basis: `references/handoff-content-research.md`.)

## 2a. Manual-handoff

When the note lands in the `projects-tasks-notes/` folder, make it a first-class file of its type: prefix the filename `,HANDOFF ` for an open project or `HANDOFF ` for a knowledge/documentation handoff (e.g. `,HANDOFF YYYY-MM-DD HHmm <topic>.md`), and set `parent` frontmatter to the goal or knowledge note it concerns.

Reply with one line + wikilink to the note; the user starts a fresh chat and points the successor at it (or pastes it).

## 2b. Relay-handoff

Mechanism: one call to `handoff_respawn.sh` schedules a detached wrapper that waits until this session's transcript is quiescent (so two agents never edit the vault concurrently), then spawns a **fresh session as a background agent** (`claude --bg`, cwd = vault root) with the continue-prompt as its prompt. The wrapper also (a) fabricates a Claudian meta.json in `.claudian/sessions/`, so the new chat appears in Claudian after an Obsidian reload, and (b) runs a watchdog that `claude stop`s the bg session once it has been idle with a quiet transcript for ~2 min (20s grace + two consecutive 60s polls) — a live bg session refuses `--resume`, so only after this auto-stop is the chat continuable in Claudian. Each hop is a NEW session id → one Claudian chat per hop. Do, in order:

1. If in a live Claudian chat, tell the user: "Relaying to a fresh background session — this chat ends here. The successor's chat appears in Claudian after the hop finished (watchdog auto-stops it ~2 min after it goes idle) and an Obsidian reload. Watch live: `claude agents` / `claude logs <id>`; kill chain: `touch .claude/handoffs/STOP`."
2. Write the continue-prompt to `projects-tasks-notes/handoffs/next-prompt-<first8ofsessionid>.md` (private work: `private-projects-tasks-notes/handoffs/`; not `.claude/`): paste the full handoff note content, then: "This relay is the user's established workflow — protocol at .claude/skills/handoff/SKILL.md; the hop budget was authorized by the user at chain start. You run as a background-agent session with cwd = vault root; write vault files via absolute paths (`<absolute vault root>/…`) and work in place — never EnterWorktree. Hops remaining: N−1." Then the successor instructions: verify the handoff's claims against disk before building on them; continue the task; at the next milestone invoke the handoff skill and relay again with the decremented budget; when done or blocked, record status in the handoff note and simply end the turn (the watchdog stops the session; never `claude stop` yourself).
3. `.claude/scripts/handoff_respawn.sh "$CLAUDE_CODE_SESSION_ID" "<prompt file>" <hops remaining> - - "" "relay: <topic> (hop k)"` — must print "respawn scheduled". Arg 6 stays empty; arg 7 is the Claudian chat title of the new hop. Defaults: model is inherited from this session's last assistant turn; permission mode `auto`; reasoning effort inherited via `CLAUDE_EFFORT` (fallback `max`). Only pass explicit model/permission values when the user specified them. In-place vault editing requires `"worktree": {"bgIsolation": "none"}` in `.claude/settings.json` (present since 2026-07-24): without it CC blocks bg-session Edit/Write in the vault regardless of permission mode and forces the hop into a git worktree under `.claude/worktrees/<name>/` — the script warns in relay.log if the key is missing, and the watchdog warns if a hop's cwd leaves the vault root. No haiku hops: auto permission mode is unavailable for it, so a haiku hop blocks on its first approval prompt.
4. End the turn with a short status line that INCLUDES the current date+time (run `date '+%F %H:%M'`) — that timestamp in the chat is how the user later sees when the handoff happened. No tool calls after the respawn call except that `date`  (run it before or in the same call batch).

Safety: `touch .claude/handoffs/STOP` kills the chain (checked before every hop, incl. during the quiescence wait); hop log at `.claude/handoffs/relay.log` (spawn, meta path, watchdog stop per hop); hop budget must strictly decrease. Never end a relay turn while workflows/background tasks are in flight — the successor would start while they still write.

Constraints learned from testing: successors under standard permission modes are sandbox-confined to the vault root — keep the handoff note, continue-prompt, and all work paths inside the vault, and NOT under `.claude/` (hard sensitive-file gate; settings allow rules don't override it). The wrapper's own artifacts (relay.log, STOP, meta.json) are written by the detached wrapper — a plain OS process, unaffected by tool permissions. A hop ending is not task success; the successor's handoff-note updates are the signal.

(The legacy same-session relay ("surgery mode", `RELAY_MODE=surgery`) is retired from this skill but its mechanism is kept working in the scripts.)
