#!/usr/bin/env python3
"""Configure this shared vault on one member's machine — everything that can be
done from disk. Driven by the `setup-member` skill; safe to run by hand.

    python3 .claude/skills/setup-member/setup_member.py --name <firstname>
    python3 .claude/skills/setup-member/setup_member.py --dry-run
    python3 .claude/skills/setup-member/setup_member.py --update-templates
    (Windows: `py -3` instead of `python3`)

Every action first checks whether it is already true, so re-running changes
nothing (`already`). The vault it acts on is derived from this file's own
location, never from the working directory, and nothing outside that folder is
written — the one exception is the Syncthing ignore pattern, which is this
folder's own ignore list and is set through the local Syncthing API (read from
the local config.xml) or, if that is unreachable, by writing `.stignore` here.

The note templates are JavaScript that Templater runs when the member calls their commands
(Alt+P, "Insert properties"), so the folder Templater runs is this machine's
`local_templates/` (never synced), filled from the shared `shared_templates/` only after a
scan for code a template has no business containing; a shared template that changed after
the copy is printed as a diff and copied only with `--update-templates`. Templater's
creation trigger (device-local, Obsidian's localStorage) is switched OFF through the
`obsidian` CLI when there is one — see act_creation_trigger for why; a new note's `owner`
and `parent` come from the bases' New button instead. Where a Linux package has put the
desktop app in front of that CLI on Claudian's PATH, a PATH line in Claudian's settings
puts the CLI first again.

Normally run from Claudian, i.e. with Obsidian open (INSTALL_AND_SETUP step 7): Obsidian reads
community-plugins.json only at startup (app.json and hotkeys.json it picks up live), so
the member restarts it afterwards. Obsidian's Restricted mode lives in its own
localStorage (key `enable-plugin-<appId>`), outside the vault — the member switched
it off when installing Claudian (INSTALL_AND_SETUP step 6); on the terminal route they click
"Turn on community plugins" once Obsidian opens the vault.
"""

import argparse
import difflib
import filecmp
import io
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

VAULT = Path(__file__).resolve().parents[3]

# Plugins installed from their latest GitHub release. All are also in Obsidian's
# community directory (ids below), so "Browse" in Obsidian is the manual route.
PLUGINS = [
    {"id": "templater-obsidian", "name": "Templater", "repo": "SilentVoid13/Templater"},
    {"id": "realclaudian", "name": "Claudian", "repo": "YishenTu/claudian"},
    # Shows `.claude/` (the shared skills, CLAUDE_*.md) in the file explorer, search and
    # Bases. Needs Obsidian >= 1.13; an older one lists the plugin but refuses to load it.
    {"id": "hidden-folders-access", "name": "Hidden Folders Access",
     "repo": "dsebastien/obsidian-hidden-folders-access"},
    {"id": "obsidian-outliner", "name": "Outliner", "repo": "vslinko/obsidian-outliner"},
]
HIDDEN_FOLDERS = [".claude"]  # the root dot-folders Hidden Folders Access is told to index
ASSETS = ["main.js", "manifest.json", "styles.css"]

SHARED_TEMPLATES = "shared_templates"   # the synced source, changed by agreement
LOCAL_TEMPLATES = "local_templates"     # the folder Templater runs: this machine's checked copy, never synced
TEMPLATE_PATH = LOCAL_TEMPLATES + "/project.md"
PROPERTIES_TEMPLATE = LOCAL_TEMPLATES + "/properties.md"
LEGACY_TEMPLATE_PATH = "templates/project.md"  # the shared folder was Templater's folder until 2026-09-20
HOTKEY_COMMAND = "templater-obsidian:" + TEMPLATE_PATH  # Templater names the command after the path
LEGACY_HOTKEY_COMMAND = "templater-obsidian:" + LEGACY_TEMPLATE_PATH
LEGACY_TEMPLATED_FOLDER = "projects-tasks-notes"  # had a Templater folder template until 2026-09-20; the entry is removed
# Code a vault template has no business containing: shell, network, the file system, other
# people's scripts, files other than the one being created. A hit blocks the copy.
UNSAFE_TEMPLATE_CODE = re.compile(
    r"tp\.system|tp\.user|tp\.web|require\s*\(|import\s*\(|fetch\s*\(|XMLHttpRequest|WebSocket"
    r"|child_process|process\.|electron|__dirname|\beval\s*\(|new\s+Function|adapter\.|localStorage"
    r"|vault\.(modify|create|createBinary|copy|rename|delete|trash)\s*\(|fileManager\.")
# Templater >= 2.25 keeps its creation trigger in Obsidian's localStorage, per device and per vault ID.
TEMPLATER_LOCAL_KEY = "templater-local-settings"
# Where "register Obsidian CLI" (Settings -> General -> Command line interface, INSTALL_AND_SETUP step 6) puts
# the command, for when it is not on this process's PATH: Linux, macOS, Windows.
CLI_PATHS = ["~/.local/bin/obsidian", "/usr/local/bin/obsidian", "%LOCALAPPDATA%/Programs/Obsidian/Obsidian.com"]
# Claudian's settings, and the folders it puts on its agents' PATH ahead of everything but the
# PATH line of its own "Shared environment" (macOS and Linux; ~/.local/bin comes after them).
CLAUDIAN_SETTINGS = ".claudian/claudian-settings.json"
CLAUDIAN_FIRST_DIRS = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin"]
HOTKEY = {"modifiers": ["Alt"], "key": "P"}
IGNORE_LINE = "#include .stignore-shared"

# The `## User` opener written into .claude/CLAUDE.md, and the exact first line it gets
# when no name is known anywhere — a CLAUDE.md still carrying that line is a stub to redo.
NAMELESS = "yourname"
CLAUDE_MD_INTRO = (
    "%s. In this vault they work on their team's projects; their name in `owner` / "
    "`next_action_by` is `%s`.\n\n"
    "(Replace this with a few lines about yourself — what you work on, your background per "
    "field so Claude can skip basics. Durable setup facts (machine, plan tier) belong in "
    "`.claude/skills/about-me/SKILL.md`, also yours alone.)\n")
NAMELESS_LINE = (CLAUDE_MD_INTRO % ("You", NAMELESS)).split("\n", 1)[0]

DONE, ALREADY, NEEDS_YOU, FAILED = "done", "already done", "needs you", "failed"

results = []  # (action, status, detail)
diffs = []  # unified diffs of shared templates that changed since their copy, printed after the table


def report(action, status, detail=""):
    results.append((action, status, detail))
    return status


# --------------------------------------------------------------------------- io

def read_json(path, default):
    """Existing JSON, or `default` when the file is absent. None = unparseable."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8") or "null") or default
    except (ValueError, OSError):
        return None


def write_text(path, text, dry_run):
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-setup-member")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_json(path, data, dry_run):
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", dry_run)


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "team-vault-setup"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ------------------------------------------------------------------- the actions

def identity_name():
    """The `user:` value in `_local/me.md` — the name this vault already knows about
    its owner, or None when the note is missing or has no such line."""
    path = VAULT / "_local" / "me.md"
    if not path.exists():
        return None
    found = re.search(r"^user:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
    return found.group(1) if found else None


def act_identity(name, dry_run):
    path = VAULT / "_local" / "me.md"
    if path.exists():
        known = identity_name()
        if known:
            return report("_local/me.md", ALREADY, "user: " + known)
        return report("_local/me.md", NEEDS_YOU, "exists but has no `user:` line — add one")
    if not name:
        return report("_local/me.md", NEEDS_YOU, "re-run with --name <your first name>")
    write_text(path, (
        "---\nuser: %s\n---\n\n"
        "Identity note for this device. Every base reads `user` from here to decide which rows "
        "are \"Mine\" — keep it to your own lowercase first name, the same string the others type "
        "into `owner` and `next_action_by`. Never synced (`.stignore-shared`) and never committed.\n"
    ) % name, dry_run)
    return report("_local/me.md", DONE, "user: " + name)


def act_plugin(plugin, dry_run):
    folder = VAULT / ".obsidian" / "plugins" / plugin["id"]
    manifest = folder / "manifest.json"
    if manifest.exists() and (folder / "main.js").exists():
        have = read_json(manifest, {}) or {}
        return report(plugin["name"] + " plugin files", ALREADY, "v%s in .obsidian/plugins/%s/"
                      % (have.get("version", "?"), plugin["id"]))
    if dry_run:
        return report(plugin["name"] + " plugin files", DONE, "would download latest release of "
                      + plugin["repo"])
    base = "https://github.com/%s/releases/latest/download/" % plugin["repo"]
    staging = Path(tempfile.mkdtemp(prefix="setup-member-"))
    try:
        for asset in ASSETS:
            (staging / asset).write_bytes(fetch(base + asset))
        got = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
        if got.get("id") != plugin["id"] or (staging / "main.js").stat().st_size < 10_000:
            return report(plugin["name"] + " plugin files", FAILED,
                          "release assets look wrong (id %r) — install it in Obsidian instead: "
                          "Settings \u2192 Community plugins \u2192 Browse \u2192 %s"
                          % (got.get("id"), plugin["name"]))
        folder.mkdir(parents=True, exist_ok=True)
        for asset in ASSETS:
            shutil.move(str(staging / asset), str(folder / asset))
        return report(plugin["name"] + " plugin files", DONE, "v%s \u2192 .obsidian/plugins/%s/"
                      % (got.get("version", "?"), plugin["id"]))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return report(plugin["name"] + " plugin files", FAILED,
                      "download failed (%s) — install it in Obsidian instead: Settings \u2192 "
                      "Community plugins \u2192 Browse \u2192 %s" % (exc, plugin["name"]))
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def act_local_templates(update, dry_run):
    """Templater runs whatever is in local_templates/ when the member calls its commands: copy
    the shared templates there only after the scan, and one that changed since its copy only
    once a person has read the diff (`--update-templates`)."""
    action = "Templates in " + LOCAL_TEMPLATES
    sources = sorted((VAULT / SHARED_TEMPLATES).glob("*.md"))
    if not sources:
        return report(action, NEEDS_YOU, "%s/ has not arrived yet \u2014 let the folder reach \"Up to Date\", then re-run"
                      % SHARED_TEMPLATES)
    copied, changed, unsafe, same = [], [], [], []
    for src in sources:
        text = src.read_text(encoding="utf-8")
        hit = UNSAFE_TEMPLATE_CODE.search(text)
        if hit:
            unsafe.append("%s has `%s`" % (src.name, hit.group(0)))
            continue
        dst = VAULT / LOCAL_TEMPLATES / src.name
        have = dst.read_text(encoding="utf-8") if dst.exists() else None
        if have == text:
            same.append(src.name)
        elif have is not None and not update:
            changed.append(src.name)
            diffs.append("".join(difflib.unified_diff(have.splitlines(True), text.splitlines(True),
                                                      LOCAL_TEMPLATES + "/" + src.name,
                                                      SHARED_TEMPLATES + "/" + src.name)))
        else:
            write_text(dst, text, dry_run)
            copied.append(src.name + (" (updated)" if have is not None else ""))
    detail = ([("copied " + ", ".join(copied))] if copied else []) + \
             ([("up to date: " + ", ".join(same))] if same else [])
    if unsafe:
        return report(action, NEEDS_YOU, "NOT copied \u2014 %s: code a template should not need; tell the vault "
                      "owner. %s" % ("; ".join(unsafe), "; ".join(detail)))
    if changed:
        return report(action, NEEDS_YOU, "%s changed in %s/ since the copy \u2014 read the diff printed below, "
                      "then re-run with --update-templates. %s" % (", ".join(changed), SHARED_TEMPLATES, "; ".join(detail)))
    return report(action, DONE if copied else ALREADY, "; ".join(detail))


def act_templater_settings(dry_run):
    path = VAULT / ".obsidian" / "plugins" / "templater-obsidian" / "data.json"
    data = read_json(path, {})
    if data is None:
        return report("Templater settings", NEEDS_YOU, "%s is not valid JSON \u2014 delete it and re-run" % path.name)

    def template_of(entry):  # a path string or {"template": path, ...} (Templater >= 2.23)
        return entry if isinstance(entry, str) else (entry or {}).get("template")

    hotkeys = [h for h in (data.get("enabled_templates_hotkeys") or []) if template_of(h) != LEGACY_TEMPLATE_PATH]
    hotkeys += [t for t in (TEMPLATE_PATH, PROPERTIES_TEMPLATE) if not any(template_of(h) == t for h in hotkeys)]
    # Nothing runs on creation any more (act_creation_trigger): drop the folder template wired until 2026-09-20.
    folders = [f for f in (data.get("folder_templates") or [])
               if not (isinstance(f, dict) and f.get("folder") == LEGACY_TEMPLATED_FOLDER)]
    wanted = {
        "data_version": 2,                        # >= 2.25 schema, in which the pre-2.25 keys below are dead
        "templates_folder": LOCAL_TEMPLATES,
        "trigger_on_file_creation_mode": "none",  # nothing to apply, should the (device-local) trigger ever be on
        "folder_templates": folders,
        "enabled_templates_hotkeys": hotkeys,
    }
    legacy = [k for k in ("trigger_on_file_creation", "enable_folder_templates", "enable_file_templates") if k in data]
    if not legacy and all(data.get(k) == v for k, v in wanted.items()):
        return report("Templater settings", ALREADY, "template folder, no folder template, hotkey commands")
    for key in legacy:
        del data[key]
    data.update(wanted)
    write_json(path, data, dry_run)
    return report("Templater settings", DONE,
                  "templates folder = %s, no template on creation, commands \"Insert project\" and "
                  "\"Insert properties\" registered" % LOCAL_TEMPLATES)


def find_cli():
    """The registered `obsidian` command, or None. Its known locations come before PATH, and on
    Linux PATH is not asked at all: a Linux package installs the desktop app itself as
    /usr/bin/obsidian, and running that as a CLI starts a second Obsidian."""
    for candidate in CLI_PATHS:
        path = os.path.expandvars(os.path.expanduser(candidate))
        if os.path.isfile(path):
            return path
    return None if sys.platform.startswith("linux") else shutil.which("obsidian")


def obsidian_eval(code):
    """Run JavaScript inside the open Obsidian through its CLI (Obsidian >= 1.12: Settings ->
    General -> Command line interface). The printed result, or None when there is no CLI or
    the vault is not open."""
    cli = find_cli()
    if not cli:
        return None
    try:
        run = subprocess.run([cli, "vault=" + VAULT.name, "eval", "code=" + code],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return run.stdout.strip() if run.returncode == 0 else None


def act_creation_trigger(dry_run):
    """Templater's "Trigger Templater on new file creation" switch (>= 2.25) lives in Obsidian's
    localStorage, per device, so only the open Obsidian can flip it. In a synced vault it has to
    be OFF: on, Templater runs the template commands inside any non-empty note that appears on
    disk, the notes other members' machines sync in included, and re-saves every such note, which
    Syncthing passes on as an edit by this member. This script switched it on until 2026-09-20."""
    action = "Templater creation trigger off"
    manual = ("make sure it is off: Settings \u2192 Templater \u2192 \"Trigger Templater on new file creation\" (off is "
              "Templater's default; a setup run before 2026-09-21 switched it on)")
    key = json.dumps(TEMPLATER_LOCAL_KEY)
    read = "JSON.stringify(app.loadLocalStorage(%s) || {})" % key
    state = obsidian_eval(read)
    if not state or "{" not in state:  # no CLI, or it reached no open vault (prints nothing then)
        return report(action, NEEDS_YOU, "could not ask the open Obsidian (the `obsidian` command is registered in "
                                         "INSTALL_AND_SETUP step 6) \u2014 " + manual)
    if '"trigger_on_file_creation":true' not in state:
        return report(action, ALREADY, "off (device-local, in Obsidian's localStorage)")
    if dry_run:
        return report(action, DONE, "would switch it off through the Obsidian CLI")
    state = obsidian_eval("app.saveLocalStorage(%s, Object.assign({}, app.loadLocalStorage(%s) || {}, "
                          "{trigger_on_file_creation: false})); %s" % (key, key, read))
    if state and "{" in state and '"trigger_on_file_creation":true' not in state:
        return report(action, DONE, "switched off (through the Obsidian CLI; Templater reads the switch live)")
    return report(action, NEEDS_YOU, "could not switch it off through the Obsidian CLI \u2014 " + manual)


def path_line_first(env_text, folder):
    """Claudian's KEY=VALUE lines with `folder` leading the PATH line (the last one counts)."""
    lines = env_text.split("\n") if env_text else []
    for i in reversed(range(len(lines))):
        line = lines[i].strip()
        key, eq, value = (line[7:] if line.startswith("export ") else line).partition("=")
        if eq and key.strip() == "PATH":
            rest = [p for p in value.strip().strip("\"'").split(os.pathsep) if p and p != folder]
            lines[i] = "PATH=" + os.pathsep.join([folder] + rest)
            return "\n".join(lines)
    return "\n".join(lines + ["PATH=" + folder])


def act_claudian_cli_path(dry_run):
    """Claudian looks for commands in CLAUDIAN_FIRST_DIRS before the member's own folders, so where
    a Linux package installs the desktop app as /usr/bin/obsidian, `obsidian` in a Claudian session
    is the app instead of the CLI registered in ~/.local/bin: every call starts another Obsidian,
    and with none running the call becomes the app. A PATH line in Claudian's shared environment
    is the one thing Claudian puts in front of those folders."""
    action = "Obsidian CLI inside Claudian"
    cli = find_cli()
    first = None if os.name == "nt" else next(
        (p for p in (os.path.join(d, "obsidian") for d in CLAUDIAN_FIRST_DIRS) if os.path.isfile(p)), None)
    if not first or (cli and (os.path.realpath(first) == os.path.realpath(cli)
                              or filecmp.cmp(first, cli, shallow=False))):
        return report(action, ALREADY, "`obsidian` means the CLI there")
    if not cli:
        return report(action, NEEDS_YOU,
                      "`obsidian` in a Claudian session is the desktop app (%s), so every call starts another "
                      "Obsidian \u2014 register the CLI (INSTALL_AND_SETUP step 6), then re-run" % first)
    folder = os.path.dirname(cli)
    path = VAULT / CLAUDIAN_SETTINGS
    data = read_json(path, {})
    if data is None or not isinstance(data, dict):
        return report(action, NEEDS_YOU, "%s is not valid JSON \u2014 put the line PATH=%s into Settings \u2192 "
                                         "Claudian \u2192 Shared environment yourself" % (CLAUDIAN_SETTINGS, folder))
    old = data.get("sharedEnvironmentVariables")
    old = old if isinstance(old, str) else ""
    new = path_line_first(old, folder)
    if new == old:
        return report(action, ALREADY, "Claudian's PATH starts with %s" % folder)
    detail = "%s first on Claudian's PATH (%s is the desktop app, and Claudian looked there first)" % (folder, first)
    if dry_run:
        return report(action, DONE, "would put " + detail)
    # A loaded Claudian rewrites its settings file from memory, so change it there when it runs.
    queued = obsidian_eval(
        "(() => { const p = app.plugins.plugins.realclaudian; if (!p || !p.mutateSettings) return 'absent'; "
        "p.mutateSettings(s => { s.sharedEnvironmentVariables = %s; }); return 'queued'; })()" % json.dumps(new))
    if queued and "queued" in queued:
        for _ in range(10):
            time.sleep(0.3)
            if (read_json(path, {}) or {}).get("sharedEnvironmentVariables") == new:
                return report(action, DONE, detail + " \u2014 set through the running Claudian; agents it has "
                                                   "already started keep the old PATH until Obsidian's restart")
    data["sharedEnvironmentVariables"] = new
    write_json(path, data, dry_run)
    return report(action, DONE, detail + " \u2014 written to its settings file: restart Obsidian before changing "
                                       "anything in Claudian, which saves its settings from memory")


def act_hidden_folders_settings(dry_run):
    path = VAULT / ".obsidian" / "plugins" / "hidden-folders-access" / "data.json"
    data = read_json(path, {})
    if data is None or not isinstance(data, dict):
        return report("Hidden Folders Access settings", NEEDS_YOU, "%s is not valid JSON — delete it and re-run" % path.name)
    folders = [f for f in (data.get("enabledFolders") or []) if isinstance(f, str)]
    missing = [f for f in HIDDEN_FOLDERS if f not in folders]
    if not missing:
        return report("Hidden Folders Access settings", ALREADY, "shows " + ", ".join(HIDDEN_FOLDERS))
    data["enabledFolders"] = folders + missing
    write_json(path, data, dry_run)
    return report("Hidden Folders Access settings", DONE, "enabledFolders: " + ", ".join(missing))


def act_community_plugins(dry_run):
    path = VAULT / ".obsidian" / "community-plugins.json"
    enabled = read_json(path, [])
    if enabled is None or not isinstance(enabled, list):
        return report("Plugins enabled", NEEDS_YOU, "community-plugins.json is not a JSON list — delete it and re-run")
    missing = [p["id"] for p in PLUGINS if p["id"] not in enabled]
    if not missing:
        return report("Plugins enabled", ALREADY, ", ".join(p["id"] for p in PLUGINS))
    write_json(path, enabled + missing, dry_run)
    return report("Plugins enabled", DONE, "listed in community-plugins.json: " + ", ".join(missing))


def act_hotkey(dry_run):
    path = VAULT / ".obsidian" / "hotkeys.json"
    data = read_json(path, {})
    if data is None or not isinstance(data, dict):
        return report("Hotkey Alt+P", NEEDS_YOU, "hotkeys.json is not a JSON object — delete it and re-run")
    if LEGACY_HOTKEY_COMMAND in data:  # bound before the templates folder moved (2026-09-20)
        binding = data.pop(LEGACY_HOTKEY_COMMAND)
        data.setdefault(HOTKEY_COMMAND, binding)
        write_json(path, data, dry_run)
        return report("Hotkey Alt+P", DONE, "moved from the old command %s to %s" % (LEGACY_HOTKEY_COMMAND, HOTKEY_COMMAND))
    if HOTKEY_COMMAND in data:
        bound = data[HOTKEY_COMMAND]
        return report("Hotkey Alt+P", ALREADY, "%s \u2192 %s" % (HOTKEY_COMMAND, json.dumps(bound)))
    clash = [cmd for cmd, binds in data.items()
             if any(b.get("key", "").upper() == "P" and sorted(b.get("modifiers", [])) == ["Alt"]
                    for b in (binds or []) if isinstance(b, dict))]
    if clash:
        return report("Hotkey Alt+P", NEEDS_YOU,
                      "Alt+P is already bound to %s here — pick a key in Settings \u2192 Hotkeys for "
                      "\"Templater: Insert project\"" % clash[0])
    data[HOTKEY_COMMAND] = [HOTKEY]
    write_json(path, data, dry_run)
    return report("Hotkey Alt+P", DONE, "Alt+P \u2192 Templater: Insert project")


def act_new_file_location(dry_run):
    path = VAULT / ".obsidian" / "app.json"
    data = read_json(path, {})
    if data is None or not isinstance(data, dict):
        return report("New notes beside their project", NEEDS_YOU, "app.json is not a JSON object — delete it and re-run")
    if data.get("newFileLocation") == "current":
        return report("New notes beside their project", ALREADY, "newFileLocation: current")
    data["newFileLocation"] = "current"
    write_json(path, data, dry_run)
    return report("New notes beside their project", DONE, "app.json newFileLocation: current")


def act_claude_md(name, dry_run):
    path = VAULT / ".claude" / "CLAUDE.md"
    # `_local/me.md` wins over `--name`: it is the name the bases actually read, this
    # script never overwrites it, and on a repair run (the skill tells the member to
    # drop `--name` once the note exists) it is the only place the name still is.
    name = identity_name() or name
    if path.exists():
        if name and NAMELESS_LINE in path.read_text(encoding="utf-8"):
            return report(".claude/CLAUDE.md", NEEDS_YOU,
                          "still the nameless version (written before the name was known) \u2014 "
                          "delete it (or just fix the first line under `## User`) and re-run "
                          "to get `%s` into it" % name)
        return report(".claude/CLAUDE.md", ALREADY, "your personal instructions are there")
    template = VAULT / ".claude" / "CLAUDE_template.md"
    if not template.exists():
        return report(".claude/CLAUDE.md", NEEDS_YOU, "CLAUDE_template.md has not arrived yet — copy it by hand later")
    text = template.read_text(encoding="utf-8")
    # Keep the template from its `@CLAUDE_shared.md` import on; the lines above it
    # are the "copy me" preamble, which the copy does not need.
    cut = text.find("@CLAUDE_shared.md")
    body = text[cut:] if cut != -1 else text
    who = (name or "you").capitalize()
    intro = CLAUDE_MD_INTRO % (who, name or NAMELESS)
    marker = "## User\n"
    if marker in body:
        head, _, rest = body.partition(marker)
        rest = re.sub(r"\A\s*\(.*?\)\s*\n", "", rest, flags=re.S)  # drop the template's placeholder
        body = head + marker + "\n" + intro + "\n" + rest.lstrip("\n")
    write_text(path, body, dry_run)
    return report(".claude/CLAUDE.md", DONE, "from CLAUDE_template.md, `%s` filled in" % (name or NAMELESS))


def act_settings_local(dry_run):
    path = VAULT / ".claude" / "settings.local.json"
    data = read_json(path, {})
    if data is None or not isinstance(data, dict):
        return report(".claude/settings.local.json", NEEDS_YOU, "not valid JSON — delete it and re-run")
    env = data.get("env") or {}
    if env.get("CLAUDE_CODE_FORK_SUBAGENT") == "1":
        return report(".claude/settings.local.json", ALREADY, "forkmode enabled")
    env["CLAUDE_CODE_FORK_SUBAGENT"] = "1"
    data["env"] = env
    write_json(path, data, dry_run)
    return report(".claude/settings.local.json", DONE, "forkmode enabled (microskills 13–14 of CLAUDE.md)")


# ------------------------------------------------------------------- syncthing

def syncthing_api():
    """(base_url, apikey) of the Syncthing running for this user, or None."""
    home = Path.home()
    candidates = [
        home / ".local/state/syncthing/config.xml",
        home / ".config/syncthing/config.xml",
        home / "Library/Application Support/Syncthing/config.xml",
        Path(os.environ.get("LOCALAPPDATA", home)) / "Syncthing/config.xml",
    ]
    if os.environ.get("STHOME"):
        candidates.insert(0, Path(os.environ["STHOME"]) / "config.xml")
    for cfg in candidates:
        try:
            gui = ET.parse(cfg).getroot().find("gui")
        except (OSError, ET.ParseError):
            continue
        if gui is None:
            continue
        address = (gui.findtext("address") or "127.0.0.1:8384").rsplit(":", 1)
        scheme = "https" if gui.get("tls") == "true" else "http"
        return "%s://127.0.0.1:%s" % (scheme, address[-1]), (gui.findtext("apikey") or "")
    return None


def st_call(base, key, path, payload=None):
    req = urllib.request.Request(base + path, headers={"X-API-Key": key,
                                                       "Content-Type": "application/json"})
    if payload is not None:
        req.data = json.dumps(payload).encode()
        req.method = "POST"
    context = ssl._create_unverified_context() if base.startswith("https") else None
    with urllib.request.urlopen(req, timeout=20, context=context) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None


def stignore_file_has_line():
    path = VAULT / ".stignore"
    return path.exists() and IGNORE_LINE in path.read_text(encoding="utf-8").splitlines()


def act_syncthing_ignores(dry_run):
    action = "Syncthing ignore line"
    if not (VAULT / ".stignore-shared").exists():
        return report(action, NEEDS_YOU,
                      ".stignore-shared has not arrived yet — let the folder reach \"Up to Date\", then re-run "
                      "(an #include of a missing file stops the folder syncing)")
    api = syncthing_api()
    if api:
        base, key = api
        try:
            folders = st_call(base, key, "/rest/config/folders") or []
            mine = [f for f in folders
                    if os.path.normcase(os.path.realpath(os.path.expanduser(f.get("path", "x"))))
                    == os.path.normcase(str(VAULT))]
            if mine:
                fid = mine[0]["id"]
                current = (st_call(base, key, "/rest/db/ignores?folder=" + fid) or {}).get("ignore") or []
                if IGNORE_LINE in current:
                    return report(action, ALREADY, "folder %s already includes .stignore-shared" % fid)
                if not dry_run:
                    st_call(base, key, "/rest/db/ignores?folder=" + fid,
                            {"ignore": current + [IGNORE_LINE]})
                return report(action, DONE, "added to Syncthing folder %s (active now)" % fid)
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            pass  # fall through to the file route
    # No reachable API, or this folder is not (yet) a Syncthing folder here.
    if stignore_file_has_line():
        return report(action, ALREADY, ".stignore in the vault root has the line")
    if not dry_run:
        path = VAULT / ".stignore"
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        write_text(path, (old + "\n" if old and not old.endswith("\n") else old) + IGNORE_LINE + "\n", dry_run)
    return report(action, DONE,
                  "wrote .stignore in the vault root; Syncthing applies it at its next scan of this "
                  "folder — to apply it now, paste \"%s\" into the folder's Edit \u2192 Ignore Patterns" % IGNORE_LINE)


# ------------------------------------------------------------------------ main

def main():
    # On Windows a piped stdout (as under Claude Code) is cp1252 up to Python 3.14, which cannot
    # encode the `\u2192` in the report or a name like `\u0142ukasz` \u2014 the final write would raise after
    # every action had already succeeded. Force UTF-8 (`replace` so nothing can ever crash it).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Set this shared vault up on one member's machine.")
    parser.add_argument("--name", help="the member's first name, one word, any alphabet "
                                       "(lowercased here; only needed the first time)")
    parser.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    parser.add_argument("--update-templates", action="store_true",
                        help="replace a local template whose shared original changed, once its diff "
                             "(printed by a previous run) has been read")
    args = parser.parse_args()

    for marker in ("README.md", "me.base", ".claude/CLAUDE_shared.md", SHARED_TEMPLATES + "/project.md"):
        if not (VAULT / marker).exists():
            sys.exit("%s does not look like the shared vault (no %s) — is this script still inside it?"
                     % (VAULT, marker))
    if (VAULT / ".git").exists():
        sys.exit("%s has a .git — this is the automation host, which is set up by VPS_SETUP_INFO.md, not by this "
                 "script. Nothing was changed." % VAULT)

    # One whitespace-free token in any alphabet — `joão`, `zoë`, `łukasz` are names, "Matilda
    # Smith" and paths are not. `:` and the slashes would break the `user:` YAML line; the first
    # character must be alphanumeric for the same reason (a leading `#`, quote or `-` is YAML).
    name = (args.name or "").strip().lower() or None
    if name and (any(c.isspace() for c in name) or set("/\\:") & set(name) or not name[0].isalnum()):
        sys.exit("--name should be a single first name with no spaces (any alphabet, e.g. joão): got %r"
                 % args.name)

    act_syncthing_ignores(args.dry_run)  # first: nothing private below is written before its ignore line
    act_identity(name, args.dry_run)
    for plugin in PLUGINS:
        act_plugin(plugin, args.dry_run)
    act_local_templates(args.update_templates, args.dry_run)
    act_templater_settings(args.dry_run)
    act_creation_trigger(args.dry_run)
    act_claudian_cli_path(args.dry_run)
    act_hidden_folders_settings(args.dry_run)
    act_community_plugins(args.dry_run)
    act_hotkey(args.dry_run)
    act_new_file_location(args.dry_run)
    act_claude_md(name, args.dry_run)
    act_settings_local(args.dry_run)

    out = io.StringIO()
    print("vault: %s%s" % (VAULT, "   (DRY RUN — nothing written)" if args.dry_run else ""), file=out)
    width = max(len(a) for a, _, _ in results)
    for action, status, detail in results:
        print("  %-*s  %-11s  %s" % (width, action, status, detail), file=out)
    for diff in diffs:
        print(file=out)
        print(diff.rstrip("\n"), file=out)
    left = [r for r in results if r[1] in (NEEDS_YOU, FAILED)]
    print(file=out)
    print("Still on you: restart Obsidian (quit and reopen it) — it reads .obsidian/community-plugins.json "
          "only at startup, so the plugins load only then. If Obsidian shows a "
          "\"Restricted mode\" dialog when it opens the vault, click \"Turn on community plugins\" "
          "(Settings → Community plugins has the same switch) — Obsidian keeps it outside the "
          "vault, so no program can flip it for you. From then on Alt+P gives a `,` project its "
          "sections, and the command \"Templater: Insert properties\" fills the properties of a note "
          "made without a base's New button (the button fills `owner` and `parent` by itself).", file=out)
    if left:
        print("Also unfinished: " + "; ".join("%s (%s)" % (a, s) for a, s, _ in left), file=out)
    sys.stdout.write(out.getvalue())
    return 1 if any(r[1] == FAILED for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
