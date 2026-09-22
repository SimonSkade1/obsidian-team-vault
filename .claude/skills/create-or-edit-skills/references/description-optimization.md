# Description Optimization

The description field is the primary mechanism determining whether Claude invokes a skill. This workflow measures triggering accuracy and improves it. Requires the `claude` CLI (`claude -p`); see `environments.md` if unavailable.

## How triggering works (design your evals around this)

Skills appear in Claude's available-skills list as name + description, and Claude decides from that whether to consult the skill. Two empirical properties matter:

1. Claude consults skills mainly for tasks it can't easily handle alone. Trivial one-step queries ("read this PDF") often won't trigger a skill even when the description matches perfectly. Eval queries must therefore be substantive enough that consulting a skill would actually help — simple queries test nothing.
2. This threshold is a property of the current model, not a constant. Retest triggering after model updates.

## Step 1: Generate trigger eval queries

Create an eval set — default 20 queries, but note the statistics: with a 60/40 train/test split, 20 queries leaves ~8 held-out queries × 3 runs each ≈ 24 trigger decisions selecting the winner. That catches gross failures but is noisy for close calls. For skills that matter, generate 40–60 queries before trusting small score differences.

Mix should-trigger and should-not-trigger roughly evenly. Save as JSON:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

Queries must be realistic — what a Claude Code or Claude.ai user would actually type: concrete and specific, with file paths, personal context, column names, company names, URLs, a bit of backstory. Some lowercase, some with typos or casual speech. Mixed lengths. Focus on edge cases rather than clear-cut cases (the user signs off on them anyway).

Bad: `"Format this data"`, `"Extract text from PDF"`, `"Create a chart"`

Good: `"ok so my boss just sent me this xlsx file (its in my downloads, called something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add a column that shows the profit margin as a percentage. The revenue is in column C and costs are in column D i think"`

**Should-trigger queries**: cover different phrasings of the same intent — formal and casual; cases where the user never names the skill or file type but clearly needs it; uncommon use cases; cases where this skill competes with another but should win.

**Should-not-trigger queries**: the valuable ones are near-misses — queries sharing keywords or concepts with the skill but needing something different. Adjacent domains, ambiguous phrasing where naive keyword matching would fire, contexts where another tool is more appropriate. Avoid obviously irrelevant negatives ("write a fibonacci function" against a PDF skill tests nothing).

## Step 2: Review with user

Bad eval queries lead to bad descriptions, so have the user review the set via the HTML template:

1. Read `assets/eval_review.html`
2. Replace placeholders: `__EVAL_DATA_PLACEHOLDER__` → the JSON array (unquoted — it's a JS variable assignment), `__SKILL_NAME_PLACEHOLDER__` → skill name, `__SKILL_DESCRIPTION_PLACEHOLDER__` → current description
3. Write to e.g. `/tmp/eval_review_<skill-name>.html` and open it
4. The user edits queries, toggles should-trigger, adds/removes entries, clicks "Export Eval Set"
5. The file lands in `~/Downloads/eval_set.json` — check for the most recent version if there are duplicates (`eval_set (1).json`)

## Step 3: Run the optimization loop

Tell the user this takes a while and will run in the background. Save the eval set to the workspace, then:

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

Use the model ID from your system prompt so the triggering test matches what the user actually experiences. Periodically tail the output to report which iteration it's on and the scores.

The loop: splits the eval set 60% train / 40% held-out test, evaluates the current description (each query 3×), has Claude propose improvements based on failures, re-evaluates on both splits, iterates up to 5 times, then opens an HTML report and returns JSON with `best_description` — selected by test score rather than train score to limit overfitting (note: with a small eval set, "test score" is itself noisy; see Step 1).

## Step 4: Apply the result

Update the skill's frontmatter with `best_description`. Show the user before/after and the scores. Sanity-check the winner against the description principles in SKILL.md (front-loaded key use case, explicit trigger contexts, "not for X" boundaries) — the optimizer maximizes the eval metric, and with few queries a degenerate-looking description can win by chance.
