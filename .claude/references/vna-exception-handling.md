# Handling a VNA exception

Read the item's `# Exception` or `# Result` and little else.

Whatever you choose, the item must end up no longer stuck. Leave it in one of two states: open again, which means its `status` is cleared (clear it also where you put something in front of the item); or `cancelled`. Otherwise the loop lands here again.

## Options

These are options to weigh, not a procedure. Take the smallest that suffices. Where the item will run again, the next agent has to learn the outcome: write what you decided, what the user answered in chat, or which checkpoint holds their answers, as `## Handling` under the item's `# Exception`.

1. **Decide it.** Do this when the answer follows from what you know, or when the choice is clearly within the project's purpose. Fix the input prompt or the spec where they caused the problem; the item then runs again in place.
2. **Put a task in front of it.** Do this when one more run can supply what is missing: create a sibling task that takes over the item's `dependencies`, and put the new task into the item's `dependencies`.
3. **Too big for one run.** Give a project that is too big a plan task. Set a task that is too big `cancelled`, and replace it with a new project that has the same input prompt and a plan task.
4. **Re-plan the parent.** Do this when the approach is wrong, or when a retry needs a new framing: create a further plan task for the parent, and make the items that the re-planning affects depend on it. Where the files do not show why you called for this planning round, say it in the plan task's input prompt.
5. **Ask the user.** Do this when the decision is really theirs, when the item needs a step only they can take, or when this is the item's second exception, which shows that your first handling did not hold. Ask in chat when the user is there. Otherwise put a checkpoint in front of the item, as 2 puts a task: a checkpoint file (Formats 4) whose body links the item and repeats the questions from its `# Exception`.
6. **Cancel it.** Do this when the item turns out to be unnecessary.
7. **Stop the run.** When agents fail repeatedly, or the state of the files makes no sense, stop and tell the user.

## Log

Once the handling is decided, append one line to `other-files/VNA-exceptions-log.md` with `>>`, without reading the log:

```
YYYY-MM-DD · [[item]] · what was wrong · how it was handled
```
