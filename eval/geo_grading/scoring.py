"""Structured scoring types returned by per-task graders.

A `ScoreReport` is the canonical return of every `tasks/<slug>/grade.py`
entrypoint. The harness consumes these to build `runs/<id>/results.json`.

Scoring model:
- A grader has exactly one hard gate (``format_schema_valid``). Failing
  it collapses the score to 0 — the output is unparseable / unreadable
  / unrecoverable, so no subcheck can produce a meaningful signal.
- Everything else is a binary `Subcheck`. The task score is
  `passed / total` across all subchecks. Anything that can be recovered
  by light coercion (cast a string to int, treat ``None`` as WGS84, …)
  becomes a subcheck rather than gating downstream comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class Gate:
    """A binary hard gate. Failing collapses the task score to 0.

    Use a gate only when the output is unrecoverable for grading — file
    missing, file unparseable, top-level structure that cannot be cast or
    coerced into the comparable shape. Anything that can still be
    compared (a value of the wrong type that we can cast, an extra row, a
    near-miss count) belongs in a `Subcheck`, where it costs one point
    instead of collapsing the score.
    """

    name: str
    passed: bool
    reason: str = ""


@dataclass
class Subcheck:
    """A binary subcheck contributing `weight` to the score budget.

    The task score is ``sum(weight where passed) / sum(weight)``.
    Conventionally, schema/structural checks (CRS declared, column
    types, coordinate envelope) use ``weight=1.0`` and data-content
    checks (feature counts, IoU, attribute matches, checksums) use
    ``weight=3.0`` so a schema-clean but data-wrong submission scores
    distinctly below a data-correct one.
    """

    name: str
    passed: bool
    detail: str = ""
    weight: float = 1.0


@dataclass
class ScoreReport:
    """Per-task grading result.

    `score` is `passed_subchecks / total_subchecks` across all subchecks
    when all gates pass; 0.0 if any gate fails.
    """

    task_id: str
    gates: list[Gate] = field(default_factory=list)
    subchecks: list[Subcheck] = field(default_factory=list)

    @property
    def gates_passed(self) -> bool:
        return all(g.passed for g in self.gates)

    @property
    def hard_gate_failed(self) -> bool:
        """Any failed gate collapses the score to 0 — all gates are hard."""
        return any(not g.passed for g in self.gates)

    @property
    def score(self) -> float:
        if self.hard_gate_failed:
            return 0.0
        if not self.subchecks:
            return 1.0 if self.gates_passed else 0.0
        total_weight = sum(s.weight for s in self.subchecks)
        if total_weight <= 0:
            return 1.0 if self.gates_passed else 0.0
        earned = sum(s.weight for s in self.subchecks if s.passed)
        return earned / total_weight

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.subchecks if s.passed)

    @property
    def total_count(self) -> int:
        return len(self.subchecks)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "score": self.score,
            "gates_passed": self.gates_passed,
            "gates": [
                {"name": g.name, "passed": g.passed, "reason": g.reason}
                for g in self.gates
            ],
            "subchecks": [
                {
                    "name": s.name,
                    "passed": s.passed,
                    "detail": s.detail,
                    "weight": s.weight,
                }
                for s in self.subchecks
            ],
            "passed_count": self.passed_count,
            "total_count": self.total_count,
        }
