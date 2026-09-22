---
name: create-or-edit-skills
description: Mandatory read before creating or editing any skill, however small the edit. Also covers skill evals/benchmarks and tuning descriptions for better triggering.
---

# Creating and editing skills

**For creating a new skill or a major rewrite, reading `references/process.md` is required, not optional.** It covers the full loop: right-sizing the process, testing, improving the skill, description optimization, and delivery. For smaller edits, this file suffices.

## The user's protocol for skill changes

1. **Never silently create or edit a skill.** Always tell the user exactly what you changed.
	1. **Default to proposing the edit and asking before applying** — unless it's a clear-cut fix (e.g. a broken cross-reference) or the user has already signaled they want it applied.
2. **Keep skills lean:** tight, action-oriented `description` (it's the router); no clutter; keep it simple; lean toward not adding stuff unless clearly important.
3. **Don't overfit to specific failure modes.** Usually say how things should be done and not how they shouldn't.
4. **Make sure there are no implicit references to anything that isn't in the context of the agent who will read the skill.**
5. **The skill should be written in a sensible order so explanations and instructions further down make sense in the context given above.**
6. **Don't give optional references without clear instructions when to read them.**
	1. Don't have external references that should always be read. If sth should always be read it should be part of the skill. (Possible exception: If the skill is only invoked as `.claude/agents/` subagent where the subagent always takes the other required skill too. Still no link with "read that" though.)

## Capture intent

The current conversation might already contain the workflow the user wants to capture (e.g. "turn this into a skill"). If so, extract what you can from the history first — tools used, sequence of steps, corrections the user made, input/output formats — and confirm your understanding before proceeding.

Establish:

1. What should this skill enable Claude to do?
2. When should it trigger? (what user phrases/contexts)
3. What's the expected output format?
4. How heavyweight a process fits (right-sizing in `references/process.md`)

Then interview for edge cases, input/output formats, example files, success criteria, and dependencies. If MCPs are available for research (searching docs, finding similar skills), use them — come prepared so the burden on the user is low.

## Writing the skill

### Anatomy

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

### Progressive disclosure

Skills load in three levels, and each level has a different cost profile:

1. **Metadata** (name + description) — in context on *every* message, whether or not the skill is used. This is the expensive real estate.
2. **SKILL.md body** — loaded whenever the skill triggers. Too much information may still lead claude to perform worse.
3. **Bundled resources** — loaded only as needed; scripts can execute without ever entering context.

Push content down this hierarchy as far as it will go. Give large reference files (>300 lines) a table of contents. When a skill supports multiple domains/frameworks, organize by variant (e.g. `references/aws.md`, `references/gcp.md`) so only the relevant file gets read.

### The description

The description is the primary triggering mechanism. Include both what the skill does and the specific contexts in which to use it — all "when to use" information belongs here, not in the body. Front-load the most important use case. Beyond covering the triggers, optimize hard for brevity: the description is paid on every message, so shorten it and keep it lean as much as sensibly possible — cut anything that doesn't improve routing. 1–3 sentences usually suffice; the ~1,536-character cap (Claude Code truncates long entries) is a limit, not a budget.

Triggering errs in both directions and the costs are asymmetric to the user's setup:

1. **Undertriggering** (the more common failure): the skill silently never fires. Counter it by naming concrete trigger contexts, not just capabilities — "use whenever the user mentions dashboards, internal metrics, or wants to display company data, even without the word 'dashboard'" beats "how to build dashboards."
2. **Overtriggering**: false fires load the whole body into context and, across a profile with many skills, degrade every session. The more skills the user has installed, the more precision matters — include "not for X" boundaries when adjacent tasks exist.

Don't guess which failure mode you have; the trigger eval in `references/description-optimization.md` measures it.

### Writing style

Prefer the imperative form. Explain *why* things matter instead of stacking ALL-CAPS MUSTs — models have good theory of mind, and instructions whose purpose is understood generalize; bare commandments get pattern-matched and misapplied. If you find yourself writing ALWAYS or NEVER or repeating an instruction for emphasis, treat it as a yellow flag: usually the fix is explaining the reasoning once, clearly. Rigid structure is fine where the output genuinely must be exact (templates, schemas, field names a script depends on) — say so, and say why.

Make the skill general rather than fitted to the specific examples at hand. Draft, then reread with fresh eyes and cut anything not pulling its weight.

Useful patterns:

**Output format** — when exactness matters, show the template:
```markdown
## Report structure
Use this exact template (downstream tooling parses these headers):
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples** — input/output pairs communicate more than prose:
```markdown
## Commit message format
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```
