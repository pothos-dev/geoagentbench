# Orchestrator-judgment prompt (circuit-break only)

Invoked when the per-task orchestrator detects a systemic failure pattern: 3 consecutive `unsolvable` results, or 4 of the last 5 tasks share a clustered root cause. Your job is to read the failed run's implementation notes, decide whether the failures share a single fixable prompt-level cause, and if so produce a revised task-design prompt for the next overnight run.

You do **not** restart the run yourself — the orchestrator does that after committing your prompt revision. You write the revised prompt to disk and a one-page rationale; the orchestrator handles git and re-spawning.

---

## Inputs you receive

The per-task orchestrator hands you:

- `runs/<run-id>/morning-summary.md` — aggregated status across the failed run.
- `tasks/<slug>/IMPLEMENTATION_NOTES.md` for every task that ran (completed, caveated, or unsolvable).
- `tasks/_blocked/<slug>.md` for any unsolvable tasks.
- `authoring/task-design-prompt.md` — the prompt that produced the failed run.
- The current run's branch name.

---

## Workflow

1. **Read all `IMPLEMENTATION_NOTES.md` files from this run.** Look for the `Open issues` and `Suggested prompt changes` sections especially. Cluster issues by root cause.

2. **Decide: is the pattern fixable at the prompt level?**
   - **Yes** — the same underlying ambiguity / missing-instruction / wrong-default appears across multiple tasks. Continue to step 3.
   - **No** — the failures are task-specific (each had its own unrelated reason). Write `runs/<run-id>/judgment.md` with this finding, recommend manual review of the affected tasks, and exit. Do not revise the prompt.

3. **Draft the revised prompt.** Edit `authoring/task-design-prompt.md` to address the clustered root cause. Rules:
   - Make the **smallest possible change** that addresses the root cause. Sweeping rewrites lose the prompt's coherence.
   - Preserve all section headers and the workflow numbering. Add to sections; don't reshuffle them.
   - If you add a new requirement (e.g. an extra acceptance check), ensure it's testable — don't add prose the next agent can ignore.

4. **Write `runs/<run-id>/prompt-revision-rationale.md`.** Sections:
   - **Failure pattern observed.** What clustered across the failed tasks.
   - **Root cause hypothesis.** What in the original prompt led to that pattern.
   - **Fix applied.** Exact diff against the prior prompt (paste the unified diff).
   - **Expected effect.** Which acceptance criteria the revised prompt makes more likely to pass.
   - **Risks.** What this change might break in tasks that *were* working.

5. **Stop.** Do not start the next run. Do not delete prior task work — the orchestrator tags the failed branch and starts a fresh one.

---

## Hard rules

- **Maximum 1 restart per overnight session.** If the next run also trips the circuit breaker, the orchestrator pauses for human review without invoking you again.
- **Do not edit `authoring/inventory.md`, `authoring/author-context.md`, or `eval/geo_grading/`.** The prompt is the only authoring surface you may change.
- **Do not commit.** The orchestrator commits your prompt revision plus the rationale file in one atomic commit before starting the new run.
- **Bias toward "no, it's task-specific."** Restarting is expensive and the validity of the run as a research artefact depends on prompt coherence. Restart only if the cluster is unambiguous.

---

## Output

When you finish, the working tree contains:

- `authoring/task-design-prompt.md` (edited if you decided to restart) or unchanged (if not).
- `runs/<run-id>/judgment.md` (your decision rationale, always written).
- `runs/<run-id>/prompt-revision-rationale.md` (only if you revised the prompt).

The orchestrator inspects these files to decide whether to restart and, if so, on which branch.
