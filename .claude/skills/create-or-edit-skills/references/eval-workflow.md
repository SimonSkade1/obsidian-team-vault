# Eval Workflow

The full testing loop for skills with objectively verifiable output. This file assumes subagents are available (Claude Code, Cowork); for environments without them, read `environments.md` for what to substitute.

Do not use `/skill-test` or other testing skills; this workflow is self-contained.

## Contents

1. Test cases
2. Workspace layout
3. Step 1: Spawn all runs in the same turn
4. Step 2: Draft assertions while runs are in progress
5. Step 3: Capture timing data as runs complete
6. Step 4: Grade, aggregate, launch the viewer
7. Step 5: Read the feedback
8. The iteration loop
9. Blind comparison (advanced)

## 1. Test cases

After drafting the skill, write 2–3 realistic test prompts — the kind of thing a real user would actually type, with concrete details (file names, column names, casual phrasing). Share them: "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" Real prompts from the user's own work beat invented ones.

Save to `evals/evals.json` (prompts only; assertions come later — see `schemas.md` for the full schema):

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

## 2. Workspace layout

Put results in `<skill-name>-workspace/` as a sibling of the skill directory. Organize by iteration (`iteration-1/`, `iteration-2/`, ...), and within that one directory per test case. Give each eval a descriptive name based on what it tests (use it for the directory too, not `eval-0`). Create directories as you go, not upfront.

## 3. Step 1: Spawn all runs (with-skill AND baseline) in the same turn

For each test case, spawn two subagents in the same turn — one with the skill, one baseline — so everything finishes around the same time instead of serializing.

**Workflow tool variant**: if the harness has a Workflow orchestration tool, prefer it over hand-spawned subagents — pipeline over test cases, each stage running the with-skill and baseline agents in parallel and grading as each pair completes (no barrier between test cases). Per-run token/duration notifications don't arrive in this mode; skip `timing.json` (or pull numbers from the workflow progress view) and let the benchmark cover pass rates.

**With-skill run:**

```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/<eval-name>/with_skill/outputs/
- Outputs to save: <what the user cares about — e.g. "the .docx file", "the final CSV">
```

**Baseline run** (same prompt; the baseline depends on context):

1. Creating a new skill → no skill at all; save to `without_skill/outputs/`.
2. Improving an existing skill → the old version. Before editing, snapshot it (`cp -r <skill-path> <workspace>/skill-snapshot/`) and point the baseline subagent at the snapshot; save to `old_skill/outputs/`.

Write an `eval_metadata.json` per test case (assertions may be empty for now). If an iteration uses new or modified prompts, recreate these files — they don't carry over.

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

## 4. Step 2: While runs are in progress, draft assertions

Use the waiting time: draft quantitative assertions for each test case and explain them to the user (or review/explain existing ones in `evals/evals.json`).

Good assertions are objectively verifiable and have descriptive names — they should read clearly in the viewer so a glance tells the user what each one checks. Don't force assertions onto subjective qualities that need human judgment.

Update `eval_metadata.json` and `evals/evals.json` once drafted, and tell the user what they'll see in the viewer.

## 5. Step 3: As runs complete, capture timing data

Each completing subagent's notification contains `total_tokens` and `duration_ms`. This notification is the only place the data exists — save it immediately (per notification, not batched) to `timing.json` in the run directory:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

## 6. Step 4: Grade, aggregate, launch the viewer

Once all runs are done:

1. **Grade each run** — spawn a grader subagent (or grade inline) following `agents/grader.md`; save `grading.json` in each run directory. The `expectations` array must use exactly the fields `text`, `passed`, `evidence` — the viewer parses these names. For programmatically checkable assertions, write and run a script instead of eyeballing: faster, unbiased, reusable across iterations.
2. **Aggregate** — from this skill's directory:
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
   Produces `benchmark.json`/`benchmark.md` with pass rate, time, tokens per configuration (mean ± stddev and delta). Put each with_skill version before its baseline counterpart. Manual generation: see `schemas.md`.
3. **Analyst pass** — read the benchmark data for patterns the aggregates hide (see the "Analyzing Benchmark Results" section of `agents/analyzer.md`): non-discriminating assertions that always pass, high-variance (flaky) evals, time/token tradeoffs.
4. **Launch the viewer** — always via `generate_review.py` (no custom HTML), and launch it *before* doing your own detailed output review. Human review time is the scarce resource; your analysis can run in parallel with theirs, and reviewing first risks anchoring your revision on your own reading instead of theirs.
   ```bash
   nohup python <this-skill's-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```
   For iteration 2+, add `--previous-workspace <workspace>/iteration-<N-1>`. Headless environments: use `--static <output_path>` (see `environments.md`).
5. **Tell the user** something like: "I've opened the results in your browser. Two tabs — 'Outputs' lets you click through each test case and leave feedback, 'Benchmark' shows the quantitative comparison. Come back and let me know when you're done."

### What the user sees

The Outputs tab shows one test case at a time: prompt, output files rendered inline where possible, previous output (iteration 2+, collapsed), formal grades (collapsed), a feedback textbox that auto-saves, and their previous feedback. The Benchmark tab shows pass rates, timing, and token usage per configuration with per-eval breakdowns and analyst observations. "Submit All Reviews" saves everything to `feedback.json`.

## 7. Step 5: Read the feedback

When the user says they're done, read `feedback.json`:

```json
{
  "reviews": [
    {"run_id": "eval-0-with_skill", "feedback": "the chart is missing axis labels", "timestamp": "..."},
    {"run_id": "eval-1-with_skill", "feedback": "", "timestamp": "..."}
  ],
  "status": "complete"
}
```

Empty feedback means the user thought it was fine; focus improvements where they had specific complaints. Kill the viewer server afterwards: `kill $VIEWER_PID 2>/dev/null`.

## 8. The iteration loop

1. Apply improvements to the skill (see "Improving the skill" in SKILL.md)
2. Rerun all test cases into `iteration-<N+1>/`, including baselines. New skill → baseline stays `without_skill`. Existing skill → judgment call: original version or previous iteration.
3. Launch the viewer with `--previous-workspace` pointing at the previous iteration
4. Wait for the user's review; read feedback; repeat

Before declaring the skill done, expand the test set — including at least one prompt you never iterated against — and run once more at that larger scale.

## 9. Blind comparison (advanced)

For a rigorous answer to "is the new version actually better?": give both outputs to an independent agent without revealing which is which and let it judge, then analyze why the winner won. Read `agents/comparator.md` and `agents/analyzer.md`. Requires subagents; most users won't need it — the human review loop is usually sufficient.
