"""Run directory layout + atomic writes for run.json.

See eval-app-design.md "On-disk layout" and "run.json schema".
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = EVAL_ROOT / "runs"


def new_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return "run-" + now.strftime("%Y%m%d-%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data)
    os.replace(tmp, path)


class RunStore:
    """Owns the on-disk state for one run."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self._lock = threading.Lock()
        self._state: dict = {}

    @classmethod
    def create(cls, runs_root: Path, run_id: str, initial: dict) -> "RunStore":
        run_dir = runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        store = cls(run_dir)
        store._state = initial
        store._flush()
        return store

    @classmethod
    def open(cls, run_dir: Path) -> "RunStore":
        store = cls(run_dir)
        store._state = json.loads((run_dir / "run.json").read_text())
        return store

    @property
    def state(self) -> dict:
        return self._state

    @property
    def cancel_flag(self) -> Path:
        return self.run_dir / "cancel.flag"

    def task_dir(self, task_id: str) -> Path:
        d = self.run_dir / task_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def request_cancel(self) -> None:
        self.cancel_flag.write_text(utc_iso())

    def is_cancelled(self) -> bool:
        return self.cancel_flag.exists()

    def update(self, mutate) -> None:
        with self._lock:
            mutate(self._state)
            self._flush()

    def update_task(self, task_id: str, fields: dict) -> None:
        def _m(state: dict) -> None:
            state.setdefault("tasks", {}).setdefault(task_id, {}).update(fields)

        self.update(_m)

    def set_status(self, status: str, **fields) -> None:
        def _m(state: dict) -> None:
            state["status"] = status
            for k, v in fields.items():
                state[k] = v

        self.update(_m)

    def _flush(self) -> None:
        _atomic_write(
            self.run_dir / "run.json",
            json.dumps(self._state, indent=2, default=str) + "\n",
        )


def list_runs(runs_root: Path = RUNS_DIR) -> list[dict]:
    """Return all runs' state dicts, newest first by run_id."""
    if not runs_root.exists():
        return []
    out = []
    for d in sorted(runs_root.iterdir(), reverse=True):
        rj = d / "run.json"
        if rj.is_file():
            try:
                out.append(json.loads(rj.read_text()))
            except Exception:
                continue
    return out
