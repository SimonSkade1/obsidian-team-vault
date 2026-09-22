---
status:
priority: 1
parent:
owner: simon
next_action_by:
not_before: 2099-01-01
subscribers:
---

![[subtasks.base]]

# Purpose / goal clarification / success criteria

A five-minute exercise for learning the vault: you build one small fictional project of your own, Claudian grades it, and it stays here as `done`. Read [[README]] first. Claude made this note and keeps it; `not_before: 2099` keeps it out of everyone's queue.

# Spec

## Steps

1. **Make your tutorial project.** Press **New** in the table at the top of this note → type `,<yourname> tutorial PauseAI info stall` → **Enter**, then open it, click at the end of the note and press **Alt+P**. It now has the seven properties (`owner` = you, `parent` = this project), its own subtasks table at the top and the three standard sections below it — it is the fictional stall project the questions are about. (No `owner`, or everything in `me.base` under `0 ⚠ create _local/me.md`? Your setup is incomplete — finish [[INSTALL_AND_SETUP]] step 7 and start over.)
2. **Get the questions.** With your tutorial project open, type in the Claudian pane: `copy the questions from [[,Vault tutorial exercise]] into this note`. The `## Questions` from this note appear under its `# Spec`.
3. **Answer them** — inside your tutorial project only. The answers are files and their properties, not text: create every item with **New** in your tutorial project's subtasks table and name it with the right prefix. Start every name with your own name (`!anna book the stall`): file names must be unique in the whole vault, and your colleagues do this exercise too. Watch `me.base` (view **Mine**) as you go — each item lands in the section its properties put it in.
4. **Get graded.** Same note open, in Claudian: `grade this tutorial project against the answer key in [[,Vault tutorial exercise]]`. Fix what it flags if you like.
5. **Finish.** Set `status: done` on your tutorial project and every open item in it — by hand, or tell Claudian: `mark this tutorial project and everything in it done`. They vanish from [[me.base]]'s **Mine** and **All**, and drop to the bottom of the table at the top of this note under `12 Archived` (`13 Archived Notes` for notes), next to everyone else's. Leave them there.

## Questions

Kim is a fictional PauseAI volunteer without access to this vault

1. Kim asked you to run a PauseAI info stall at a street fair next month — that is this project. Give it three tasks: book the stall (you will do it), draft the flyer text (you plan to write it together with Claude), recruit volunteers (Kim offered to do that one).
2. Bookings only open in two weeks — keep the booking task out of your way until then. The flyer is the most urgent item: priority 7.
3. Kim sent the fair's details: organiser Sam Lee, stall fee 40 €, setup from 8:00. Keep them where whoever works on the stall will find them.
4. The organiser calls: no flyers allowed, only conversations. Record that the flyer task is off.

# Notes

## Answer key

For Claude when grading (members: peek if stuck). Read the tutorial project with `python3 .claude/scripts/read_obsidian.py "<note>"` (its table lists the children), check the points below, and reply in chat with one numbered line per question: what is right, what is off, and the exact fix. Do not edit the member's files unless asked. Names may differ; structure and properties are what count. Also check the tutorial project itself: `parent` = `[[,Vault tutorial exercise]]`, `owner` = the member, every file with all seven properties and `parent` a quoted wikilink.

1. Three `!` files (tasks) whose `parent` is the tutorial project. Booking task: `owner` = the member, `next_action_by` empty (→ `4 Your Tasks`). Flyer task: `owner` = the member, `next_action_by` empty (→ `4 Your Tasks`): planning to do something with Claude changes no property, you just ask Claudian when you get to it ([[README]], *Personal task management* 3). `next_action_by: claude` (→ `5 Claude`) is not wrong, only unnecessary: say so, but do not count it against them. Volunteers task: `owner` = the member, `next_action_by: kim` (→ `6 Wait`: the member's item, Kim's move). `owner: kim` is wrong: Kim is not in the vault, and by default you stay owner anyway ([[README]], *Working together* 4); it would land under `7 Delegated`.
2. Booking task: `not_before` = a date about two weeks from today (→ `10 Later Tasks` until then). Flyer task: `priority: 7` (10 = most important).
3. Either is fine: a line under the project's `# Notes` (slightly better for three details like these — note files are for longer material, e.g. research done with Claude) or a file with no prefix (a note), child of the tutorial project, with the details in its body (→ `9 Notes`). A `!` file is wrong: it is information, nothing to do.
4. Flyer task: `status: cancelled` — not `done` (it was not done) and not deleted (the record stays). It disappears from [[me.base]] and drops to `12 Archived` at the bottom of your project's table.
5. Slips worth naming when you see them: a prefix missing or followed by a space; `parent` typed by hand without quotes and brackets; a name that already exists in the vault; items created with **New** in `me.base` (they land parentless in `quick-tasks-and-notes/`) instead of in the project's table.

On `copy the questions …`: paste the `## Questions` section from this note's `# Spec` verbatim — heading included, this answer key excluded — at the end of the tutorial project's `# Spec` section.
On `mark … everything in it done`: set `status: done` on the tutorial project and on every descendant whose status is not already terminal (leave `cancelled` as it is). Never delete tutorial files.
