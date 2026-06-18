"""Smoke tests for the eval package: import surface + storage primitives."""
from __future__ import annotations

import json
from pathlib import Path

from eval.core import (
    AdapterTarget,
    RunSpec,
    load_tasks,
    new_run_id,
)
from eval.core.runner import is_max_iterations_error, is_rerunnable
from eval.core.storage import RunStore


def test_is_max_iterations_error():
    assert is_max_iterations_error("RuntimeError: max iterations exceeded (75)")
    assert not is_max_iterations_error("JSONDecodeError: Expecting value")
    assert not is_max_iterations_error("RuntimeError: session stalled for 600s")
    assert not is_max_iterations_error(None)
    assert not is_max_iterations_error("")


def test_is_rerunnable_skips_max_iterations():
    # infra failures and other incomplete states are rerunnable
    assert is_rerunnable({"status": "failed", "error": "ConnectTimeout"})
    assert is_rerunnable({"status": "pending"})
    assert is_rerunnable({"status": "cancelled"})
    # a genuine max-iterations failure is left alone
    assert not is_rerunnable({"status": "failed", "max_iterations_reached": True})
    # done tasks are never rerun
    assert not is_rerunnable({"status": "done"})


def test_imports_and_run_id():
    assert new_run_id().startswith("run-")
    spec = RunSpec(adapter=AdapterTarget(url="http://x"), task_filter=None)
    assert spec.adapter.url == "http://x"
    # load_tasks must not crash even with an empty suite
    assert isinstance(load_tasks(), list)


def test_run_store_atomic_write(tmp_path: Path):
    state = {
        "run_id": "run-test",
        "status": "running",
        "tasks": {"a": {"status": "pending"}},
    }
    s = RunStore.create(tmp_path, "run-test", state)
    assert (s.run_dir / "run.json").is_file()
    s.update_task("a", {"status": "running", "last_event": "go"})
    reloaded = json.loads((s.run_dir / "run.json").read_text())
    assert reloaded["tasks"]["a"]["last_event"] == "go"

    s.set_status("done", finished_at="2026-05-11T15:00:00Z")
    reloaded = json.loads((s.run_dir / "run.json").read_text())
    assert reloaded["status"] == "done"
    assert reloaded["finished_at"] == "2026-05-11T15:00:00Z"


def test_cancel_flag(tmp_path: Path):
    s = RunStore.create(tmp_path, "run-test", {"run_id": "run-test", "tasks": {}})
    assert not s.is_cancelled()
    s.request_cancel()
    assert s.is_cancelled()
