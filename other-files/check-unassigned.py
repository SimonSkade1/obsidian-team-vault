#!/usr/bin/env python3
"""check-unassigned.py — nightly check of the shared vault for unassigned items.

Run by other-files/run-daily-review.sh on the automation host (pure python, no
Claude). An item is unassigned when its `owner` and `next_action_by` are both
empty and its status is not terminal — exactly the "Unassigned" view of
me.base: every .md under projects-tasks-notes/ except archived/, handoffs/ and
.sync-conflict- copies; a file without properties counts too.

It nags once per item: an item already linked from any "!check unassigned
items …" file (any status, archived ones too) is covered. When new, uncovered
items exist it appends them to the open check task if there is one, else files
a new dated task for simon (status inbox, priority 6) in quick-tasks-and-notes/.
So there is at most one open check task, and nothing is filed twice.

Usage: check-unassigned.py [VAULT_ROOT] [--dry-run]
  VAULT_ROOT defaults to the parent of this script's folder. --dry-run writes nothing.
Prints one summary line (it lands in the nightly log). Exit 0 unless it crashes.
"""
import datetime
import re
import sys
from pathlib import Path

TERMINAL = {"done", "cancelled", "failed"}
CHECK_PREFIX = "!check unassigned items"
OWNER = "simon"
PRIORITY = 6
SUBFOLDER = "quick-tasks-and-notes"

_QUOTED = re.compile(r'^(["\'])(.*)\1$')
_WIKILINK = re.compile(r"\[\[([^\]]+?)\]\]")
_LIST_ITEM = re.compile(r"^(\d+)\. ")


def frontmatter(text):
    """Minimal YAML front matter: top-level `key: scalar` pairs -> {key: str}.
    Empty / null / block values become "". Enough for status, owner, next_action_by."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() in ("---", "..."):
            break
        if not line or line[0] in " \t-#":
            continue  # list items / nested / comments belong to the previous key
        key, sep, value = line.partition(":")
        if not sep or " " in key.strip():
            continue
        value = value.strip()
        if value in ("", "~", "null", "Null", "NULL", "[]", "{}"):
            value = ""
        m = _QUOTED.match(value)
        if m:
            value = m.group(2)
        fm[key.strip()] = value.strip()
    return fm


def wikilinks(text):
    """Basenames linked from the text: [[name]], [[name|alias]], [[name#h]], [[folder/name]]."""
    out = set()
    for m in _WIKILINK.finditer(text):
        target = re.split(r"[|#]", m.group(1), 1)[0].strip()
        out.add(target.rsplit("/", 1)[-1])
    return out


def kind(basename):
    return "project" if basename.startswith(",") else "task" if basename.startswith("!") else "note"


def item_line(base, fm):
    st = fm.get("status", "")
    return f"[[{base}]] — {kind(base)}" + (f", {st}" if st else "")


def scan(root):
    """All .md files under projects-tasks-notes/ as (relpath, basename, fm, text), path order."""
    out = []
    for p in sorted((root / "projects-tasks-notes").rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out.append((p.relative_to(root).as_posix(), p.stem, frontmatter(text), text))
    return out


def appended(text, items, today):
    """The open task's text with the new items continuing its numbered list (or a new list at the end)."""
    lines = text.split("\n")
    last = max((i for i, l in enumerate(lines) if _LIST_ITEM.match(l)), default=None)
    if last is None:
        start, at = 1, None
    else:
        start, at = int(_LIST_ITEM.match(lines[last]).group(1)) + 1, last + 1
    new = [f"{start + i}. {item_line(b, fm)} (added {today})" for i, (_, b, fm, _) in enumerate(items)]
    if at is None:
        while lines and lines[-1] == "":
            lines.pop()
        lines += ["", *new, ""]
    else:
        lines[at:at] = new
    return "\n".join(lines)


def main(argv):
    dry = "--dry-run" in argv
    args = [a for a in argv if a != "--dry-run"]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parent.parent
    if not (root / "projects-tasks-notes").is_dir():
        print(f"check-unassigned: no projects-tasks-notes/ under {root}", file=sys.stderr)
        return 2

    files = scan(root)
    checks = [f for f in files if f[1].startswith(CHECK_PREFIX)]          # any status, archived too
    covered = set().union(*(wikilinks(f[3]) for f in checks)) if checks else set()
    open_checks = [f for f in checks if f[2].get("status", "").lower() not in TERMINAL]

    in_scope = [f for f in files if "/archived/" not in "/" + f[0] and "/handoffs/" not in "/" + f[0]
                and ".sync-conflict-" not in f[1] and not f[1].startswith(CHECK_PREFIX)]
    unassigned = [f for f in in_scope
                  if f[2].get("owner", "") == "" and f[2].get("next_action_by", "") == ""
                  and f[2].get("status", "").lower() not in TERMINAL]
    new = [f for f in unassigned if f[1] not in covered]
    n, m = len(unassigned), len(new)
    today = datetime.date.today().isoformat()

    if m == 0:
        print(f"check-unassigned: {n} unassigned item(s), none new — nothing to do")
        return 0

    if open_checks:                                       # (a) never a second open task: extend it
        rel, base, _, text = max(open_checks, key=lambda f: f[1])
        target = root / rel
        content = appended(text, new, today)
        action = f"appended {m} new item(s) to {rel}"
    else:
        taken = {f[1] for f in files}
        name = f"{CHECK_PREFIX} {today}"
        k = 2
        while name in taken:                              # basenames must be unique vault-wide
            name = f"{CHECK_PREFIX} {today} ({k})"
            k += 1
        target = root / "projects-tasks-notes" / SUBFOLDER / f"{name}.md"
        head = ["---", "status: inbox", f"priority: {PRIORITY}", "parent:", f"owner: {OWNER}",
                "next_action_by:", "not_before:", "subscribers:", "---",
                "Give each item an `owner` or a `next_action_by` (or a terminal status); "
                "the **Unassigned** view of `me.base` lists all of them live. "
                f"New on {today} ({m} item{'s' if m != 1 else ''}):", ""]
        content = "\n".join(head + [f"{i}. {item_line(b, fm)}" for i, (_, b, fm, _) in enumerate(new, 1)]) + "\n"
        action = f"created {target.relative_to(root).as_posix()} with {m} item(s)"

    if dry:
        print(f"check-unassigned: {n} unassigned item(s), {m} new; (dry run) would have {action}")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"check-unassigned: {n} unassigned item(s), {m} new; {action}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    sys.exit(main(sys.argv[1:]))
