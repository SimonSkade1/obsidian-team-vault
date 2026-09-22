---
name: setup-member
description: Finish this shared vault's setup on the person's own machine — identity note, the plugins (Templater, Claudian, Hidden Folders Access, Outliner) installed and enabled, the checked local copy of the note templates with the Alt+P hotkey, new-note location, their personal CLAUDE.md, the Syncthing ignore line. Use when someone says "complete the setup", "set up this vault for me", "finish my onboarding", "update the templates", "set up my private folder" or runs /setup-member here, when a template in `shared_templates/` changed, or when they are visibly a new member of this vault (no `_local/me.md`, no `.obsidian/plugins/`).
---

# Complete a member's setup of this vault

A new member has synced the vault, opened it in Obsidian with Claudian installed, and is talking to you from the Claudian pane (`INSTALL_AND_SETUP.md` steps 6–7; a terminal `claude` in the vault folder is the fallback). Everything that can be done from disk is done by one script; you ask one question, report what it did, and tell them to restart Obsidian.

## Do this

1. **Ask for the first name — but only if `_local/me.md` is missing.** One word, lowercase, the string the others will type into `owner` and `next_action_by`. Any alphabet: `joão`, `zoë`, `łukasz` are fine — the bases compare `user` as plain text. That is the only question this setup needs; decide everything else from the vault.
2. **Run the script** from the vault root:

	```
	python3 .claude/skills/setup-member/setup_member.py --name <firstname>
	```

	Windows: `py -3` instead of `python3` — the python.org install has no `python3` command. Drop `--name` when the identity note already exists. It takes a few seconds (≈6 MB of plugin downloads). Every action is checked before it is done, so re-running it after a failure or a half-finished attempt is safe — it reports `already done` instead of redoing work. `--dry-run` reports without writing anything; `--update-templates` accepts a changed shared template once you have read its diff (pt 4).
	1. **Obsidian is open while this runs** (you are inside it), so tell them to restart it afterwards: Obsidian reads `community-plugins.json` only at startup (and writes its in-memory list back over it if a plugin is toggled before then), so the plugins the script installed load only after the restart; `app.json` and `hotkeys.json` it picks up live. On the terminal route with Obsidian closed no restart is needed.
3. **Relay its table**, then tell them the two things that are left:
	1. **Restart Obsidian** (quit and reopen) — that loads the plugins. If Obsidian then shows a *Restricted mode* dialog (only on the terminal route, when the vault had never been opened), **Turn on community plugins** there or under **Settings → Community plugins**; Obsidian stores that switch outside the vault, which is why no program can flip it.
	2. **The end-to-end test**: `me.base` → **New** → name it `!test` → **Enter**. It worked when the row shows under **4 Your Tasks** with their name in `owner` — the base's New button fills it from `_local/me.md`. Then they rename it to `,test`, open it, put the cursor at the end and press **Alt+P**: the project sections with the subtasks table appear. Then delete it.
4. **Anything the table marks `needs you` or `failed`** is yours to fix or explain — the detail column says what is wrong. Common ones: the folder has not finished its first sync (`.stignore-shared` missing) — wait for *Up to Date* and run again; Alt+P already taken in this vault — offer to bind another key in `.obsidian/hotkeys.json`; a plugin download failed — the member installs it from Obsidian's **Community plugins → Browse** instead (`Templater`, `Hidden Folders Access`, `Outliner`; `Claudian` is already there when they talk to you through it).
	1. **`Templates in local_templates` — needs you.** Either a shared template changed since its copy: read the diff the script printed together with the template's header comment, and accept it with `--update-templates` only if the code does just what the comment says — emits text for the note it is inserted into, reads `_local/me.md`, nothing else (no shell, network, other files, other people's scripts). Or the scan hit code a template should not need: copy nothing and tell the vault owner (`simon`) what you found.
	2. **`Templater creation trigger off` — needs you.** The script could not make sure the switch is off: Templater keeps it outside the vault (Obsidian's localStorage), which the script reaches only through the `obsidian` command that INSTALL_AND_SETUP step 6 registers, and only while Obsidian is open. Off is Templater's default, so on a machine that never ran this setup before 2026-09-21 nothing is wrong; otherwise the member looks once Templater is loaded: **Settings → Templater → Trigger Templater on new file creation** → off.

## What the script touches, so you can explain or repair it

Inside the vault only: `_local/me.md`; `.obsidian/plugins/<id>/` for the script's `PLUGINS` list — `templater-obsidian`, `realclaudian`, `hidden-folders-access`, `obsidian-outliner` (latest GitHub release of `SilentVoid13/Templater`, `YishenTu/claudian`, `dsebastien/obsidian-hidden-folders-access`, `vslinko/obsidian-outliner`, all four also in Obsidian's community directory — Claudian is normally already there from INSTALL_AND_SETUP step 6 and reports `already done`) plus `local_templates/` (copies of `shared_templates/*.md`, made only after a scan for code a template has no business containing and, once a copy exists, refreshed only through `--update-templates` — templates are JavaScript that Templater runs when the member calls their commands, and this is what keeps something that merely arrived over the network from running), Templater's `data.json` (templates folder `local_templates`, the commands *Insert project* and *Insert properties*, no folder template — the one a setup before 2026-09-21 wired is removed), Templater's device-local creation trigger, switched **off** (Obsidian localStorage key `templater-local-settings`, reachable only through the `obsidian` CLI's `eval`) and Hidden Folders Access' `data.json` (`enabledFolders: [".claude"]`, so the shared skills and `CLAUDE_*.md` show in the file explorer and search; the plugin needs Obsidian ≥ 1.13 — an older one lists it but refuses to load it, so **Settings → About → Check for updates** is the fix); `.claudian/claudian-settings.json` (only where a Linux package installed the desktop app as `/usr/bin/obsidian`: Claudian searches that folder before `~/.local/bin`, so `obsidian` in a Claudian session would start another Obsidian instead of reaching the open one — a `PATH=` line in Claudian's *Shared environment* puts the registered CLI's folder first); `.obsidian/community-plugins.json`, `hotkeys.json` (Alt+P → *Templater: Insert project*; a binding of the pre-2026-09-20 command `templater-obsidian:templates/project.md` is moved over), `app.json` (`newFileLocation: current`); `.claude/CLAUDE.md` from `CLAUDE_template.md` and `.claude/settings.local.json`. JSON files are merged, never replaced.

Why the creation trigger stays off: with it on, Templater runs the template commands inside any non-empty note that appears on disk — every note another member's machine syncs in included, so whoever can write to the vault could run code on each member's machine (a guard inside a template does not help: a folder template is only applied to empty notes). It also re-saves every newly arrived note, which Syncthing passes on as an edit by this member and which can end in a sync conflict while the author is still typing. What the trigger used to do needs no code now: the New button of `me.base` and `subtasks.base` fills `owner` and `parent` from filter clauses (`obsidian-bases` skill); the properties of a note made another way and a project's sections are inserted by command.

The one thing outside: this folder's Syncthing ignore list gets the line `#include .stignore-shared`, set through the local Syncthing API (folder matched by path) or, if that is unreachable, by writing `.stignore` in the vault root. Without it the member's Syncthing keeps announcing and rescanning their private files.

The script refuses to run where a `.git` exists in the vault root — that is the automation host, which `VPS_SETUP_INFO.md` sets up instead.

If `python3` (Windows: `py -3`) is missing on this machine, read `setup_member.py` and make the same writes with your own tools rather than sending the member to the manual fallback.

## Private folder — only when the member asks for one

`private-projects-tasks-notes/` is a member's own unsynced twin of `projects-tasks-notes/` — same prefixes, properties and `![[subtasks.base]]` — watched through `private.base`. Not part of the script; from the vault root:

1. Check that `.stignore` holds `#include .stignore-shared` and that `.stignore-shared` lists `/private-projects-tasks-notes` and `/private.base`. Those lines keep both off the network, so they have to be there before the folder is.
2. Create the folder, and generate the base from `me.base` instead of writing it — it is `me.base` with the folder swapped, so re-run this whenever `me.base` changed:

	```
	mkdir -p private-projects-tasks-notes
	sed -e 's#inFolder("projects-tasks-notes")#inFolder("private-projects-tasks-notes")#' -e 's#^newItemFolder: .*#newItemFolder: private-projects-tasks-notes#' me.base > private.base
	```

	Without `sed` (plain Windows shell), make the same two replacements with your own tools.
3. Tell them what unsynced means: no copy on the hub and no nightly snapshot, so backing the folder up is theirs to arrange; and a shared note that links to a private one shows everyone its title as a dead link.
