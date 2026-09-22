# Full process: the loop, testing, improving, delivering

Read this file end to end when creating a skill or doing a major rewrite. (`SKILL.md` carries the user's protocol and the writing advice; this file carries the rest of the loop.)

The core loop:

1. Figure out what the skill should do and when it should trigger
2. Draft (or edit) the skill
3. Run test prompts with the skill and evaluate the results with the user
4. Improve based on feedback; repeat until satisfied
5. Optionally optimize the description for triggering accuracy; package and deliver

Figure out where the user is in this loop and help them progress. They might arrive with nothing but an idea, with an existing draft, or with a skill that misbehaves. Enter the loop at the right point.

## Right-size the process

Not every skill needs the full testing apparatus. Match the process weight to the skill:

1. **Lightweight path** — for skills encoding preferences, style, or workflows with subjective output (writing voice, roleplay, review checklists): draft it, run one or two sanity-check prompts, let the user eyeball the output, ship. Assertions and benchmarks add ceremony without signal here.
2. **Full eval path** — for skills with objectively verifiable output (file transforms, data extraction, code generation, fixed multi-step workflows), especially ones that will run many times: use the testing workflow in `references/eval-workflow.md`.

Suggest the appropriate default, let the user decide, and stay flexible — if the user says "just vibe with me," do that.

Also worth surfacing before building: skills pay rent. Every installed skill's name + description sits in context on every message. A good heuristic to share when the user seems to be building speculatively: has this task come up ~5 times already, and will it come up ~10 more? If not, a one-off prompt may serve better than a skill.

## Testing and iterating

For the lightweight path: run 1–2 realistic prompts using the skill, show the user, adjust. Done.

For the full eval path, read `references/eval-workflow.md`. It covers: writing test cases (`evals/evals.json`), spawning with-skill and baseline runs, drafting assertions, grading, benchmarking, the eval viewer the user reviews results in, and reading their feedback. If a Workflow orchestration tool is available, use it for the run fan-out and grading instead of hand-spawning subagents (see the note in that file). The one thing to internalize even before reading it: human review time is the scarce resource in this loop, so get outputs in front of the user (via the viewer) *before* doing your own detailed analysis — your self-review can happen while they review.

Environment matters: subagents, browsers, and the `claude` CLI aren't available everywhere. Read `references/environments.md` for what to adapt in Claude.ai and Cowork, and for the mechanics of updating an existing skill (preserve its name, copy to a writable location before editing).

## Improving the skill

This is the heart of the loop. Principles, in priority order:

1. **Generalize from feedback.** The skill may run thousands of times across prompts you'll never see; you're iterating on a handful of examples only because it's fast. A fix that works only for those examples is worthless. When an issue is stubborn, resist fiddly overfitted patches and constrictive MUSTs — try a different framing, metaphor, or recommended working pattern instead. Iterating on a fixed test set creates optimization pressure toward it, so rotate in a fresh prompt occasionally, and before declaring the skill done, run 1–2 prompts you never optimized against.
2. **Keep it lean.** Read the transcripts, not just the final outputs. If the skill makes the model do unproductive work, cut the part causing it and see what happens. Remove anything not earning its tokens.
3. **Explain the why.** Even when user feedback is terse or frustrated, work out what they actually need and transmit that understanding — not just the surface instruction — into the skill.
4. **Bundle repeated work.** If test runs independently wrote similar helper scripts (every run produced its own `create_docx.py`), that's a strong signal to write it once, put it in `scripts/`, and point the skill at it.

Take your time here — thinking time is not the bottleneck, and skills compound: a small quality difference multiplies across every future invocation. Stop iterating when the user is happy, feedback comes back empty, or you've stopped making real progress.

## Description optimization

After the skill body is in good shape, offer to optimize the description with the trigger-eval loop in `references/description-optimization.md` (requires the `claude` CLI; see `references/environments.md` if unavailable). Two things to keep in mind:

1. Triggering behavior is an empirical property of the current model, not a constant: models consult skills mainly for tasks they can't trivially handle alone, and this threshold shifts between model versions. Retest triggering (and ideally the evals) after model updates.
2. The default eval set (20 queries) gives roughly 8 held-out queries — enough to catch gross failures, noisy for fine comparisons. If the skill matters, use 40–60 queries before trusting small score differences.

## Deliver

In local Claude Code-style setups, installing is just placing the folder: `~/.claude/skills/<name>/` (personal, all projects) or `<project>/.claude/skills/<name>/` (project-scoped). Package a `.skill` file only for sharing or Claude.ai:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

If a file-delivery tool is available (`present_files`, or `SendUserFile` in Cowork remote), send the `.skill` file — its card shows a **Save skill** button when the user's org allows skill creation.

## Reference files

Read these when you reach the relevant stage — not upfront:

1. `references/eval-workflow.md` — full testing loop: test cases, runs, assertions, grading, benchmark, viewer, feedback
2. `references/environments.md` — Claude.ai and Cowork adaptations; updating existing skills
3. `references/description-optimization.md` — trigger eval queries, review UI, optimization loop
4. `references/schemas.md` — JSON structures (evals.json, grading.json, benchmark.json, ...)
5. `agents/grader.md`, `agents/comparator.md`, `agents/analyzer.md` — instructions for grader/comparison/analysis subagents
