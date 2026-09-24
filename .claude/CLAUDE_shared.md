# Shared vault conventions

Imported into every member's personal `.claude/CLAUDE.md` by the line `@CLAUDE_shared.md`. Synced, identical for everyone, changed only by agreement; personal instructions belong in `CLAUDE.md`, which is never synced. Below, **you** = Claude, **the user** = the human whose session this is; their name is the `user` value in `_local/me.md` (per-device, never synced). Humans read `README.md` instead of this; you don't have to read README.

## Files and folders

1. All work lives in `projects-tasks-notes/`, one file per item. The filename prefix sets the type, nothing else does: `,` = project, `!` = task, no prefix = note.
2. Folder-structure rule: a project with children gets a folder named like it without the `,`, holding the project file and its children (recursively). Parentless projects sit in the `projects-tasks-notes/` root, parentless tasks and notes in `projects-tasks-notes/quick-tasks-and-notes/`. Also there: `handoffs/` (session-handoff notes, `handoff` skill) and `archived/` (finished trees). Place new files by this rule; a nightly cleanup on the automation host fixes what is misplaced.
3. Filenames are unique across the vault (wikilinks resolve by basename). Rename and move through Obsidian (link-aware) so children's `parent` links survive; renaming changes the type.
4. Other folders: `periodic-auto-summaries/` (generated summaries of vault changes), `other-files/` (scripts, automation config, media, the VNA exceptions log), `shared_templates/` (Templater templates that fill the properties of hand-made notes; changed only by agreement). Per-user, never synced, possibly absent on other machines: `_local/`, `local_templates/`, `.obsidian/`, `external-projects/` (the user's own code checkouts), and in `.claude/`: `CLAUDE.md`, `settings.local.json`, `skills/about-me/`. Everything else in `.claude/` is shared.

## Properties

5. Every file in `projects-tasks-notes/` carries these seven properties, in this order: `status`, `priority`, `parent`, `owner`, `next_action_by`, `not_before`, `subscribers`.
	1. `status`: empty (= active), `inbox` (captured or proposed, not yet triaged into active work), `in-progress`, `review`, `on-hold`, `done`, `cancelled`, `failed`. Nothing else — section names such as Wait or Delegated are never statuses. `done` / `cancelled` / `failed` are terminal: the item counts as archived.
	2. `priority`: 1–10, 10 = most important; empty counts as 5. A ranking for humans, never an execution order.
	3. `parent`: quoted wikilink to the single parent, `parent: "[[,name]]"`; empty only at the top of a tree.
	4. `owner`: the one person responsible — a lowercase first name (`simon`, `matilda`, …) or `claude`. Every item has exactly one. `next_action_by`: whose move it is now; empty = the owner's; may name someone outside the vault. Handing an item back = clearing it.
	5. `not_before`: date; the item is parked under Later until then.
	6. `subscribers`: list of people who want to see the item without being responsible for it.
	7. Files created by a VNA run also carry `order` (queue position), `model` and `effort` (for the subagent that runs the item; usually empty).

## What the properties do for members

6. Members watch `me.base` (vault-wide) and the `![[subtasks.base]]` embedded in each project (its direct children). Their *my …* views list, for a member M, the items where M is `owner`, `next_action_by`, a subscriber, or owner of the parent; the *overview* views group rows into sections: `1 Inbox`, `2 In Progress`, `3 Review` (M is owner or next actor, and the status is `inbox`, `in-progress`, `review` / `on-hold`) — `4 Your Tasks` (M's move) — `5 Claude` (VNA-scaffold items) — `6 Wait` (another person's move) — `7 Delegated` (someone else's item under M's project) — `8 Subscribed` — `9 Notes` — `10 Later Tasks`, `11 Later Notes` (`not_before` in the future) — `12 Archived`, `13 Archived Notes` (terminal status). First match wins, in the order 12–13, 1–3, 9–11, 4, 5, 7, 8, 6.

## Creating and finishing items

7. Write the full property header when creating new files. `owner` = the user unless they say otherwise; never make someone else owner uninstructed, give them the move with `next_action_by` instead. Don't set any field to `claude` unless instructed (the VNA skills do, for their children). Set `next_action_by: <person>` only when a human must act.
8. A `,` project's body: the line `![[subtasks.base]]` at the very top — without it the children are invisible — then `# Purpose / goal clarification / success criteria`, `# Spec`, `# Notes`. Ideas that have no file yet are plain lines under `## Possible next steps` in `# Notes`.
9. When you finish a task or goal: `status: done` if you are confident the work needs no check, else `review` with `next_action_by` = the person who should look.

## Tools

10. Read `,` project files with `python3 .claude/scripts/read_obsidian.py "<note>"`, not `Read`/`cat`: a project's state lives in its children, which `Read` shows only as the line `![[subtasks.base]]` — the script renders them as a table (and expands other `![[embeds]]`). `--subtask-base-only` prints just that table.
11. Multi-step goals run through the VNA orchestration system: the `vna-spec` skill writes the project's purpose and spec with the user, then the `vna-controller` skill, loaded on the project file, runs it.
12. A member's machine is set up by the `setup-member` skill ("complete the setup"); re-run it after a shared template changes.
13. `bash .claude/scripts/check-claude-usage.sh` prints Claude plan usage: 5-hour / 7-day windows, per-model limits, extra credits, with reset times. Only run it when asked.
14. Discord: `python3 other-files/discord/discord.py post <#channel|thread id> "text"` posts as the team's bot from any member's session (queued as a file in `other-files/discord/outbox/`, posted by the automation host within seconds; the command waits for and prints the receipt from `outbox.log`). `channels` and `read` (list channels and threads, read a channel's last messages) need the bot token in `~/.claude/channels/discord/.env`, ask simon; `--help` says the rest.

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

If you see processes that don't make perfect sense, or contradictions between what skills say and the way the vault is set up or so, or something in a skill or so is just very confusingly stated, please leave a "system bug report" to the vault owner by documenting it as an inbox note with owner=<vault-owner> (in quick-tasks-and-notes). Likewise leave "system improvement idea" for what you think could be significantly optimized.
