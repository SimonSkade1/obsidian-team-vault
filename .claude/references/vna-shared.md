# VNA — the process

VNA works through a goal that is too big for one agent run. (VNA = von Neumann Architecture, which inspired the original version.) The goal is a tree of ordinary vault files: projects and tasks; a task is always a leaf. A controller takes the unfinished child with the lowest `order` and descends through projects until it reaches a leaf, which it runs with one fresh subagent. Files are the only channel between agents. The filename says which skill runs an item. An item named `create spec for …` is run with `vna-spec`, which writes the parent project's purpose and spec. An item named `create plan for …` is run with `vna-plan`, which turns that spec into child files. Every other item is run with `vna-executor`, which does the work and leaves a `# Result`. A project that gets no children besides its spec and plan tasks is a leaf too: it is executed as a whole. An unfinished item whose `next_action_by` names a human is a checkpoint: the move is the human's, so the controller stops there and goes on once the human has handed the item back.

If you are a subagent and your instructions make no sense, or you otherwise cannot sensibly proceed, you can throw an exception: read `.claude/references/vna-exception-throwing.md` when you consider one, not before.

## Formats

These formats are exact, because other agents read them.

1. **Queue files an agent creates**: they carry the full property header with `owner: claude`, followed by the properties `order`, `model` and `effort`. Number `order` in gaps of 10; an item inserted later takes a free number, and decimals are allowed. `model` and `effort` are empty by default: the item then runs with the model and effort of the user's session. Set one of them only where that default may not be good. Values of `effort`: `low`, `medium`, `high`, `xhigh`, `max`. Value of `model`: a name the Agent tool accepts.
2. **Spec and plan tasks** of a project X are named `!create spec for {X}` and `!create plan for {X}`; the plan task of a later planning round is named `!create plan 2 for {X}`. The braces are part of the name: the spec task of the project `,new website` is `!create spec for {new website}`. These tasks are children of X and carry the header of 1. The spec task comes first in X's queue, the plan task behind it.
3. **Input prompt**: the text above an item's first heading. In a project file it stands below the `![[subtasks.base]]` line.
4. **Checkpoint file**: a file named `!checkpoint <what is asked>`. It only asks a human something, and the controller never runs an agent on it. The name contains no `?` or `:`, which are invalid in filenames on Windows.
5. **Checkpoint question format**: numbered questions, each with a recommendation and an empty `A:` line; then one line saying that an unanswered question means its recommendation stands.
