#!/usr/bin/env python3
"""Keep the vault's file names valid on Windows.

Syncthing on a Windows machine cannot create a file or folder whose name Windows
forbids, so such a file never arrives there; it stays in that member's Syncthing
under "Failed Items" (2026-10-09: three notes with > " ? in their names).
Obsidian on Linux and macOS accepts these names, so they keep appearing. This
script finds them. With --fix, it renames them and has a headless Claude session
patch the links.

  python3 other-files/check-filenames.py                  list the problems, change nothing (exit 1 if any)
  python3 other-files/check-filenames.py --fix            fix them (team-vault-filename-check.timer, every 10 min)
  python3 other-files/check-filenames.py --fix --dry-run  show the renames --fix would make, change nothing

The script checks every file and folder Syncthing shares: the patterns of .stignore
(which includes .stignore-shared; a simple subset of the syntax is supported).
.git, .stversions, .obsidian, .trash and Syncthing's own files are always
skipped. It flags:
  1. the characters < > : " \\ | ? * and control characters;
  2. a name ending in a space or a period;
  3. a Windows device name: CON PRN AUX NUL COM0-9 LPT0-9, also with an
     extension (nul.md);
  4. two names in one folder that differ only in case (Windows and macOS hold
     one of them).
Anything modified in the last 30 minutes waits, because someone may be editing
it; for a folder, a change to anything inside it counts. Modification times are
synced, so this covers every member's edits (the vault cleanup uses the same
rule). A `,` project note waits as long as its folder does.

--fix renames them in this script, by fixed rules (windows_name):
  -> becomes →, <- becomes ←, => becomes ⇒, " becomes ', ": " becomes " - ",
  any other : | \\ becomes -, any other < > becomes ‹ ›; ? * and control
  characters are dropped; trailing spaces and periods are stripped; a device
  name gets a _ (nul_.md).
Of two names that differ only in case, the newer one gets " 2". So does any new
name that is taken (by a sibling, or for a file by a basename anywhere in the
vault). Folders go before their contents.
Then, if any shared text file mentions an old name, one `claude -p` session
(model and tools: other-files/filename-fix-settings.json: read, grep and edit,
no shell) patches the links. Its output goes to the journal and to
other-files/logs/filename-fix-<time>.log.
Claude does not do the renames itself because Claude Code's dontAsk mode refuses
`mv` on a path with ? or *, and `mv -n` (tested 2026-10-09, Claude Code 2.1.286).
Afterwards the script checks the names again, and checks for wikilinks that still
point to an old name. It DMs the vault owner (if other-files/discord/ exists) once about anything still wrong (state:
other-files/logs/filename-check-state.json; logs/ is neither synced nor committed).
The round is skipped while run-vault-cleanup.sh holds its lock, because both
move files. The script is silent when there is nothing to do.

Test hooks (environment): FC_VAULT=<dir> another vault root (a throwaway copy),
FC_MIN_AGE_MIN=<minutes> instead of 30, FC_CLAUDE_BIN=<path> instead of claude
from PATH, FC_NO_DM=1 sends no Discord DM.
"""
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent  # other-files/ of the vault the script sits in
VAULT = Path(os.environ.get("FC_VAULT") or HERE.parent).resolve()
LOGS = VAULT / "other-files" / "logs"
STATE = LOGS / "filename-check-state.json"
MIN_AGE = float(os.environ.get("FC_MIN_AGE_MIN", "30")) * 60
CLEANUP_LOCK = "/tmp/vault-cleanup-team-vault.lock"  # held by run-vault-cleanup.sh while it runs

RESERVED = set('<>:"\\|?*') | {chr(i) for i in range(32)}
DEVICE = re.compile(r"(CON|PRN|AUX|NUL|COM\d|LPT\d)(\..*)?", re.I)
NEVER_SHARED = re.compile(r"\.git|\.stfolder|\.stversions|\.stignore|\.obsidian|\.trash"
                          r"|\.syncthing\..*\.tmp|~syncthing~.*\.tmp")
TEXT = {".md", ".base", ".canvas", ".json", ".py", ".sh", ".txt", ".yml", ".yaml", ".js", ".mjs", ".html", ".css"}

PROMPT = """You run unattended on this Obsidian vault's automation host; the working directory is the vault root. These files and folders were just renamed because Windows cannot hold their old names (old path → new path):

{renames}

Patch every link to an old name or path so that it points to the new one. These files mention an old name (some only in prose):

{files}

Links come in these forms: wikilinks and embeds (`[[old]]`, `[[old|alias]]`, `[[old#heading]]`, `[[folder/old.md]]`, `![[old]]`), also inside frontmatter (`parent`, `dependencies`; keep the YAML quoting valid), markdown links with a URL-encoded path (`%20`, `%22`, `%3F`, …), and paths in scripts, skills and settings. A renamed folder changes every path through it. Leave prose that only mentions an old name as it is, and edit nothing else. Your tools are Read, Grep, Glob and Edit. End with one line per rename: `old -> new: N links patched in M files`."""


def glob_re(p):
    """the regex of a Syncthing glob: ** any path, * and ? within one name segment"""
    out, i = [], 0
    while i < len(p):
        if p.startswith("**", i):
            out.append(".*")
            i += 2
            continue
        out.append({"*": "[^/]*", "?": "[^/]"}.get(p[i]) or re.escape(p[i]))
        i += 1
    return "".join(out)


def stignore(root):
    """Syncthing's ignore patterns of root as [(regex, ignored?)]; the first match decides"""
    pats, seen = [], set()

    def load(f):
        if f in seen or not f.is_file():
            return
        seen.add(f)
        for line in f.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("#include "):
                load(f.parent / line[len("#include "):].strip())
                continue
            if not line or line.startswith("//"):
                continue
            ignore, flags = True, 0
            while True:
                if line.startswith("!"):
                    ignore, line = False, line[1:]
                elif line.startswith("(?i)"):
                    flags, line = re.I, line[4:]
                elif line.startswith("(?d)"):
                    line = line[4:]
                else:
                    break
            # /x = x at the root; x = x at any depth; a folder's match covers its contents
            body = glob_re(line[1:]) if line.startswith("/") else "(?:.*/)?" + glob_re(line)
            pats.append((re.compile(body + "(?:/.*)?", flags), ignore))

    load(root / ".stignore")
    if not seen:  # a copy or a machine without its own .stignore
        load(root / ".stignore-shared")
    return pats


def shared(root):
    """(folder, its vault-relative prefix, its shared names) for every folder Syncthing shares"""
    pats = stignore(root)
    for d, dirs, files in os.walk(root):
        rel = Path(d).relative_to(root).as_posix()
        pre = "" if rel == "." else rel + "/"
        names = sorted(n for n in dirs + files if not NEVER_SHARED.fullmatch(n)
                       and not next((ign for rx, ign in pats if rx.fullmatch(pre + n)), False))
        keep = set(names)
        dirs[:] = sorted(n for n in dirs if n in keep)  # do not descend into what is not shared
        yield d, pre, names


def shared_files():
    return [pre + n for d, pre, names in shared(VAULT) for n in names if os.path.isfile(os.path.join(d, n))]


def newest(p):
    """latest modification time of p and, for a folder, of anything inside it"""
    t = os.lstat(p).st_mtime
    if os.path.isdir(p) and not os.path.islink(p):
        for d, dirs, files in os.walk(p):
            for n in dirs + files:
                try:
                    t = max(t, os.lstat(os.path.join(d, n)).st_mtime)
                except OSError:
                    pass
    return t


def problems(name, twins):
    why = []
    bad = sorted(set(name) & RESERVED)
    if bad:
        why.append("characters " + " ".join(c if c.isprintable() else f"\\x{ord(c):02x}" for c in bad))
    if name[-1] in " .":
        why.append("ends in a " + ("space" if name[-1] == " " else "period"))
    if DEVICE.fullmatch(name):
        why.append("Windows device name")
    if twins:
        why.append("differs only in case from " + ", ".join(twins))
    return "; ".join(why)


def scan():
    """[(path, problem, recent?)] for every shared name Windows cannot hold"""
    now, found = time.time(), []
    for d, pre, names in shared(VAULT):
        by_case = {}
        for n in names:
            by_case.setdefault(n.lower(), []).append(n)
        for n in names:
            why = problems(n, [m for m in by_case[n.lower()] if m != n])
            if why:
                found.append((pre + n, why, now - newest(os.path.join(d, n)) < MIN_AGE))
    return found


def windows_name(name):
    """name with the renaming rules of the header applied"""
    orig = name
    for a, b in (("->", "→"), ("<-", "←"), ("=>", "⇒"), ('"', "'"), ("<", "‹"), (">", "›")):
        name = name.replace(a, b)
    name = re.sub(r"\s*[:|\\]\s+|\s+[:|\\]\s*", " - ", name)  # "a: b" -> "a - b"
    name = re.sub(r"[:|\\]", "-", name)  # "12:30" -> "12-30"
    name = "".join(c for c in name if c not in "?*" and ord(c) >= 32)
    name = re.sub(r" {2,}", " ", name).rstrip(" .")
    name = re.sub(r"^(CON|PRN|AUX|NUL|COM\d|LPT\d)(?=\.|$)", r"\1_", name, flags=re.I)
    return name if name and (orig[0] == "." or name[0] != ".") else "unnamed" + name  # "???.md" -> "unnamed.md"


def rename_all(todo, dry):
    """rename the paths of todo, folders first; returns [(old path, new path)] and [(old path, error)]"""
    basenames = Counter(Path(p).name.lower() for p in shared_files())
    moved, done, failed = {}, [], []
    order = sorted(todo, key=lambda p: (p.count("/"), -os.lstat(VAULT / p).st_mtime))  # newer case twin first
    for p in order:
        anc = max((o for o in moved if p.startswith(o + "/")), key=len, default=None)
        cur = moved[anc] + p[len(anc):] if anc else p
        folder, old = os.path.split(cur)
        is_file = not os.path.isdir(VAULT / cur)
        new = windows_name(old)
        stem, ext = os.path.splitext(new) if is_file else (new, "")
        siblings = {n.lower() for n in os.listdir(VAULT / folder) if n != old}
        i = 1
        while new.lower() in siblings or (is_file and new.lower() != old.lower() and basenames[new.lower()]):
            i += 1
            new = f"{stem} {i}{ext}"
        if new == old:  # e.g. the case twin that was renamed already
            continue
        dest = f"{folder}/{new}" if folder else new
        if not dry:
            try:
                os.rename(VAULT / cur, VAULT / dest)
            except OSError as e:
                failed.append((p, str(e)))
                continue
        basenames[old.lower()] -= 1
        basenames[new.lower()] += 1
        if not is_file and not dry:
            moved[p] = dest
        done.append((p, dest))
    return done, failed


def stem(path):
    name = Path(path).name
    return name[:-3] if name.endswith(".md") else name


def mentions(renames):
    """shared text files that contain an old name as typed, YAML-escaped or URL-encoded"""
    olds = set()
    for o, _ in renames:
        s = stem(o)
        olds |= {s, s.replace('"', '\\"'), s.replace(" ", "%20"), quote(s)}
    hits = []
    for p in shared_files():
        if Path(p).suffix.lower() in TEXT:
            try:
                text = (VAULT / p).read_text(errors="ignore")
            except OSError:
                continue
            if any(o in text for o in olds):
                hits.append(p)
    return hits


def stale_links(renames, files):
    """[(old path, file)] for every wikilink in files that still points to an old name (or through an old folder)"""
    pats = [(o, re.compile(r"\[\[(?:[^\]|#^\n]*/)?" + re.escape(s)
                           + ("/" if os.path.isdir(VAULT / n) else r"(?:\.md)?(?=[\]|#^])")))
            for o, n in renames for s in {stem(o), stem(o).replace('"', '\\"')}]
    out = []
    for f in files:
        try:
            text = (VAULT / f).read_text(errors="ignore")
        except OSError:
            continue  # renamed meanwhile
        out += [(o, f) for o, rx in pats if rx.search(text) and (o, f) not in out]
    return out


def cleanup_running():
    try:
        with open(CLEANUP_LOCK) as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
    except FileNotFoundError:
        return False
    except BlockingIOError:
        return True
    return False


def run_claude(prompt, log):
    """one headless session in the vault; returns its final text (or why it did not run)"""
    env = dict(os.environ)  # systemd does not source ~/.profile: make the claude launcher findable
    env["PATH"] = f"{Path.home()}/.local/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    claude = os.environ.get("FC_CLAUDE_BIN") or shutil.which("claude", path=env["PATH"])
    out, err = "", "claude not found on PATH"
    if claude:
        try:
            r = subprocess.run([claude, "-p", prompt, "--settings", str(HERE / "filename-fix-settings.json"),
                                "--permission-mode", "dontAsk", "--strict-mcp-config", "--output-format", "json"],
                               cwd=VAULT, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               timeout=1800)
            out, err = r.stdout, r.stderr
        except (OSError, subprocess.TimeoutExpired) as e:
            err = f"claude did not finish: {e}"
    log.write_text(f"{prompt}\n\n=== claude output ===\n{out}\n=== stderr ===\n{err}")
    try:
        res = json.loads(out)
        return f"{res.get('result', '').strip()}\n(session {res.get('session_id')}, ${res.get('total_cost_usd', 0):.2f})"
    except ValueError:
        return (out + err).strip()[-3000:]


def dm(problems, state):
    """DM the vault owner once per problem (needs other-files/discord/); problems = {key: line}"""
    new = {k: v for k, v in problems.items() if k not in state}
    if not new or os.environ.get("FC_NO_DM") or not (HERE / "discord" / "discord.py").is_file():
        return
    text = ("File-name check on the automation host: still wrong after its fix attempt "
            "(names that Windows members cannot sync, or links to an old name):\n"
            + "\n".join(f"- {v}" for v in new.values())
            + "\nDetails: journalctl --user -u team-vault-filename-check -o cat, other-files/logs/filename-fix-*.log.")
    try:
        ok = subprocess.run([sys.executable, str(HERE / "discord" / "discord.py"), "post", "@<vault-owner>", text],
                            stdin=subprocess.DEVNULL, timeout=120).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    if ok:
        state.update({k: time.time() for k in new})
    else:
        print("The DM to the vault owner failed; the next round tries again.")


def fix(dry):
    LOGS.mkdir(parents=True, exist_ok=True)
    lock = open(LOGS / "filename-check.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0  # the previous round is still running
    if cleanup_running():
        print("The vault cleanup is running; the next round checks again.")
        return 0
    found = scan()
    waiting = {p for p, _, recent in found if recent}
    todo = [p for p, _, recent in found if not recent
            # a `,` project note goes with its folder (named like it without the `,`)
            and not (Path(p).name == f",{Path(p).parent.name}.md" and Path(p).parent.as_posix() in waiting)]
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    if not todo:
        if state and not found:  # all fixed: forget what was reported
            STATE.write_text("{}\n")
        return 0

    renames, failed = rename_all(todo, dry)
    if dry:
        print("\n".join(f"{o} -> {n}" for o, n in renames))
        return 0
    files = mentions(renames) if renames else []
    if renames:
        print(f"Renamed {len(renames)} path(s) Windows cannot hold:")
        print("\n".join(f"  {o} -> {n}" for o, n in renames))
    if files:
        log = LOGS / f"filename-fix-{time.strftime('%Y%m%dT%H%M%S')}.log"
        prompt = PROMPT.format(renames="\n".join(f"- `{o}` → `{n}`" for o, n in renames),
                               files="\n".join(f"- `{f}`" for f in files))
        print(f"{len(files)} file(s) mention an old name; Claude patches the links (log: {log}):")
        print(run_claude(prompt, log))
    elif renames:
        print("No file mentions an old name: no links to patch.")

    problems = {p: f"{p}: rename failed ({e})" for p, e in failed}
    problems.update({p: f"{p}: {why}" for p, why, recent in scan() if not recent and p not in problems})
    problems.update({f"{o} in {f}": f"{f} still links to the old name {Path(o).name}"
                     for o, f in stale_links(renames, files)})
    if problems:
        print("Still wrong:\n" + "\n".join(f"  {v}" for v in problems.values()))
    dm(problems, state)
    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    return 1 if problems else 0


def main():
    sys.stdout.reconfigure(line_buffering=True)  # keep the journal in order with the subprocesses' output
    args = sys.argv[1:]
    if args and args[0] == "--fix" and set(args[1:]) <= {"--dry-run"}:
        sys.exit(fix("--dry-run" in args))
    if args:
        sys.exit(__doc__)
    found = scan()
    for p, why, recent in found:
        print(f"{p}: {why}" + ("  (changed in the last 30 min: waits)" if recent else ""))
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
