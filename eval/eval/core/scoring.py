"""Inline scorer: dynamic-import a task's grade.py and persist score.json.

The grader signature is `grade(submission_dir: Path) -> ScoreReport`. Exceptions
are caught and written as `{"score": null, "grader_error": "..."}`; the run
is not interrupted.
"""
from __future__ import annotations

import importlib.util
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from eval.core.tasks import Task, load_tasks


def _default(obj):
    """JSON serializer for numpy types that the default encoder can't handle."""
    try:
        import numpy as np
    except ImportError:
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _import_grader(task: Task):
    spec = importlib.util.spec_from_file_location(
        f"_grader_{task.task_id.replace('-', '_')}", task.grade_py
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {task.grade_py}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def failure_reason(task_state: dict) -> str | None:
    """Return a reason string if this task's session ended in failure, else None.

    A failed session scores 0 regardless of any partial outputs it produced
    before dying — an errored run is not a gradeable submission. This covers
    both currently-failed tasks (`status == "failed"`) and ones a targeted
    rerun relabeled to 'done' but tagged `last_event "done (preserved; was
    failed)"`.
    """
    if task_state.get("status") == "failed":
        return task_state.get("error") or task_state.get("last_event") or "session failed"
    if "preserved; was failed" in str(task_state.get("last_event") or ""):
        return "session failed (preserved)"
    return None


def score_task(task: Task, task_run_dir: Path, zero_reason: str | None = None) -> dict:
    """Grade one task's submission and write `score.json`. Returns the dict.

    When `zero_reason` is set the session failed: the grader still runs to
    record which outputs (if any) existed, but the final score is forced to 0.
    """
    outputs_dir = task_run_dir / "outputs"
    score_path = task_run_dir / "score.json"
    graded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        mod = _import_grader(task)
        report = mod.grade(outputs_dir)
        rep = report.to_dict()
        out = {
            "task_id": task.task_id,
            "graded_at": graded_at,
            "gates": [
                {"name": g["name"], "passed": g["passed"], "detail": g.get("reason", "")}
                for g in rep.get("gates", [])
            ],
            "score": rep.get("score"),
            "subchecks": [
                {
                    "name": s["name"],
                    "passed": s["passed"],
                    "axis": s.get("axis", ""),
                    "detail": s.get("detail", ""),
                    "weight": s.get("weight", 1.0),
                }
                for s in rep.get("subchecks", [])
            ],
            "grader_error": None,
        }
    except Exception:
        out = {
            "task_id": task.task_id,
            "graded_at": graded_at,
            "gates": [],
            "score": None,
            "subchecks": [],
            "grader_error": traceback.format_exc(),
        }

    if zero_reason is not None:
        out["graded_score"] = out["score"]
        out["score"] = 0.0
        out["zeroed"] = {"reason": zero_reason}

    score_path.write_text(json.dumps(out, indent=2, default=_default) + "\n")
    return out


def score_run(run_dir: Path) -> dict[str, dict]:
    """Re-grade every task in a run directory. Returns mapping task_id → score dict."""
    from eval.core.storage import RunStore

    store = RunStore.open(run_dir)
    tasks_by_id = {t.task_id: t for t in load_tasks()}
    out: dict[str, dict] = {}
    for task_id, task_state in store.state.get("tasks", {}).items():
        task = tasks_by_id.get(task_id)
        if task is None:
            continue
        task_run_dir = run_dir / task_id
        zero_reason = failure_reason(task_state)
        # Skip tasks that never ran; a failed task is always (re-)scored to 0.
        if not (task_run_dir / "outputs").exists() and zero_reason is None:
            continue
        scored = score_task(task, task_run_dir, zero_reason=zero_reason)
        out[task_id] = scored
        store.update_task(task_id, {"score": scored.get("score")})
    return out
