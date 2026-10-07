# Shared vault conventions

Imported into every member's personal `.claude/CLAUDE.md` by the line `@CLAUDE_shared.md`. Synced, identical for everyone, changed only by agreement; personal instructions belong in `CLAUDE.md`, which is never synced. Below, **you** = Claude, **the user** = the human whose session this is; their name is the `user` value in `_local/me.md` (per-device, never synced). Humans read `README.md` instead of this; you don't have to read README.

## Files and folders

1. All work lives in `projects-tasks-notes/`, one file per item. The filename prefix sets the type, nothing else does: `,` = project, `!` = task, no prefix = note.
2. Folder-structure rule: a project with children gets a folder named like it without the `,`, holding the project file and its children (recursively). Parentless items sit in the `projects-tasks-notes/` root. Also there: `handoffs/` (session-handoff notes, `handoff` skill) and `archived/` (finished parentless items, a project with its folder). Place new files by this rule; a nightly cleanup on the automation host fixes what is misplaced and does the archiving.
3. Filenames are unique across the vault (wikilinks resolve by basename). Rename and move through Obsidian (link-aware) so children's `parent` links survive; renaming changes the type.
4. Other folders: `periodic-auto-summaries/` (generated summaries of vault changes), `other-files/` (scripts, automation config, media, the VNA exceptions log), `shared_templates/` (Templater templates that fill the properties of hand-made notes; changed only by agreement), `vault-members/` (one empty file per vault member, named like their `user`, made by `setup-member`; next to it `<user>.base`, `me.base` as they see it, generated — `obsidian-bases` skill). Per-user, never synced, possibly absent on other machines: `_local/`, `local_templates/`, `.obsidian/`, `external-projects/` (the user's own code checkouts), and in `.claude/`: `CLAUDE.md`, `settings.local.json`, `skills/about-me/`. Everything else in `.claude/` is shared.

## Properties

5. Every file in `projects-tasks-notes/` carries these nine properties, in this order: `status`, `priority`, `parent`, `owner`, `reviewer`, `not_before`, `dependencies`, `due`, `subscribers`.
	1. `status`: empty (= active), `inbox` (captured or proposed, not yet triaged into active work), `in-progress`, `review` (the owner is finished; the reviewer checks, then sets `done`, or clears the status with a comment to send it back), `exception` (VNA only: a Claude run hit a problem; the controller handles it), `done`, `cancelled`, `failed`. Nothing else — section names such as Delegated or Awaiting Review are never statuses. `done` / `cancelled` / `failed` are terminal: the item counts as archived.
	2. `priority`: 1–10, 10 = most important; empty counts as 5. A ranking for humans, never an execution order.
	3. `parent`: quoted wikilink to the single parent, `parent: "[[,name]]"`; empty only at the top of a tree.
	4. `owner`: the one who does the item — a link to them, `owner: "[[simon]]"`, or plain `claude`. Every item has exactly one. `reviewer` (formerly `stakeholder`): the one person the item is for, who tracks and reviews it; empty = the owner; equal to the owner = the owner's own item. A person in these two or in `subscribers` is such a link, by first name, if they are a vault member (it resolves to their file in `vault-members/`) or likely to become one (it resolves once they join); anyone else is a plain name.
	5. `not_before`: date; the item is parked under Later until then.
	6. `dependencies`: list of wikilinks to items this one waits for; while any of them is unfinished (neither `review` nor terminal), the item is parked under Blocked.
	7. `due`: date; the bases sort the item as if its `priority` were 1 higher on that day and 2 higher once it has passed. No other effect.
	8. `subscribers`: list of people who want to see the item without being responsible for it.
	9. Files created by a VNA run also carry `model` and `effort` (for the subagent that runs the item; usually empty).

## What the properties do for members

6. Members watch `me.base` (vault-wide) and the `![[subtasks.base]]` embedded in each project (its direct children). Their *my …* views list, for a member M, the items where M is `owner`, `reviewer` or a subscriber; the *overview* views group rows into sections: `1 Inbox`, `2 In Progress` (M is owner, and the status is `inbox` / `in-progress`) — `3 Review` (status `review`, M the reviewer, M's own items included) — `4 Your Tasks` (M's other open items) — `5 Delegated` (open items where M is reviewer but not owner, Claude's included) — `6 Awaiting Review` (M's `review` items that someone else reviews) — `7 Subscribed` (M only a subscriber) — `8 Notes` — `9 Blocked` (an unfinished item in `dependencies`) — `10 Later Tasks`, `11 Later Notes` (`not_before` in the future) — `12 Archived`, `13 Archived Notes` (terminal status) — `14 Archived Subscribed` (terminal, M a subscriber but neither owner nor reviewer) — `15 Others` (only in the *everyone* views: M not involved). First match wins, in the order 14, 12–13, 1–3, 6, 8–11, 4, 5, 7, 15.

## Creating and finishing items

7. Write the full property header when creating new files. `owner` = the user unless they say otherwise; never make someone else owner uninstructed. `reviewer` = the owner of the parent project, or the owner where there is no parent. To get something done by someone else (a member, an external person, Claude), create a subtask owned by them; the user stays reviewer. Don't set any field to `claude` unless instructed (the VNA skills do, for their children).
8. A `,` project's body: the line `![[subtasks.base]]` at the very top — without it the children are invisible — then `# Purpose / goal clarification / success criteria`, `# Spec`, `# Notes`. Ideas that have no file yet are plain lines under `## Possible next steps` in `# Notes`.
9. When you finish a task or goal: `status: done` if you are confident the work needs no check, else `review`: the reviewer looks (if the reviewer is `claude`, make the user the reviewer).

## Tools

10. Read `,` project files with `python3 .claude/scripts/read_obsidian.py "<note>"`, not `Read`/`cat`: a project's state lives in its children, which `Read` shows only as the line `![[subtasks.base]]` — the script renders them as a table (and expands other `![[embeds]]`). `--subtask-base-only` prints just that table.
11. Multi-step goals run through the VNA orchestration system: the `vna-spec` skill writes the project's purpose and spec with the user, then the `vna-controller` skill, loaded on the project file, runs it: every task or project under it with `owner: claude`, once its `dependencies` are finished. An item a human owns is that human's move; a checkpoint (`!checkpoint …`) is owned by the user, in `inbox` once its questions are written, and the user answers it and sets `done`.
12. A member's machine is set up by the `setup-member` skill ("complete the setup"); re-run it after a shared template changes.
13. `bash .claude/scripts/check-claude-usage.sh` prints Claude plan usage: 5-hour / 7-day windows, per-model limits, extra credits, with reset times. Only run it when asked.
14. Discord: `python3 other-files/discord/discord.py post <#channel|thread id|@member> "text"` posts as the team's bot from any member's session (`@member`, a vault name, = a DM; queued as a file in `other-files/discord/outbox/`, carried out by the automation host within seconds; the command waits for and prints the receipt from `outbox.log`). `channels` and `read` (list channels and threads, read a channel's last messages) work the same way; `--help` says the rest.

## Sharing, sync and git

15. Several people have the same files open through Syncthing. Keep edits small and targeted; never rewrite wholesale a file you did not just create. Everyone reads everything: no secrets or sensitive material in the vault. A `*.sync-conflict-*` file is Syncthing's copy of a collision (hidden by the bases): merge it, then delete it.
16. Never commit in this vault. Its git repository exists on the automation host only (nightly snapshot, summaries, cleanup), and that host's job commits. Repositories under `external-projects/` are the user's own and unaffected.

## Principles

(You don't need to follow those unless instructed, but understand the spirit of the importance of simplicity and keeping our goal in mind:)
17. We work backwards from our goals. We first clarify our goal and then a more detailed vision ("spec") of a project before starting with implementation.
18. We need to question our requirements and think what is really necessary. Drill down to base requirements by asking why requirements are necessary. Try to delete requirements: Is it really necessary? Are there creative ways to loosen it? Perhaps try to find the core of what we really need.
19. We want to have only necessary parts. We try to delete non-essential parts from our spec before we start implementing it. We have a bias against adding stuff.
20. Simplicity is crucial. We try to find ways things could work in a very natural, clean, and simple way. We want to check whether we can simplify our spec further. Are there different approaches that might be simpler?
21. Writing concisely (both in the chat and in documents), and especially not writing unnecessary text or items, is very important too. We do not want to clutter context. Prioritize what is important and cut the rest. (Or if instructed externalize the rest into a detailed reference note where it doesn't clutter context of most agents or people).

## Other notes

If you see processes that don't make perfect sense, or contradictions between what skills say and the way the vault is set up or so, or something in a skill or so is just very confusingly stated, please leave a "system bug report" to the vault owner by documenting it as an inbox note with owner=<vault-owner>. Likewise leave "system improvement idea" for what you think could be significantly optimized.
If the user is confused about something and the system (a skill, doc or process) could plausibly be made clearer or better, suggest you could file a system bug report or improvement idea this way (add them as subscriber).
