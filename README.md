# obsidian-team-vault — project management with Obsidian and Claude Code, alone or as a team

A vault for running projects: every project, task and note is one file with nine properties; [Obsidian Bases](https://help.obsidian.md/bases) turn those into per-person dashboards; [Claude Code](https://claude.com/claude-code) works inside the vault through the [Claudian](https://obsidian.md/plugins?id=realclaudian) plugin — including the "VNA" scaffold, which writes a project's spec, plans it into children and runs them one by one in fresh subagents. Optionally a team shares the vault through [Syncthing](https://syncthing.net), with one always-on machine running nightly summaries and cleanup. It is the live vault of PauseAI Global's infrastructure team with the content removed.

## Setup on one machine (~10 minutes)

1. **Get the files**: `git clone --depth 1 https://github.com/SimonSkade1/obsidian-team-vault.git` and delete the `.git` folder (`rm -rf obsidian-team-vault/.git`), or **Code → Download ZIP** and unpack it as `obsidian-team-vault`. A vault is not a git checkout: only a team's automation host keeps a repository (its own), and step 4 refuses to run next to one.
2. **Install** [Obsidian](https://obsidian.md/download) (a current version — the views are Bases, tested on 1.13.7), [Claude Code](https://claude.com/claude-code) (`curl -fsSL https://claude.ai/install.sh | bash`; Windows: `irm https://claude.ai/install.ps1 | iex`) and run `claude` once to log in with your own subscription; have Python 3.8+ (`python3 --version`; Windows: `py -3 --version`). OS details: [`INSTALL_AND_SETUP.md`](INSTALL_AND_SETUP.md) steps 3, 4 and 6.
3. **Open the folder as a vault** in Obsidian → **Turn on community plugins** → **Browse** → `Claudian` → **Install** → **Enable**. Then **Settings → General → Command line interface** → on: that registers the `obsidian` command Claude uses to reach the running app (to finish step 4, and later to move and rename notes without breaking links).
4. **Click the robot icon** (Claudian) and type `complete the setup`. It asks for your first name (lowercase — the string used in `owner` and `reviewer`), then installs Templater, Hidden Folders Access and Outliner, your checked copy of the note templates with the **Alt+P** hotkey, `_local/me.md` (your identity, read by every view) and your personal `.claude/CLAUDE.md`. Approve the commands it asks to run.
5. **Read the rest of this file** — below the line is the vault's own README, as members see it (5 minutes) — then do the five-minute exercise in `projects-tasks-notes/Vault tutorial exercise/`.

## Team use (optional)

Several people, one folder, no server software: [`TEAM_SETUP.md`](TEAM_SETUP.md) — Syncthing hub-and-spoke through one always-on machine, which also runs the nightly git snapshot, summaries and cleanup; each member's onboarding is [`INSTALL_AND_SETUP.md`](INSTALL_AND_SETUP.md).

## Where things are

1. `*.base` — the views: `me.base` (your overview), `subtasks.base` (embedded in every project), `recent.base`; [`shared_templates/`](shared_templates) — the note templates; [`projects-tasks-notes/`](projects-tasks-notes) — all items, empty but for the tutorial.
2. [`.claude/`](.claude) — Claude's shared instructions (`CLAUDE_shared.md`, imported by each member's own `CLAUDE.md`), skills (`vna-*`, `setup-member`, `handoff`, `obsidian-bases`, …), agent definitions and scripts.
3. [`other-files/`](other-files) — the automation host's scripts, config and its setup doc `VPS_SETUP_INFO.md`.
4. Exported from the live vault by a script (not included: it holds the strings it redacts), so the docs name that team's people and machines — `TEAM_SETUP.md` lists what to replace. `[[wikilinks]]` resolve in Obsidian, not on GitHub.

---

# How to use this vault

Here is a video on how to use this vault (not completely up to date but mostly): https://drive.google.com/file/d/1-I16xe_iM7RDpa0E5xWXfsMx_sPfb18L/view?usp=sharing

How the vault is used day to day. Machine not set up yet? First the setup steps above (one machine) or [[INSTALL_AND_SETUP]] (joining a team's vault). Read this file (5 minutes), then do the five-minute exercise in [[,Vault tutorial exercise]].

## Files

1. **The name sets the type**: `,name` = project, `!name` = task, no prefix = note. Renaming changes the type.
2. **Nine properties**, written by the **New** button when you create a file (see *Creating items*):
	1. `status` — empty = active; or `in-progress`, `inbox`, `review` (finished, the reviewer checks), `exception` (set only by Claude's VNA runs), `done`, `cancelled`, `failed`. Nothing else.
	2. `priority` — 1–10, **10 = most important**, empty counts as 5; sorts within a section, highest first.
	3. `parent` — one link to its project, `"[[,name]]"`; empty = top of a tree.
	4. `owner` — who does it: a link to the person, `"[[harry]]"` (type `[[` and pick the name). Vault members have a file in `vault-members/`. Someone outside the vault: a link only if they'll likely join (it stays unresolved until they do), else just their name.
	5. `reviewer` (formerly `stakeholder`) — the one person it is for, who tracks and reviews it (written like `owner`); empty = the owner. **New** sets it to the parent project's owner (no parent: to you).
	6. `not_before` — a date; the item sits under `10 Later Tasks` (a note: `11 Later Notes`) until then, sorted by this date, soonest first.
	7. `dependencies` — links to the items this one waits for (`"[[!name]]"`, a list); while any of them is unfinished (`review` counts as finished), the item sits under `9 Blocked`.
	8. `due` — a date; sorts the item as if its `priority` were 1 higher on that day and 2 higher once it has passed. Nothing else changes.
	9. `subscribers` — people (links, like `owner`) who want to see it without owning it.
(Files that Claude's VNA runs create also carry `model` and `effort`; humans can ignore them.)

## Your project and task overview: [[me.base]]

1. **Views**: **my overview** = all top-level open items, plus subfiles of your projects that are in sections 1–3 or 6, ordered by sections below; **my projects** = all your open items, grouped by project; **everyone overview** / **everyone projects** = the same for everyone's items; **Archived** = finished (`done`, `cancelled`, `failed`), **Unassigned** = no owner (shouldn't exist but fallback in case it does).
2. **Sections**:
	1. `1 Inbox`
	2. `2 In Progress`
	3. `3 Review` (status = review, you are the reviewer: check it, then set `done`)
	4. `4 Your Tasks` (your other open items)
	5. `5 Delegated` (someone else — a member, an external person or Claude — is owner, you are the reviewer)
	6. `6 Awaiting Review` (your `review` items that someone else checks)
	7. `7 Subscribed` (you are in the subscriber column)
	8. `8 Notes` (files that don't start with `,` or `!`)
	9. `9 Blocked` (an unfinished item in `dependencies`)
	10. `10 Later Tasks` (`not_before` in the future)
	11. `11 Later Notes`
	12. `12 Archived`, `13 Archived Notes`, `14 Archived Subscribed` (finished; 14 = you are a subscriber but neither owner nor reviewer) — not in **my overview** (use the **Archived** view), only in the embedded project tables (see 3.)
	13. `15 Others` (only in the **everyone** views: items you are not involved in)
3. The embedded base at the top of a project note shows the same sections for the project's direct children (i.e. it shows the project tasks that belong to you; other members see their own tasks there); its **my project subprojects** / **everyone project subprojects** views show the whole subtree grouped by sub-project, like **my projects**; finished items stay while their parent is open (a finished subtree collapses to its top item). It has no Archived view: finished children stay in the **my project overview** / **everyone project overview** tables, at the bottom under `12 Archived` (`13 Archived Notes` for notes), so a project keeps its history in view.

## Creating items

1. **Inside a project**: press **New** in its subtasks table, type `!name`, `,name`, or `name` (depending on type you want), Enter. The file lands beside the project with `parent` filled and the nine properties set, `owner` = you, `reviewer` = the project's owner.
2. **Without a parent** (a new top-level project, or a standalone task or note): press **New** in [[me.base]]; `owner` and `reviewer` = you.
3. **Hand an item to Claude**: create a subtask with `owner: claude`; you stay reviewer, and it shows in your `5 Delegated`. When a VNA run reaches its project, the item runs as soon as its `dependencies` are finished — with none, right away.

Whenever you want to insert the project template (roughly necessary for projects IMO): Press **Alt+P**.

## Personal task management

1. **Need something done by someone else, or waiting for someone?** Create a subtask owned by them (**New** in the project's subtasks table, then change `owner`; written like `owner`, can be someone outside this vault). You stay reviewer, and it shows in your `5 Delegated`. If an item of yours can't go on until then, add the subtask to its `dependencies`.
2. **Only need a project/task/note for later?** Set not-before to the date by when you want to see it properly. Until then it is in the later sections.
3. **How to use Claude:** have Claudian open and ask it for help with your projects. (To hand an item to a VNA run, see *Creating items* 3.)
4. **Finish** = `status: done` (or `cancelled` / `failed`). Needs a check? `review`: the reviewer checks and sets `done`, or clears the status with a comment to send it back. Should someone else check your own item, make them reviewer.

## Working together

1. **Sharing**: everyone sees everything — keep sensitive material out.
2. **Rule: Everything needs exactly one owner.** 
3. By default you should **probably only set yourself as the owner**; to get something done by someone else, create a subtask owned by them (you stay reviewer) and tell them. (Please do still capture someday-maybe ideas others would be involved in, but perhaps don't capture them as projects directly but rather as actionable-for-you task like "consider whether we should start project X".)

## How we run projects

We work backwards from the goal: purpose → spec → plan → build. The project template (**Alt+P**) has the sections for it:

1. `# Purpose / goal clarification / success criteria` — why the project exists and what success criteria are.
2. `# Spec` — the vision of how what will be built should look like: the parts, their interfaces, constraints. Before anything is built, **delete**: question every requirement (why is it needed?), drop what success does not need, be biased against adding. Then **simplify**: is there a more natural, simpler design?
3. **Plan subprojects and subtasks**: Create them with **New** in the subtasks table: tasks, and for big parts projects, which get a purpose and spec of their own. Then build.
4. `# Notes` — everything else.

For big projects where creating the spec or planning the subtasks are themselves difficult, you can also add `!create spec for {project}` subtasks where you can take notes, or even `,create spec ...` subprojects (and likewise for `!create plan ...`).

**Claude can run this pipeline for you** (the "VNA scaffold"), for goals too big for one claude session:

5. Tell Claude `load vna-spec on [[,name]]`: it asks its questions in one batch, then writes purpose and spec by the principles above. Correct the result: everything is built from it.
6. Then (perhaps in a new chat): `load vna-controller on [[,name]]`. Claude plans the project into children and works through them, each in a fresh Claude instance; children that do not depend on each other run at the same time. It also plans checkpoints where it gives you a summary and asks you for decisions: a checkpoint is a `!checkpoint …` task owned by you, in your `1 Inbox`: answer the `A:` lines in the file and set it `done`; the run goes on when you start the controller again.

## Folder structure

(This section is just for understanding, you don't access files through navigating folders, but through the bases (explained above).)

1. **`projects-tasks-notes/` — every project, task and note.** Items without a parent sit in its root (where **New** in [[me.base]] creates); a project with children gets a folder of the same name (without the `,`) holding them, e.g. `Vault tutorial exercise/`.
	1. `handoffs/` — Claude session-handoff notes.
	2. `archived/` — finished (`done` / `cancelled` / `failed`) items without a parent, a project with its folder; the nightly cleanup moves them here.
Less important:
2. `periodic-auto-summaries/` — generated daily/weekly/monthly/… summaries of what changed in the vault.
3. `other-files/` — scripts, automation config. also images and audio that don't clearly belong to a project.
4. `external-projects/` — mostly intended for code repositories. (not synced via syncthing. use github here instead.)
5. `shared_templates/` — the note templates (synced); `local_templates/` — your running copy (unsynced); `_local/` — your identity note `me.md` (unsynced).
6. `.claude/` — Claude configuration; `CLAUDE.md` and `settings.local.json` are yours, the rest is shared.
7. `vault-members/` — one empty file per vault member (`simon.md`, …), made by the setup; the links in `owner` / `reviewer` / `subscribers` point here.
