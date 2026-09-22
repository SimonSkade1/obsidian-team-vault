# Handoff-note content — research basis (2026-07-08)

Compiled from 3 Opus research subagents: (A) human-domain handover practices, (B) AI-agent context handoffs, (C) completion records. This is the evidence behind SKILL.md §1. Read when re-optimizing the skill.

## Synthesis — what went into the skill

1. Goal & done-criteria first, the user's instructions/constraints quoted verbatim (B1, B7, A4; Cognition: WHAT survives summaries, WHY doesn't; "done was never defined" is the top long-run failure).
2. State synthesized + verified against disk, verified-vs-believed marked (A1 synthesis-not-dump; B: unverified completion claims are the #1 LLM handoff failure; Anthropic harness: completion is *tested*, never asserted).
3. Note-as-index with exact paths, never note-as-copy (B2; Manus "restorable compression"; chapsoft "pass pointers, verify content"; keeps note short → Chroma context rot: reasoning degrades well before window is full, ~50k can already hurt).
4. Decisions + rationale (A5, B5, C4 — unanimous across all three).
5. Dead ends / settled negatives (A6, B6; Manus "leave the wrong turns in").
6. Continuation mode: ordered next steps, first immediately executable + contingencies "if X do Y" (A2/A3 — contingency planning is I-PASS's differentiator; B3 recitation combats goal drift).
7. Completion mode: outcome vs each criterion, NOT-verified ledger, loose ends/follow-ups, `status: review` hook (C1, C3, C6, C7).
8. Stable headers / fixed skeleton (A11; broken-telephone paper: unconstrained prose drifts fastest over hops).
9. "What would surprise the successor?" final check (A6/A17: omission-by-assumed-knowledge is the top failure), hand off with context to spare (A19: rushed handoffs).
10. Relay chains: one note updated per hop, rebuild from artifacts not from predecessor summaries (B multi-hop hygiene; Sonovore single live session-state.md).
11. Task-oriented, not conversation-narration — the deliberate contrast to Claude Code's own compaction prompt, which is chronological/conversation-oriented ("analyze each message", "list ALL user messages"). The handoff note serves the task; only task-relevant conversation content (constraints, preferences, decisions) survives, as distilled fields.

## Deliberately left out (candidates for later optimization)

12. Receiver read-back: successor re-states its understood plan before acting (I-PASS "synthesis by receiver" — the element with a forcing-function role in the NEJM trial). Partially covered by 2b's "verify claims against disk first".
13. Machine-checkable state files: JSON subtask list with per-item `passes` + verification method (Anthropic long-running harness); durable-vs-volatile split into separate files (Letta memory blocks, artemxtech).
14. Completion-record quality gate (SRE: senior review before a postmortem counts as done) and owner+deadline tracking for follow-ups.
15. Emergency pre-compact dump mode (Sonovore) — a degraded fast path when context is nearly gone.
16. Explicit responsibility-transfer timestamp ("as of T, state is X; next actor does Y") — RIP/TOA marked-event principle.

---

## Report A — Human-domain handover practices (work-in-progress)

### Top content elements, ranked

1. **Synthesis / current state as a coherent narrative** (not raw log) — the single highest-leverage element. I-PASS makes the receiver *re-state* the summary ("Synthesis by Receiver"); the point is a digested mental model, not a data dump. For a solo written handoff, the writer must do this synthesis *for* the successor.
2. **Situation awareness + contingency guidance ("if/then")** — I-PASS's "S" is explicitly "know what's going on; plan for what might happen using if/then statements." The element most associated with the NEJM error reduction and the one most often missing from naive summaries.
3. **Action list / next steps with explicit ownership** — I-PASS "A" = to-dos with owner and timeline. ICS and PM transition docs both center "current plan + who owns what." Ambiguous responsibility transfer is a top failure mode.
4. **Objectives, priorities, and the current plan** — ICS transfer-of-command briefing leads with these. Successor needs the *goal* and *why this approach* before the details, or they optimize the wrong thing.
5. **Rationale / "the why" behind decisions and tacit judgment** — PM/departure knowledge-transfer sources stress capturing tacit knowledge: judgment calls, "why behind processes," escalation heuristics. This is what dies when the session's context is lost.
6. **Undocumented workarounds + "what would surprise you"** — KT guides single out "the things never written down" as the largest knowledge gap; the maritime night-order book exists precisely to flag the non-obvious/anomalous.
7. **Constraints, limitations, and known risks/open items** — ICS ("constraints or limitations," "incident potential"); PM ("risks, open items").
8. **History / how we got here (condensed)** — enough backstory to interpret the state; over-inclusion here is the classic data-dump failure.
9. **Key contacts / resources / where things live** — for a vault agent: file paths, external sources, tools.

### Structural / process principles

10. Write for "you in 6 months who hasn't thought about this," a colleague with zero session memory (lab-notebook standard).
11. Structured/standardized template beats free-form — I-PASS/SBAR/ICS-201 all impose a fixed skeleton; lack of standardization is itself a documented failure mode.
12. Synthesis over volume; digest, don't dump.
13. Front-load severity/priority — lead with what matters most (I-PASS "Illness severity" first; SBAR "Situation" first).
14. Make responsibility transfer explicit and time-stamped (RIP/TOA, ICS).
15. Anticipate, don't just report — forward-looking contingencies are the effective-vs-ineffective differentiator.
16. Build in read-back/validation — receiver restates before acting.

### Documented failure modes

17. **Omission** — critical detail unshared due to assumed shared knowledge or time pressure (top medical-handoff failure).
18. **Data-dump without synthesis.**
19. **Rushed/last-minute handoff** (agent analogue: writing the note at 2% context).
20. **No standardization** — inconsistent structure leaves predictable gaps.
21. **Ambiguous responsibility / no clear next action.**
22. Scale: up to ~80% of serious medical errors involve miscommunication at transitions (Joint Commission).

### Continuation vs completion (A's view)

23. The whole watch/shift/command genre is *continuation*: its defining additions are contingency if/then guidance, next actions with owners, a marked transfer moment. A completed-work record optimizes for retrieval/audit (lab-notebook reproducibility standard), not action continuity.
24. Continuation = forward-weighted (next steps, open items, contingencies); completion = backward-weighted (what was done, decisions, final artifacts). Contingency guidance is the clearest dividing line.

### Sources

1. **[Changes in Medical Errors after Implementation of a Handoff Program (I-PASS)](https://www.nejm.org/doi/full/10.1056/NEJMsa1405556)** (NEJM paper; 2014-11-06) — landmark trial: I-PASS bundle across 9 sites cut medical errors 23% and preventable adverse events 30%; strongest quantitative evidence that a structured handoff template improves outcomes.
2. **[I-PASS Institute — Resources](https://www.ipassinstitute.com/resources)** (org/curriculum site; date unverified) — I-PASS = Illness severity, Patient summary, Action list, Situation-awareness & Contingency planning, Synthesis by receiver.
3. **[SBAR Tool: Situation-Background-Assessment-Recommendation](https://www.ihi.org/library/tools/sbar-tool-situation-background-assessment-recommendation)** (IHI tool; living doc) — minimal front-loaded structure; model for "lead with what matters."
4. **[Transfer of Command](https://training.fema.gov/emiweb/is/icsresource/assets/transfer%20of%20command.pdf)** (FEMA/ICS doc; 2019-02-27) — canonical written-briefing element list: history; priorities/objectives/current plan; resources; constraints/limitations; incident potential.
5. **[FM 3-90 Ch. 15 — Relief in Place](https://www.globalsecurity.org/military/library/policy/army/fm/3-90/ch15.htm)** (US Army field manual; date unverified) — RIP/TOA: responsibility transferred as a marked event; "continuity books."
6. **[Asynchronous communication for remote work](https://handbook.gitlab.com/handbook/company/culture/all-remote/asynchronous/)** (GitLab handbook; living doc) — single-source-of-truth: write it down or it doesn't transfer.
7. **[Knowledge Transfer for Successful Employee Handovers (+Template)](https://enboarder.com/blog/checklist-knowledge-transfer/)** (blog/template; ~2026) — explicit vs tacit knowledge; validate that knowledge transferred, not merely delivered.
8. **[Keeping an Electronic Lab Notebook — Basic Principles and Best Practices](https://oir.nih.gov/system/files/media/file/2024-07/best_practices-keeping_eln-trainee_0.pdf)** (NIH guide; 2024-07) — write so a colleague or future-you can reproduce the work in 6 months with no conversation.
9. **[Handoff communication: using failure modes and effects analysis](https://pubmed.ncbi.nlm.nih.gov/21467897/)** (PubMed paper; 2011) — FMEA-grounded failure-mode list (omission, rushing, nonstandardization).
10. **[Checklist for taking over bridge watch](https://marinegyaan.com/checklist-for-taking-over-bridge-watch/)** (maritime training article; date unverified) — night-order-book practice: flag anomalies and non-obvious standing instructions before transfer.

---

## Report B — AI-agent context handoffs

### Top content elements, ranked

1. **Goal + success criteria / "definition of done", verbatim where the user stated them** — the #1 documented failure of long agent runs is that "done" was never defined; naive summaries keep the WHAT and drop the WHY/acceptance bar.
2. **Pointers (exact paths/URLs/IDs) to durable on-disk artifacts — NOT copies.** The note is an index into source-of-truth files; duplicated content goes stale and drifts. "The config file" instead of an exact path is a failure.
3. **An immediately-executable first next action**, plus how to verify current state. Recitation of the next step combats goal drift (Manus todo.md pattern).
4. **Verified status of each subtask with the verification method and explicit passes/fails flag** — completion must be *tested*, not asserted (Anthropic harness: JSON feature list, `passes` boolean).
5. **Decisions + rationale** — actions carry implicit decisions; if only outcomes survive, successors make conflicting choices (Cognition).
6. **Dead ends / settled negatives ("don't re-try X, because…")** — "leave the wrong turns in"; append-only bug ledgers exist to stop re-running settled tests.
7. **User-stated constraints & preferences, quoted** — high-value, low-token, easily paraphrased away.
8. **Open questions / what the next hop must decide.**

### Structural / process principles

9. **Note-as-index, not note-as-copy** — filesystem is unlimited persistent memory; "restorable compression": drop content but keep paths/URLs so nothing is unrecoverable.
10. **Verify-before-build-on ("intake hygiene")** — successor treats note claims as unverified pointers, re-checks against disk; blocks "evidence laundered through a trusted source."
11. **Separate durable vs volatile state** — stable constraints/goal in a rarely-changing block; live progress in a continuously-rewritten dashboard (avoids stale-memory rot).
12. **Multi-hop hygiene** — each hop re-derives from *artifacts*, not by summarizing the previous *note* (telephone-game accumulation); structured fields degrade far slower than free prose.
13. **Length: "smallest set of high-signal tokens"** — maximize recall first, then prune; context rot degrades reasoning well before the window fills (~50k can already hurt).
14. **Prefer structured formats the model won't casually corrupt** (JSON vs prose).

### Failure modes

15. **Unverified completion claims** — features "marked done" that fail; hallucinated changes.
16. **Vague pointers / lost specifics** — exact paths become "the config file"; numbers/edge-cases vanish.
17. **Keeping WHAT, losing WHY/success-criteria** → conflicting downstream decisions.
18. **Lost constraints/preferences** — paraphrase drops user-stated rules.
19. **Dead ends erased** → successor re-explores.
20. **Multi-hop drift / telephone game** — omission+distortion+addition accumulate; worse with free-form prose and long chains.
21. **Trusting the note over on-disk reality** — provenance failure.
22. **Context rot** — even a perfect long note degrades the reader as it grows.

### Continuation vs completion (B's view)

23. Same skeleton, different emphasis and terminal fields — not a different doc. Continuation foregrounds next action + open decisions + volatile state + what's unverified; completion foregrounds final verified deliverable location + passed acceptance checks + residual known-issues/follow-ups, reading as an audit trail. Verification discipline is *heavier* at completion (it's the last gate). Practically: one template with a mode that swaps the trailing block between NEXT ACTION and DELIVERABLE + PROOF + FOLLOW-UPS.

### Sources

11. **[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)** (Anthropic engineering; 2025-11-26) — fresh-context sessions rebuild state from on-disk artifacts: JSON feature list with per-item `passes` booleans + verification steps, progress file, `init.sh`; completion is tested, never asserted.
12. **[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)** (Anthropic engineering; 2025-09-29) — compaction = keep decisions/unresolved issues/constraints, drop tool noise; "smallest set of high-signal tokens."
13. **[Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)** (blog; 2025-07-18) — "leave the wrong turns in"; restorable compression; todo.md recitation against lost-in-the-middle goal drift.
14. **[Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents)** (Cognition blog; 2025-06-12) — share full traces not lossy summaries; "actions carry implicit decisions"; compression is "hard to get right."
15. **[Context Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot)** (Chroma research; 2025-07) — all 18 tested frontier models degrade as input grows, well before the window fills.
16. **[LLM as a Broken Telephone: Iterative Generation Distorts Information](https://arxiv.org/html/2502.20258v1)** (arXiv paper; 2025-02) — multi-hop drift accelerates with chain length and unconstrained prompts; structure slows but never eliminates it.
17. **[Pass pointers, verify content](https://chapsoft.com/dispatches/pass-pointers-verify-content)** (blog; 2026-04-21) — pass opaque pointers, not paraphrases; receiver fetches and verifies; unverified summary is a provenance failure.
18. **[claude-code-handoff (Sonovore)](https://github.com/Sonovore/claude-code-handoff)** (repo; ⭐10) — mode-specific handoffs (Context/Task/Bug/Clean); references artifacts by path; single live `session-state.md`; append-only bug ledger.
19. **[Memory Blocks: The Key to Agentic Context Management](https://www.letta.com/blog/memory-blocks/)** (Letta blog; date unverified) — labeled memory blocks (user prefs/constraints vs behavior rules) with persistence-by-default.
20. **[Never lose your work between Claude Code sessions](https://artemxtech.substack.com/p/never-lose-your-work-between-claude)** (Substack blog; 2026-05-27) — handoff = what-done / current-state / next-steps / intent + definition of done; volatile state out of static memory files.
21. **[How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)** (Anthropic engineering; 2025-06) — lead agent saves its plan to memory before spawning subagents so overflow can't lose the plan.

---

## Report C — Completion records

### Top content elements, ranked

1. **Goal vs outcome against explicit success/acceptance criteria** — AAR Q1/Q2 ("supposed to happen" vs "actually happened"); a completion claim is meaningless without the bar it's measured against.
2. **Artifact inventory with exact locations** — transition-to-ops "turnover package"; without it the work is done but unfindable/unreusable.
3. **What was verified vs not, and how** — distinguish evidence-backed claims from assumed-good; prevents "success without evidence."
4. **Key decisions + rationale** — lets a future agent avoid re-litigating settled choices or breaking load-bearing ones.
5. **Deviations from plan + why** — AAR Q3; records what the final state actually is vs what was commissioned.
6. **Known limitations / loose ends / risks** — the single most valuable thing for follow-up months later.
7. **Recommended follow-ups with owners** — SRE action items are specific, owned, due-dated; unowned recommendations don't happen.
8. **Reusable lessons (sustain + change)** — AAR Q4 keeps "sustain" items, not just fixes.
9. **Method/provenance trail sufficient to reproduce** — reproducible-research norm.
10. **Acceptance / sign-off state** — PRINCE2 end-project report as "final accountability document"; here, the `status: review` flag for the user.

### Principles for not being write-only

11. **Pull must be cheap, or push it** — GAO's core NASA finding: the lessons system was a passive repository nobody searched ("hard to weed through irrelevant lessons to get the jewels"); managers asked colleagues instead. Put the record where the successor will already look, not in a separate graveyard.
12. **Findable + signal-dense** — short, indexed, co-located with the artifact.
13. **Peer review before publication** — SRE quality gate stops write-only junk.
14. **Blameless/frank framing** — honestly record what didn't work / wasn't verified; no success-washing (NASA's #1 barrier was fear of sharing negative lessons).
15. **Close the loop with tracked action items.**
16. **Written from system data, not memory** — SRE reconstructs timelines from logs; cite actual paths/commands/outputs.

### Failure modes

17. **Lessons-learned graveyard / write-only repository** — GAO-02-195 (2002) and the 2012 OIG follow-up found the same defect a decade apart.
18. **Closure theater / admin fizzle** — closeout skipped or rushed as attention jumps to the next project.
19. **Success claim without evidence.**
20. **Blame culture suppressing honesty** — sanitized, low-information records.
21. **Poor retrievability.**

### Verdict on disentangling (C's view)

22. **One skill, two explicit modes — not two separate skills, and not a single blurred template.** ~70% of content overlaps (artifact inventory, decisions+rationale, deviations, limitations, state); duplicating across two skills guarantees drift. But the frame differs on three axes: audience & tense (imperative-forward vs past-tense audit for a dual audience), verification & criteria load-bearing only at completion, resumption state (next action, blockers, scratch) only at continuation. The write-only-graveyard failure is completion-specific and demands completion-only countermeasures; baking them into every mid-work handoff would be clutter.

### Sources

22. **[Postmortem Culture: Learning from Failure](https://sre.google/sre-book/postmortem-culture/)** (Google SRE Book ch. 15; 2017) — postmortem contents + the usability machinery: pre-publication review, blameless framing.
23. **[NASA: Better Mechanisms Needed for Sharing Lessons Learned (GAO-02-195)](https://spaceref.com/status-report/gao-report-nasa-better-mechanisms-needed-for-sharing-lessons-learned-gao-02-195/)** (GAO report; 2002-02-05) — the definitive write-only-repository failure study.
24. **[Survey of NASA's Lessons Learned Process (GAO-01-1015R)](https://www.gao.gov/products/gao-01-1015r)** (GAO report; 2001) — lessons "not routinely identified, collected, or shared."
25. **[After-action review](https://en.wikipedia.org/wiki/After-action_review)** (Wikipedia; living doc) — the four canonical questions (planned / actual / why the difference / sustain-or-improve).
26. **[The Leader's Guide to After-Action Reviews](https://pinnacle-leaders.com/wp-content/uploads/2018/02/Leaders_Guide_to_AAR.pdf)** (US Army guide PDF; 2013-12) — AAR structure; descriptive-not-attributive stance.
27. **[End project report](https://prince2.wiki/management-products/end-project-report/)** + **[Lessons report](https://prince2.wiki/management-products/reports/lessons-report/)** (PRINCE2 wiki; living docs) — closure as accountability document; lessons report exists "to encourage action."
28. **[Turnover Package Checklist](https://satellitegroundstation.com/resources/turnover-package-checklist-docs-baselines-spares-runbooks/)** (industry guide; date unverified) — artifact-inventory model for transition-to-ops.
29. **[Definition of Done vs. Acceptance Criteria Explained](https://www.scrum.org/resources/blog/definition-done-vs-acceptance-criteria-explained)** (Scrum.org blog; date unverified) — "done" needs a verifiable bar.
30. **[Pragmatic reproducible research](https://pmc.ncbi.nlm.nih.gov/articles/PMC10425207/)** (PMC peer-reviewed; date unverified) — provenance sufficient to re-derive results (FAIR).
31. **[How Consultants Make Client Handoffs Stick After Project Close](https://consultantmagazine.co/qa/how-consultants-make-client-handoffs-stick-after-project-close/)** (interview/blog; date unverified) — dual-audience closeout; owner per deliverable; "the why behind key decisions."
