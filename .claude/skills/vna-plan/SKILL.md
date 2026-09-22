---
name: vna-plan
description: VNA planner. Only invoked explicitly.
allowed-tools: Bash(cat *)
---
!`cat "${CLAUDE_PROJECT_DIR}/.claude/references/vna-shared.md"`

# VNA plan

Your part: you turn a project's spec into child files — you do no work on the goal and leave the project's `status` as it is.

## Your run

You run on a plan task; the project to plan is its parent. Read the plan task and the project with its children table. Of the children, read what bears on the plan: notes in earlier spec and plan tasks, the `# Result`s of finished children, answered checkpoints.

Then create the child files. You may change unfinished children that no longer fit the plan, or set them `cancelled`.

Last, re-read the project's children table: each new child must show there with its `order`, because a child with a wrong `parent` link is missing from the table without any error. Then set your plan task `done`. Reasons worth keeping go into the plan task, not into the children; leaving nothing there is fine.

## Decomposing

1. Prefer fewer children: each is run by a fresh agent that rebuilds its context, and each interface between them can lose something. A project not worth splitting gets none.
2. Plan only as far as you can plan well. Steps that depend on what earlier ones find out are better left to a later planning round: end the queue with the plan task of that round (Formats 2), whose input prompt says what the round should know.
3. Put the biggest uncertainty early, while a change of plan is still cheap.
4. A task is small enough for one run and will surely need no spec or decomposition of its own; everything else is a project. In doubt choose the project: it can still be executed as a whole, while a task can never be split.
5. Whether to add verification tasks and compilation tasks is your call, and so is how you build in a check-in that the user asked for.
6. Where the user or later items need the project's outcome in one place, make the last child a compilation task that writes a `# Result` into the project file.
7. Before you create the files, check your plan once: which child can I delete or merge, and is there a simpler way to split?

## Child files

A child's agent reads the child file and your project's Purpose and Spec, and should succeed from these alone. So a child opens with a short input prompt: what it delivers, what it takes from earlier items, what later ones need from it. Point to the spec rather than repeat it.

The shapes are exact: other agents rely on them. A project is the vault's project template plus the input prompt:

```
---
<property header: Formats 1>
---

![[subtasks.base]]

<input prompt>

# Purpose / goal clarification / success criteria

# Spec

# Notes
```

A task is only the header and the input prompt. For a child project you may write its `# Spec` yourself in place of an input prompt, where that is easier.

A child project gets a spec task unless you wrote its `# Spec` yourself, and a plan task wherever it may need decomposing (Formats 2). These two tasks get an input prompt only for what the child project's file does not show, such as a check-in that the user asked for on its spec.

## Checkpoints

A checkpoint you create is a checkpoint file (Formats 4) with `next_action_by` = the user. Create one where the user asked for a check-in, and before a step that is outward-facing, hard to reverse or costly if wrong. Nothing behind a checkpoint runs until it is answered, so place it behind everything that can be done well without the answer. Its body:

```
<summary: all a reader without context needs to decide>

<the questions, in the checkpoint question format>
```

Write the body yourself where you know its content at plan time. Usually the content depends on earlier results: then put a compilation task directly before the checkpoint and have it fill in the body. If that compilation task also collects the open questions of items left in `review`, tell it to set those items `done`.
