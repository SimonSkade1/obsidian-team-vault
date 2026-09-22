# Environment Adaptations

The core loop (draft → test → review → improve → repeat) is the same everywhere; the mechanics differ by what's available. Capabilities that vary: subagents, a browser/display, and the `claude` CLI.

## Claude.ai (no subagents, no display, no `claude` CLI)

1. **Running test cases**: no parallel execution. For each test case, read the skill's SKILL.md and follow it to complete the prompt yourself, one at a time. Skip baseline runs. Known limitation: you wrote the skill and you're also running and judging it, with full context — expect this to be biased toward the skill looking good. Compensate by (a) writing programmatic checks where assertions allow it (scripts don't share your bias) and (b) leaning harder on the human review step.
2. **Reviewing results**: no browser viewer. Present results in the conversation — per test case, the prompt and the output; save output files to the filesystem so the user can download and inspect them. Ask for feedback inline.
3. **Benchmarking**: skip it — baseline comparisons aren't meaningful without independent runs. Rely on qualitative feedback.
4. **Description optimization**: requires `claude -p` (Claude Code only). Skip; you can still hand-tune the description using the principles in SKILL.md.
5. **Packaging**: `package_skill.py` needs only Python and a filesystem — works; the user downloads the `.skill` file.

## Cowork (subagents, no display)

1. The main subagent workflow works (parallel runs, baselines, grading). If timeouts bite, running test prompts serially is fine.
2. No browser: generate the viewer with `--static <output_path>` and give the user a clickable link to open the HTML themselves. Generate the viewer with `generate_review.py` right after runs finish — before analyzing outputs yourself — so the user can start reviewing immediately (this step is easy to forget in Cowork; consider a todo item for it).
3. Feedback: with no running server, "Submit All Reviews" downloads `feedback.json` as a file. Read it from there (you may need to request access), then copy it into the workspace for the next iteration.
4. Packaging works. Description optimization (`run_loop.py`) works too (subprocess-based, no browser) — but save it until the skill body is finished and the user agrees it's in good shape.

## Updating an existing skill (any environment)

1. **Preserve the original name** — directory name and `name` frontmatter field unchanged. If the installed skill is `research-helper`, output `research-helper.skill`, not `research-helper-v2`.
2. **Copy to a writable location before editing** — installed skill paths may be read-only. Copy to `/tmp/<skill-name>/`, edit there, package from the copy.
3. **If packaging manually, stage in `/tmp/` first**, then copy to the output directory — direct writes may fail due to permissions.
