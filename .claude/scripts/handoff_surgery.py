#!/usr/bin/env python3
"""Synthetic compaction ("surgery") for Claude Code session transcripts.

Appends a compact_boundary + isCompactSummary pair to a session .jsonl so the
next resume/reopen rebuilds context as: [our hand-written summary] + [preserved
last message] + [anything appended later]. All earlier history stays on disk
but is no longer loaded. This replicates what native /compact writes, with a
hand-authored "summary" (typically a handoff note) and no LLM call.

Usage:
  handoff_surgery.py SESSION_ID_OR_JSONL_PATH SUMMARY_FILE [--force] [--no-footer]

Behavior:
  1. Refuses if the jsonl changed <10s ago (likely mid-turn) unless --force.
  2. Wraps the summary in the same framing native compaction uses, and (unless
     --no-footer) appends the pointer to the full transcript path.
  3. Verifies the appended tail and prints OK/ERROR.

Entry-format template captured from Claude Code v2.1.197 output on 2026-07-08.
"""
import glob
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone


def find_jsonl(arg: str) -> str:
    if os.path.isfile(arg):
        return arg
    hits = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{arg}.jsonl"))
    if len(hits) != 1:
        sys.exit(f"ERROR: found {len(hits)} transcripts for '{arg}': {hits}")
    return hits[0]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    footer = "--no-footer" not in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)

    path = find_jsonl(args[0])
    age = time.time() - os.path.getmtime(path)
    if age < 10 and not force:
        sys.exit(f"ERROR: {path} modified {age:.1f}s ago — session may be mid-turn. Retry or --force.")

    entries = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    msgs = [e for e in entries if e.get("type") in ("user", "assistant") and e.get("uuid")]
    if not msgs:
        sys.exit("ERROR: no user/assistant messages found in transcript")
    last = msgs[-1]
    proto = {k: last[k] for k in ("cwd", "sessionId", "version", "gitBranch", "slug") if k in last}

    body = open(args[1]).read().strip()
    summary_text = (
        "This session is being continued from a previous conversation. The text below is a "
        "hand-authored handoff that replaces the earlier history.\n\n" + body
    )
    if footer:
        summary_text += (
            "\n\nIf you need specific details from before this handoff, read the full transcript at: "
            + os.path.abspath(path)
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    b_uuid, s_uuid, p_uuid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    pre_tokens = sum(len(json.dumps(e)) for e in entries) // 4  # rough estimate; cosmetic

    boundary = {
        "parentUuid": None,
        "logicalParentUuid": last["uuid"],
        "isSidechain": False,
        "type": "system",
        "subtype": "compact_boundary",
        # Custom label (native compaction writes "Conversation compacted"):
        # display-only for the CLI; patched Claudian (fix-handoff-reload)
        # renders it as the boundary-bar text.
        "content": "handoffed",
        "isMeta": False,
        "timestamp": now,
        "uuid": b_uuid,
        "level": "info",
        "compactMetadata": {
            "trigger": "manual",
            "preTokens": pre_tokens,
            "durationMs": 0,
            "preservedSegment": {"headUuid": last["uuid"], "anchorUuid": s_uuid, "tailUuid": last["uuid"]},
            "preservedMessages": {"anchorUuid": s_uuid, "uuids": [last["uuid"]], "allUuids": [last["uuid"]]},
            "postTokens": len(summary_text) // 4,
            "cumulativeDroppedTokens": pre_tokens,
        },
        "userType": "external",
        "entrypoint": "sdk-cli",
        **proto,
    }
    summary = {
        "parentUuid": b_uuid,
        "isSidechain": False,
        "promptId": p_uuid,
        "type": "user",
        "message": {"role": "user", "content": summary_text},
        "isVisibleInTranscriptOnly": True,
        "isCompactSummary": True,
        "uuid": s_uuid,
        "timestamp": now,
        "userType": "external",
        "entrypoint": "sdk-cli",
        **proto,
    }

    with open(path, "a") as f:
        f.write(json.dumps(boundary) + "\n")
        f.write(json.dumps(summary) + "\n")

    tail = open(path).readlines()[-2:]
    ok = "compact_boundary" in tail[0] and "isCompactSummary" in tail[1]
    print(
        f"{'OK' if ok else 'ERROR'}: appended synthetic compaction to {path} "
        f"(summary {len(summary_text)} chars; ~{pre_tokens} tokens of history excluded from future loads)"
    )
    sys.exit(0 if ok else 1)


main()
