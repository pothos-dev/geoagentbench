"""eval CLI: `eval run`, `eval score`, `eval ui`.

Run lifecycle: submit, poll, download, grade inline. One CLI call → one run.
Repetition / matrix studies are external scripting; this CLI doesn't loop.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
from pathlib import Path

from eval.core.adapters import get_adapter, load_adapters
from eval.core.runner import (
    AdapterTarget,
    RunSpec,
    is_rerunnable,
    run as run_run,
    resume as resume_run,
)
from eval.core.scoring import score_run
from eval.core.storage import RUNS_DIR


def _cmd_run(args: argparse.Namespace) -> int:
    if args.agent_url:
        adapter = AdapterTarget(url=args.agent_url, name=None, label=args.agent_url)
    elif args.adapter:
        adapter = get_adapter(args.adapter)
    else:
        print("error: either <adapter> or --agent-url must be given", file=sys.stderr)
        return 2

    spec = RunSpec(
        adapter=adapter,
        task_filter=args.tasks or None,
        max_parallel=args.max_parallel,
        label=args.label,
    )

    # SIGINT → drop a cancel.flag into any run dir created after we started,
    # so the in-flight runner picks it up at the next poll cycle.
    import os
    import time

    pre_existing = set(os.listdir(RUNS_DIR)) if RUNS_DIR.exists() else set()

    def _on_sigint(_sig, _frame):
        if not RUNS_DIR.exists():
            return
        for name in os.listdir(RUNS_DIR):
            if name not in pre_existing:
                (RUNS_DIR / name / "cancel.flag").write_text("")
        print("\ncancel requested — finishing in-flight tasks…", file=sys.stderr)

    signal.signal(signal.SIGINT, _on_sigint)

    run_dir = run_run(spec, RUNS_DIR)
    print(f"run complete: {run_dir}")
    return 0


def _resolve_run_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_dir():
        return p
    candidate = RUNS_DIR / arg
    if candidate.is_dir():
        return candidate
    raise SystemExit(f"run not found: {arg}")


def _cmd_resume(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run)
    state = json.loads((run_dir / "run.json").read_text())
    incomplete = [
        tid for tid, t in state.get("tasks", {}).items()
        if is_rerunnable(t)
    ]
    if not incomplete:
        print("nothing to resume — all tasks already done")
        return 0
    print(f"resuming {len(incomplete)} incomplete task(s) in {run_dir.name}")
    resume_run(run_dir, max_parallel=args.max_parallel)
    print(f"resume complete: {run_dir}")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    run_dir = _resolve_run_dir(args.run)
    results = score_run(run_dir)
    for task_id, r in results.items():
        score = r.get("score")
        print(f"  {task_id}: {score}")
    print(f"re-scored {len(results)} task(s) in {run_dir}")
    return 0


def _cmd_ui(args: argparse.Namespace) -> int:
    import uvicorn

    from eval.ui.app import create_app

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _cmd_visualize(args: argparse.Namespace) -> int:
    from eval.core.tasks import filter_tasks, load_tasks
    from eval.core.viz import generate_layers

    tasks = filter_tasks(load_tasks(), args.tasks or None)
    n_ok = n_err = n_skip = 0
    for task in tasks:
        if not task.visualize_py.is_file():
            n_skip += 1
            continue
        outputs = task.dir / "reference" / "solution" / "outputs"
        out_dir = task.reference_visualizations_dir
        if not outputs.is_dir() or not any(outputs.iterdir()):
            print(f"  {task.task_id}: skip (no reference outputs)")
            n_skip += 1
            continue
        manifest = generate_layers(task.visualize_py, outputs, out_dir)
        if manifest["error"]:
            n_err += 1
            print(f"  {task.task_id}: ERROR")
            print(manifest["error"].rstrip())
        else:
            n_ok += 1
            print(f"  {task.task_id}: {len(manifest['layers'])} layer(s)")
    print(f"visualized {n_ok} task(s), {n_err} error(s), {n_skip} skipped")
    return 0 if n_err == 0 else 1


def _cmd_adapters(_args: argparse.Namespace) -> int:
    for name, a in load_adapters().items():
        print(f"{name}\t{a.url}\t{a.label or ''}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="eval")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="submit a task or task set to an adapter")
    pr.add_argument("adapter", nargs="?", help="adapter name from adapters.yaml")
    pr.add_argument("--agent-url", help="ad-hoc adapter base URL (no config entry)")
    pr.add_argument(
        "--tasks", nargs="*", default=None, help="task_id prefixes or glob patterns"
    )
    pr.add_argument("--max-parallel", type=int, default=None)
    pr.add_argument("--label", default=None, help="free-form run label")
    pr.set_defaults(func=_cmd_run)

    presume = sub.add_parser("resume", help="resume incomplete tasks in an interrupted run")
    presume.add_argument("run", help="run id (e.g. run-20260511-1430Z) or directory")
    presume.add_argument("--max-parallel", type=int, default=None)
    presume.set_defaults(func=_cmd_resume)

    ps = sub.add_parser("score", help="re-grade all tasks in an existing run")
    ps.add_argument("run", help="run id (e.g. run-20260511-1430Z) or directory")
    ps.set_defaults(func=_cmd_score)

    pu = sub.add_parser("ui", help="start the Starlette browse/launch UI")
    pu.add_argument("--host", default="127.0.0.1")
    pu.add_argument("--port", type=int, default=8765)
    pu.set_defaults(func=_cmd_ui)

    pv = sub.add_parser(
        "visualize",
        help="generate reference visualizations from each task's reference/solution/outputs",
    )
    pv.add_argument(
        "--tasks", nargs="*", default=None, help="task_id prefixes or glob patterns"
    )
    pv.set_defaults(func=_cmd_visualize)

    pa = sub.add_parser("adapters", help="list configured adapters")
    pa.set_defaults(func=_cmd_adapters)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
