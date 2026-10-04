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
    loop:
        ready = collect(launch item), minus the items whose agents are still running
        ready is not empty and the checks allow it → spawn(all of ready), in one message
        nothing is running → stop, unless collect changed a file this pass (closed a project, handled an exception): then pass again
        wait for an agent to finish → afterRun(each finished item)

collect(item):    # first match; returns the leaves under item that can run now
    `exception`             → handle the exception (see afterRun), then match again
    not ready (States 3)    → nothing
    a task                  → [item]
    a project:
        setup(item) if it is hand-made, the first time you reach it
        read the children table (`--subtask-base-only`)
        a queue child is open   → collect(each open queue child), all together
        it has queue children other than `create spec …` / `create plan …` items → close(item); nothing
        else                    → [item]    # the project is executed as a whole

close(project): if a child is `review`: set the project `review`, and its `reviewer` to the user where it is `claude`
                else: set it `done`
```

## States

1. **Finished**: `review`, `done`, `failed`, `cancelled`. `review` asks a human to check something, and that holds nothing up. **Open**: everything else.
2. **Queue children** of a project: its task and project children. Notes are no part of the run.
3. **Ready**: `status` empty, the move is yours, `not_before` empty or past, and `blocked` = `-` in the children table (every dependency finished). The move is yours when `owner` is `claude`; the launch item's move is yours whatever its `owner`, and the `dependencies` and `not_before` it had when the user started you do not count. An item a human owns is that human's move: it waits, and holds up only what depends on it. So do `inbox` and `in-progress`. Hence the run goes on past a checkpoint wherever nothing depends on it, and a project stays open while a child is a human's. Where a queue child in `inbox` or `in-progress` looks as if it was meant for the run (a checkpoint never is), tell the user.

## setup

A project is hand-made if it is the launch project, or a child whose `reviewer` is not `claude`. Read it and create the spec task and the plan task that it needs and does not have (Formats 2); a finished one counts as had. It needs a spec task where no spec is written and writing one is worth a run. It needs a plan task where it needs decomposing, and also where it is open whether it does. The tasks need no body. Add the `![[subtasks.base]]` line where it is missing: without it the children table stays empty. Tell the user what you created.

## spawn

The item's filename picks the skill, as the process overview says.

By default, spawn a plain subagent: no `subagent_type`, no `model`. Where the item's `effort` property is set, pass its value as `subagent_type`: an agent type of that name exists for each effort level. Where the item's `model` property is set, pass its value as `model`. Both properties are columns of the children table. Spawn all ready items in one message: no dependency path runs between them, which is the planner's promise that they can run at the same time.

The prompt is exactly this template, because the skills have no reply instructions of their own:

```
Load the skill <skill> with the Skill tool and run it on: <vault-relative path>
You are a subagent: the user cannot answer you. Reply in one line — the state you left the item in, plus anything unusual. Everything else belongs in the files.
```

Whatever else an agent must know, above all what the user tells you during the run, goes into the item, under `# Notes`, not into the prompt.

## afterRun

The loop goes on when the agent left the item `done`, or when an executor left it `review`. It also goes on when a spec agent left its spec task with an empty `status`, depending on a new checkpoint with its questions: the spec task runs again once the user has set the checkpoint `done`, and what depends on the spec task waits till then.

Every other outcome needs exception handling: the item is `exception` (the agent threw an exception), or its state makes no sense. So does a run that you yourself see going really wrong. In these cases read `.claude/references/vna-exception-handling.md` and handle the case.

## The checks: checkUsage & checkOwnContext

Run both before you spawn.

1. Run `bash .claude/scripts/check-claude-usage.sh`. Spawn only while the 5-hour and the 7-day window both have headroom, enough to leave the user slack for interactive work.
2. Estimate your own context use. Beyond ~350k tokens, spawn nothing more.

Where a check fails: spawn nothing more, wait for the running agents and do their afterRun, then stop — or, for 2, do a relay-handoff with the `handoff` skill. All state is in the files, so the successor needs only the launch path and what you have collected for the wrap-up.

## Stop and wrap-up

Whenever you stop, tell the user what was done, what needs their check, what waits on whom and what is held up behind it, and what you or the agents found unusual. Take this from the one-line replies and the `# Result`s. If the run is unfinished, say what would run next. The run goes on when the user starts you on the launch item again.
