"""Task discovery and metadata loading.

A task lives at `benchmark/tasks/<task_id>/` with at least:

    task.json              — instruction + inputs + expected_outputs
    grade.py               — defines `grade(submission_dir) -> ScoreReport`

Optional:
    metadata.yaml          — author-facing notes; not required by the runner
    visualize.py           — `visualize(outputs_dir, out_dir) -> list[layer_spec]`
    reference/solution/outputs/     — golden artefacts the grader reads
    reference/solution/visualizations/ — committed pmtiles + layers.json for the task page

Inputs `url` fields are repo-relative paths (e.g. `tasks/<id>/inputs/foo.gpkg`),
resolved against `BENCHMARK_ROOT` (the parent of `tasks/`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent.parent  # benchmark/eval
BENCHMARK_ROOT = EVAL_ROOT.parent  # benchmark/
TASKS_DIR = BENCHMARK_ROOT / "tasks"


@dataclass
class TaskInput:
    name: str
    url: str
    format: str | None = None

    @property
    def path(self) -> Path:
        """Resolve the input's repo-relative URL against benchmark/."""
        return (BENCHMARK_ROOT / self.url).resolve()


@dataclass
class TaskExpectedOutput:
    name: str
    format: str | None = None
    crs: str | None = None
    geometry_type: str | None = None
    layers: list[str] | None = None


@dataclass
class Task:
    task_id: str
    instruction: str
    inputs: list[TaskInput]
    expected_outputs: list[TaskExpectedOutput]
    deadline_seconds: int | None = None
    tags: dict[str, list[str] | str] = field(default_factory=dict)
    # Content fingerprint — bumped by the evaluator (or author) on any
    # meaningful change to prompt/grader/inputs. Tasks predating the field
    # are implicitly v1; runs predating the field are recorded as v0 and
    # rendered as outdated. See benchmark/authoring/task-evaluator-prompt.md.
    version: int = 1
    # Optional analyst-authored notes (description + approach + pitfalls).
    # Shape: {"description": str, "approach": list[str], "pitfalls": list[str]}.
    # Any subset of keys may be present; absence means "do not render".
    analyst_notes: dict | None = None
    # Render the run-task map view with MapLibre globe projection instead of
    # the default Web Mercator. Useful for polar / hemispheric tasks where
    # Mercator distortion makes the result unreadable.
    viz_globe: bool = False
    dir: Path = field(default_factory=Path)

    @property
    def grade_py(self) -> Path:
        return self.dir / "grade.py"

    @property
    def visualize_py(self) -> Path:
        return self.dir / "visualize.py"

    @property
    def reference_visualizations_dir(self) -> Path:
        return self.dir / "reference" / "solution" / "visualizations"


def _load(task_dir: Path) -> Task:
    raw = json.loads((task_dir / "task.json").read_text())
    return Task(
        task_id=raw["task_id"],
        instruction=raw["instruction"],
        inputs=[TaskInput(**i) for i in raw.get("inputs", [])],
        expected_outputs=[
            TaskExpectedOutput(**o) for o in raw.get("expected_outputs", [])
        ],
        deadline_seconds=raw.get("deadline_seconds"),
        tags=raw.get("tags", {}),
        version=int(raw.get("version", 1)),
        analyst_notes=raw.get("analyst_notes"),
        viz_globe=bool(raw.get("viz_globe", False)),
        dir=task_dir,
    )


def load_task(task_id: str, tasks_dir: Path = TASKS_DIR) -> Task:
    return _load(tasks_dir / task_id)


def load_tasks(tasks_dir: Path = TASKS_DIR) -> list[Task]:
    out: list[Task] = []
    if not tasks_dir.exists():
        return out
    for d in sorted(tasks_dir.iterdir()):
        if d.is_dir() and (d / "task.json").is_file():
            out.append(_load(d))
    return out


def filter_tasks(tasks: list[Task], filters: list[str] | None) -> list[Task]:
    """Filter by task_id prefix or glob. Empty/None returns all."""
    if not filters:
        return tasks
    import fnmatch

    matched: list[Task] = []
    for t in tasks:
        if any(fnmatch.fnmatch(t.task_id, f) or t.task_id.startswith(f) for f in filters):
            matched.append(t)
    return matched
