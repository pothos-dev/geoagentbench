# Authoring history — <task_id>

<!--
This file lives at `benchmark/tasks/<task_id>/audit/AUTHORING_HISTORY.md` and
records the full design + evaluation history of one task.

Two audiences write to it:

1. The **task-design (authoring) agent** writes the upper block (Status …
   Runtime).  `benchmark/authoring/orchestrator/notes.py` parses these
   H2 sections; do not rename them.

2. The **task-evaluator agent** appends an `## Evaluator review <date>` block
   per run.  See `benchmark/authoring/task-evaluator-prompt.md`.

If you regenerate the task (full re-author), overwrite the author block above
the `---` separator and leave evaluator review blocks below intact (they are
historical evidence of past calibration).
-->

## Status
<!-- one of: completed | completed-with-caveats | unsolvable -->

## Summary
<!-- 1–2 paragraphs: what the task tests, what input is given, what output
     is expected, what makes the task non-trivial -->

## Verification results
<!-- - Reference grader score: <score> (<n>/<m> subchecks)
     - Broken-solution scores:
       - <name>: <score> (expected range [<lo>, <hi>])
       - …
     - Second-run output match: <deterministic | non-deterministic, reason> -->

## Failure-mode coverage
<!-- bullet per failure mode the broken_* set is meant to catch, and how it
     is caught (which gate / subcheck) -->

## Open issues
<!-- - [low|med|high] — <one line> -->

## Suggested prompt changes
<!-- Proposals that the author thinks would improve the task but did not
     apply themselves; usually picked up later by the evaluator. -->

## Inventory change proposals
<!-- Proposed updates to `benchmark/authoring/inventory.md`, or "(applied —
     inventory.md updated)" if already merged. -->

## Library extensions
<!-- Any geo_grading additions made for this task, with rationale. -->

## Runtime
<!-- Wall-clock minutes the authoring run took, plus any timing notes. -->

---

# Evaluator review log

<!--
The task-evaluator agent appends one block per re-evaluation.  Most recent
run goes at the BOTTOM (chronological order).  Never edit prior blocks —
they are evidence of how the task looked at that point in time.

Template for one block:

## Evaluator review <ISO-date>  (evaluator-commit <sha-7>)

### 1. Design history

#### Initial design intent
<one paragraph reconstructed from inventory row + first commit + README at
first commit>

#### Change log
| Date | Commit | Class | What changed | Why |
|---|---|---|---|---|
| YYYY-MM-DD | abc1234 | initial-authoring | … | (initial) |
| YYYY-MM-DD | def5678 | grader-change | … | Commit msg: "…" |

### 2. Current-state review

#### Cutoff
- design-affecting cutoff: <ISO timestamp> (commit <sha>, class: <…>)

#### Runs considered
| Run | Adapter | Started | Score | Status | Validity |
|---|---|---|---|---|---|
| run-… | … | … | … | done | current |

#### Verdict
**<calibrated | too-strict | too-easy | prompt-grader-inconsistent | insufficient-evidence>**

<one paragraph reasoning>

#### Specific findings
- …

### 3. Changes applied this run

#### Unilateral edits
- <file>: <one-line>. Re-grade on reference: <score>. Reason: …

#### Proposed but not applied (HUMAN-REVIEW items)
- HR-001 — <category> — <one-line>

#### Tests run
- grader on reference: <score>
- pytest: <pass | fail with N failures>
-->
