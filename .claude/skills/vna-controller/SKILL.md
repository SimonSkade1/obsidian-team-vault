---
name: vna-controller
description: VNA controller. Only invoked explicitly.
allowed-tools: Bash(cat *)
---
!`cat "${CLAUDE_PROJECT_DIR}/.claude/references/vna-shared.md"`

# VNA controller

Your part: you are the only orchestrator; every other agent does one run on one file. The user starts you on a launch item: a project, or a single task. Your context has to last a long run, so leave all work on the items to the subagents and read little: read children tables and `# Result`s, and read a file's body only where `setup` or an exception needs it.

```
main:
    while the launch item is unfinished: run(launch item)
    stop

run(item):    # first match
    a human's move          → stop
    `on-hold`               → handle the exception (see afterRun)
    a checkpoint file       → set it `done`    # Formats 4: a human answered and handed it back
    a task                  → leaf(item)
    a project:
        setup(item) if it is hand-made
        loop: read the children table (`--subtask-base-only`)
              no queue child is unfinished → end loop
              run(the unfinished queue child with the lowest `order`)
        it has queue children other than `create spec …` / `create plan …` items → close(item)
        else → leaf(item)    # the project is executed as a whole

leaf(item):     spawn(item); afterRun(item); checkUsage & checkOwnContext
close(project): if a child is still in `review`: set the project `review` with `next_action_by` = the user
                else: set it `done`
```

## States

1. **Unfinished**: `status` empty, `in-progress` or `on-hold`. **Finished**: `review`, `done`, `failed`, `cancelled`. `review` counts as finished: it asks a human to check something, and that does not block the queue.
2. **Queue children** of a project: its children that have an `order` and are not `inbox`. Where a child that is not a queue child looks as if it was meant for the queue, tell the user.
3. **A human's move** (a checkpoint): an unfinished item whose `next_action_by` names a human, or whose `not_before` lies in the future. In the queue, an empty `next_action_by` means that the move is yours, whoever the `owner` is.

## setup

A project is hand-made if it is the launch project, or a child whose `owner` is not `claude`. Read it and create the spec task and the plan task that it needs and does not have yet (Formats 2). It needs a spec task where no spec is written and writing one is worth a run. It needs a plan task where it needs decomposing, and also where it is open whether it does. The tasks need no body. Add the `![[subtasks.base]]` line where it is missing: without it the children table stays empty. Tell the user what you created.

## spawn

The item's filename picks the skill, as the process overview says.

By default, spawn a plain subagent: no `subagent_type`, no `model`. Where the item's `effort` property is set, pass its value as `subagent_type`: an agent type of that name exists for each effort level. Where the item's `model` property is set, pass its value as `model`. Both properties are columns of the children table. Run one agent at a time, because later items build on earlier ones.

The prompt is exactly this template, because the skills have no reply instructions of their own:

```
Load the skill <skill> with the Skill tool and run it on: <vault-relative path>
You are a subagent: the user cannot answer you. Reply in one line — the state you left the item in, plus anything unusual. Everything else belongs in the files.
```

Whatever else an agent must know, above all what the user tells you during the run, goes into the item, under `# Notes`, not into the prompt.

## afterRun

The loop goes on when the agent left the item `done`, or when an executor left it `review`. It also goes on when a spec agent left its spec task unfinished, with a human in `next_action_by`: the spec task is now a checkpoint, and the next pass of the loop stops there.

Every other outcome needs exception handling: the item is `on-hold` (the agent threw an exception), or its state makes no sense. So does a run that you yourself see going really wrong. In these cases read `.claude/references/vna-exception-handling.md` and handle the case.

## checkUsage & checkOwnContext

1. Run `bash .claude/scripts/check-claude-usage.sh`. Go on only while the 5-hour and the 7-day window both have headroom, enough to leave the user slack for interactive work; otherwise stop.
2. Estimate your own context use. Beyond ~350k tokens, do a relay-handoff with the `handoff` skill. All state is in the files, so the successor needs only the launch path and what you have collected for the wrap-up.

## Stop and wrap-up

Whenever you stop, tell the user what was done, what needs their check, what waits on whom, and what you or the agents found unusual. Take this from the one-line replies and the `# Result`s. If the run is unfinished, say what would run next. The run goes on when the user starts you on the launch item again.
