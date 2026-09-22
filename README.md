# obsidian-team-vault — project management with Obsidian and Claude Code, alone or as a team

A vault for running projects: every project, task and note is one file with seven properties; [Obsidian Bases](https://help.obsidian.md/bases) turn those into per-person dashboards; [Claude Code](https://claude.com/claude-code) works inside the vault through the [Claudian](https://obsidian.md/plugins?id=realclaudian) plugin — including the "VNA" scaffold, which writes a project's spec, plans it into children and runs them one by one in fresh subagents. Optionally a team shares the vault through [Syncthing](https://syncthing.net), with one always-on machine running nightly summaries and cleanup. It is the live vault of PauseAI Global's infrastructure team with the content removed.

## Setup on one machine (~10 minutes)

1. **Get the files**: `git clone --depth 1 https://github.com/SimonSkade1/obsidian-team-vault.git` and delete the `.git` folder (`rm -rf obsidian-team-vault/.git`), or **Code → Download ZIP** and unpack it as `obsidian-team-vault`. A vault is not a git checkout: only a team's automation host keeps a repository (its own), and step 4 refuses to run next to one.
2. **Install** [Obsidian](https://obsidian.md/download) (a current version — the views are Bases, tested on 1.13.7), [Claude Code](https://claude.com/claude-code) (`curl -fsSL https://claude.ai/install.sh | bash`; Windows: `irm https://claude.ai/install.ps1 | iex`) and run `claude` once to log in with your own subscription; have Python 3.8+ (`python3 --version`; Windows: `py -3 --version`). OS details: [`INSTALL_AND_SETUP.md`](INSTALL_AND_SETUP.md) steps 3, 4 and 6.
3. **Open the folder as a vault** in Obsidian → **Turn on community plugins** → **Browse** → `Claudian` → **Install** → **Enable**. Then **Settings → General → Command line interface** → on: that registers the `obsidian` command Claude uses to reach the running app (to finish step 4, and later to move and rename notes without breaking links).
4. **Click the robot icon** (Claudian) and type `complete the setup`. It asks for your first name (lowercase — the string used in `owner` and `next_action_by`), then installs Templater, Hidden Folders Access and Outliner, your checked copy of the note templates with the **Alt+P** hotkey, `_local/me.md` (your identity, read by every view) and your personal `.claude/CLAUDE.md`. Approve the commands it asks to run.
5. **Read the rest of this file** — below the line is the vault's own README, as members see it (5 minutes) — then do the five-minute exercise in `projects-tasks-notes/Vault tutorial exercise/`.

## Team use (optional)

Several people, one folder, no server software: [`TEAM_SETUP.md`](TEAM_SETUP.md) — Syncthing hub-and-spoke through one always-on machine, which also runs the nightly git snapshot, summaries and cleanup; each member's onboarding is [`INSTALL_AND_SETUP.md`](INSTALL_AND_SETUP.md).

## Where things are

1. `*.base` — the views: `me.base` (your overview), `subtasks.base` (embedded in every project), `major_projects.base`, `recent.base`; [`shared_templates/`](shared_templates) — the note templates; [`projects-tasks-notes/`](projects-tasks-notes) — all items, empty but for the tutorial.
2. [`.claude/`](.claude) — Claude's shared instructions (`CLAUDE_shared.md`, imported by each member's own `CLAUDE.md`), skills (`vna-*`, `setup-member`, `handoff`, `obsidian-bases`, …), agent definitions and scripts.
3. [`other-files/`](other-files) — the automation host's scripts, config and its setup doc `VPS_SETUP_INFO.md`.
4. Exported from the live vault by a script (not included: it holds the strings it redacts), so the docs name that team's people and machines — `TEAM_SETUP.md` lists what to replace. `[[wikilinks]]` resolve in Obsidian, not on GitHub.

---

# How to use this vault

How the vault is used day to day. Machine not set up yet? First the setup steps above (one machine) or [[INSTALL_AND_SETUP]] (joining a team's vault). Read this file (5 minutes), then do the five-minute exercise in [[,Vault tutorial exercise]].

## Files

1. **The name sets the type**: `,name` = project, `!name` = task, no prefix = note. Renaming changes the type.
2. **Seven properties**, written by the **New** button when you create a file (see *Creating items*):
	1. `status` — empty = active; or `in-progress`, `inbox`, `review`, `on-hold`, `done`, `cancelled`, `failed`. Nothing else.
	2. `priority` — 1–10, **10 = most important**, empty counts as 5; sorts within a section, highest first; a project also counts as the highest priority among the items below it that are in your sections 1–4 (Inbox … Your Tasks), so it depends on who is looking.
	3. `parent` — one link to its project, `"[[,name]]"`; empty = top of a tree.
	4. `owner` — who is responsible. `next_action_by` — whose move it is now; empty = the owner's. Lowercase first names, `claude` for the bot.
	5. `not_before` — a date; the item sits under `10 Later Tasks` (a note: `11 Later Notes`) until then.
	6. `subscribers` — people who want to see it without owning it.

## Folder structure

1. **`projects-tasks-notes/` — every project, task and note.** Parentless projects sit in its root; a project with children gets a folder of the same name (without the `,`) holding them, e.g. `Vault tutorial exercise/`.
	1. `quick-tasks-and-notes/` — tasks and notes without a parent (where **New** in [[me.base]] creates).
	2. `handoffs/` — Claude session-handoff notes.
	3. `archived/` — completed/cancelled/failed projects.
Less important:
2. `periodic-auto-summaries/` — generated daily/weekly/monthly/… summaries of what changed in the vault.
3. `other-files/` — scripts, automation config. also images and audio that don't clearly belong to a project.
4. `external-projects/` — mostly intended for code repositories. (not synced via syncthing. use github here instead.)
5. `shared_templates/` — the note templates (synced); `local_templates/` — your running copy (unsynced); `_local/` — your identity note `me.md` (unsynced).
6. `.claude/` — Claude configuration; `CLAUDE.md` and `settings.local.json` are yours, the rest is shared.

## Your project and task overview: [[me.base]]

1. **Views**: **my overview** = what concerns you, by section (minus your own items under your own projects — those you see in the project's table); **my projects** = the same items including those, grouped by project (`<effective priority> <project> › <sub-project>:`, the project itself is the first row of its group, `no project:` first); **everyone overview** / **everyone projects** = the same for everyone's items; **Archived** = finished (`done`, `cancelled`, `failed`), **Unassigned** = no owner (shouldn't exist but fallback in case it does).
2. **Sections**: `1 Inbox`, `2 In Progress`, `3 Review` (status = review) — `4 Your Tasks` (TODO) — `5 Claude` (VNA-scaffold task) — `6 Wait` (someone else's move) — `7 Delegated` (someone else's item under your project) — `8 Subscribed` (you or someone added you in the subscriber column) — `9 Notes` — `10 Later Tasks` (`not_before` in the future) — `11 Later Notes`.
3. The embedded base at the top of a project note shows the same sections for the project's direct children (i.e. it shows the project tasks that belong to you; other members see their own tasks there). It has no Archived view: finished children stay in the table, at the bottom under `12 Archived` (`13 Archived Notes` for notes), so a project keeps its history in view.

## Creating items

1. **Inside a project**: press **New** in its subtasks table, type `!name` or `,name` as the name, Enter. The file lands beside the project with `parent` filled and the seven properties set, `owner` = you. A `,name` needs its sections: open it and press **Alt+P** with the cursor at the end of the file — that adds the standard sections and its own table.
2. **Small tasks or independent notes**: press **New** in [[me.base]] (lands in `quick-tasks-and-notes/`)
3. **New major project**: press **New** in [[major_projects.base]], then **Alt+P** in the new file as in 1.
4. **A task that became a project**: rename it with the `,` prefix, then press **Alt+P** with the cursor at the end of the file — that adds the project sections and any missing properties.
5. **A file made another way** (Ctrl+N, a clicked link to a note that does not exist yet) has no properties: run the command **Templater: Insert properties** (Ctrl+P, type "insert prop") — it adds the seven properties with `owner` = you.

## Personal task management

1. **Blocked on a project or task because you are waiting for someone?** = set `next_action_by` to that person. This can also be a person who isn't part of this synced obsidian system. The task then shows in the `6 Wait` section (of [[me.base]], or of the project's table if it is your own item under your own project). Make sure you check that section (as well as all sections until `9 Notes`) regularly.
2. **Only need a project/task/note for later?** Set not-before to the date by when you want to see it properly. Until then it is in the later sections.
3. **How to use Claude:** have Claudian open and ask it for help with your projects. You **don't** need to set any property such as `next_action_by: claude`; the `5 Claude` section only matters for the VNA scaffold, which plans and queues its own subtasks (see *How we run projects* below).

## Working together

1. **Finish** = `status: done` (or `cancelled` / `failed`). Needs a check? `review` plus `next_action_by` = who should look.
2. **Sharing**: everyone sees everything — keep sensitive material out. Simultaneous edits leave a `…sync-conflict-…` copy the bases hide: search for `sync-conflict` occasionally, merge, delete. No `: ? " * < > |` in names; keep paths short.
3. **Rule: Everything needs exactly one owner.** 
4. By default you should **probably only set yourself as the owner**, or if not then communicate to the person that you put them in as owner. (Please do still capture someday-maybe ideas others would be involved in, but perhaps don't capture them as projects directly but rather as actionable-for-you task like "consider whether we should start project X".)

## How we run projects

We work backwards from the goal: purpose → spec → plan → build. The project template (**Alt+P**) has the sections for it:

1. `# Purpose / goal clarification / success criteria` — why the project exists and what success criteria are.
2. `# Spec` — the vision of how what will be built should look like: the parts, their interfaces, constraints. Before anything is built, **delete**: question every requirement (why is it needed?), drop what success does not need, be biased against adding. Then **simplify**: is there a more natural, simpler design?
3. **Plan subprojects and subtasks**: Create them with **New** in the subtasks table: tasks, and for big parts projects, which get a purpose and spec of their own. Then build.
4. `# Notes` — everything else.

For big projects where creating the spec or planning the subtasks are themselves difficult, you can also add `!create spec for {project}` subtasks where you can take notes, or even `,create spec ...` subprojects (and likewise for `!create plan ...`).

**Claude can run this pipeline for you** (the "VNA scaffold"), for goals too big for one chat:

5. Tell Claude `load vna-spec on [[,name]]`: it asks its questions in one batch, then writes purpose and spec by the principles above. Correct the result: everything is built from it.
6. Then (perhaps in a new chat): `load vna-controller on [[,name]]`. Claude plans the project into children and works through them one by one, each in a fresh Claude instance. Where it needs you it stops and says so: answer in the item, clear `next_action_by`, tell it to go on. All state is in the files, so a run that stopped early continues when you start it again.

