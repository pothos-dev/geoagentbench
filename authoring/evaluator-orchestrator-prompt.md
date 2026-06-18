# Evaluator-orchestrator prompt

Use this as the initial prompt for a Claude Code session that will sweep the task-evaluator agent across every task in `benchmark/tasks/`. The session is expected to run unattended (AFK).

---

## Your role

You are an orchestrator. You do **not** evaluate tasks yourself. For each task slug, you spawn a fresh evaluator subagent and act on its status hand-off.

Per task you do exactly three things:

1. Spawn the evaluator subagent (one subagent per task; new context each time).
2. Read the resulting `benchmark/tasks/<slug>/audit/status.json`.
3. Decide whether to continue, pause, or stop the sweep based on that status.

The evaluator commits its own artefacts. You do not commit anything.

---

## Inputs

- `benchmark/authoring/task-evaluator-prompt.md` — the full agent prompt for one task. Pass this verbatim to each subagent, prepended with a `## Task` block (see below).
- `benchmark/tasks/` — the 36 tasks. Enumerate at start; iterate in lexicographic order. Skip nothing.

Take a clean working tree as precondition. Run `git status --short`; if the tree is dirty in `benchmark/`, stop and tell the user.

---

## Per-task loop

For each `<slug>`:

1. Verify a clean working tree (`git status --short benchmark/tasks/<slug>/` empty). If dirty, stop the sweep with reason `dirty-tree-before-<slug>`.

2. Spawn an evaluator subagent. Use the `Agent` tool with `subagent_type: general-purpose` (no worktree isolation; the evaluator works directly in the main checkout). The prompt is:

   ```
   ## Task
   - task_id: <slug>
   - worktree_root: <absolute path to repo root>

   <full contents of benchmark/authoring/task-evaluator-prompt.md verbatim>
   ```

   Tell the subagent: it must commit its own artefacts before returning. It returns a one-line summary (the orchestrator does not read the full transcript).

3. After the subagent returns, read `benchmark/tasks/<slug>/audit/status.json`. Branch:

   - `status: "completed"` and no `human_review_items` → log "✅ <slug>: <verdict>" and continue.
   - `status: "completed-with-flags"` (one or more `human_review_items`, all `severity` `low`/`med`) → log "⚠️ <slug>: <verdict> (<n> flags)" and continue.
   - Any `human_review_items[].severity == "high"` → log "🛑 <slug>: high-severity flag" and **stop the sweep**.
   - `status: "blocked"` → log "🛑 <slug>: blocked — <blocker>" and **stop the sweep**.
   - Missing or malformed `status.json` → log "🛑 <slug>: evaluator produced no status.json" and **stop the sweep**.

4. Verify the evaluator actually committed. Run `git log -1 --format='%H %s'` and confirm the message starts with `Re-evaluate <slug>:`. If no such commit exists, stop with reason `evaluator-did-not-commit-<slug>`.

Do **not** alter, amend, or revert the evaluator's commits. If you disagree with one, log it and let the human handle it.

---

## Sweep-level rules

- **Order**: lexicographic by `<slug>`. Do not parallelise. The thesis-coverage matrix is built from these artefacts in order; deterministic order helps reproducibility.
- **No interactive prompts**: never ask the user mid-sweep. Decide from `status.json` alone.
- **Stop conditions**: any `blocked`, any `severity: high`, any missing commit, dirty working tree, or a subagent that exits without producing artefacts. On any stop condition, write the morning summary up to and including the stopping task, then exit cleanly.
- **No retries**: a task either succeeds or it stops the sweep. Retrying inside the loop hides systemic problems.

---

## Final morning summary

When the sweep finishes (clean or stopped), write `benchmark/authoring/runs/evaluator-sweep-<YYYY-MM-DD>/morning-summary.md`:

```markdown
# Evaluator sweep — <YYYY-MM-DD>

- start: <ISO timestamp>
- end: <ISO timestamp>
- result: <completed | stopped-at-<slug>>
- stop reason (if stopped): <one line>

## Per-task results
| Slug | Verdict | Flags | Commit |
|---|---|---|---|
| <slug> | calibrated | 0 | <sha-7> |
| <slug> | too-strict | 2 (1 med, 1 low) | <sha-7> |
| <slug> | — | — | (skipped — sweep stopped earlier) |

## Aggregate
- calibrated:    <n>
- too-strict:    <n>
- too-easy:      <n>
- prompt-grader-inconsistent: <n>
- insufficient-evidence: <n>
- blocked:       <n>

## Human-review queue
| Slug | HR-ID | Category | Severity | One-line |
|---|---|---|---|---|
| <slug> | HR-001 | design-rationale | low | <…> |
```

Stage and commit the morning summary as a single trailing commit:

```
git add benchmark/authoring/runs/evaluator-sweep-<date>/morning-summary.md
git commit -m "Evaluator sweep <date>: <n>/<36> tasks reviewed"
```

Then exit. Do not push.

---

## What you must NOT do

- Evaluate tasks yourself. Always delegate to a fresh subagent.
- Read run transcripts, grader outputs, or task internals.
- Edit any file under `benchmark/tasks/` directly.
- Push, force-push, amend, rebase, or skip hooks.
- Continue past a `blocked` or `severity: high` flag.
- Run the eval harness or kick off new model runs. The evaluator uses existing runs only.

---

## How to run code

From the repo root:

```bash
git status --short benchmark/tasks/<slug>/
git log -1 --format='%H %s'
cat benchmark/tasks/<slug>/audit/status.json
```

No other tooling is needed at the orchestrator level. The evaluator subagent runs grader + pytest itself.
