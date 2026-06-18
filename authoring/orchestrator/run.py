"""Overnight task-authoring orchestrator.

Spawns a Claude Code agent for each task in `authoring/inventory.md`,
in L1 → L2 → L3 order. Reads the agent's `audit/AUTHORING_HISTORY.md`,
commits the result on a per-run branch, and decides whether to
advance, log a caveat, or trip the circuit breaker.

Catastrophic conditions (pause for human):
- `pytest` fails after a task run.
- ≥ 3 consecutive `unsolvable`.
- 4 of last 5 tasks share a clustered root cause (LLM-judged at
  circuit-break time; we approximate here by counting consecutive
  `completed-with-caveats` with high-severity issues).
- Network / API infrastructure failure.

Run from `benchmark/authoring/` (the orchestrator package root):

    cd benchmark/authoring
    uv run python -m orchestrator.run \
        --max-tasks 36 \
        --per-task-timeout-min 60

Paths default to `<benchmark>/authoring/inventory.md` and
`<benchmark>/authoring/task-design-prompt.md`. The agent CWD
is `<benchmark>/`, so prompts reference `authoring/...` and
`tasks/...`.

Add `--dry-run` to print the planned task order without spawning agents.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from orchestrator.inventory import TaskRecord, order_tasks, parse_inventory
from orchestrator.notes import Notes, parse_notes


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUTHORING_DIR = REPO_ROOT / "authoring"
EVAL_DIR = REPO_ROOT / "eval"
TASKS_DIR = REPO_ROOT / "tasks"
USAGE_CACHE_PATH = Path("/tmp/claude-statusline-usage-cache.json")
TOKEN_BUDGET_HALT_PCT = 90  # halt if 5h-window utilization >= this (i.e. <10% remaining)


@dataclass
class RunState:
    run_id: str
    branch: str
    source_branch: str
    runs_dir: Path
    consecutive_unsolvable: int = 0
    recent_high_severity: int = 0
    completed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    stop_requested: bool = False


def main() -> int:
    args = _parse_args()
    if args.dry_run:
        records = order_tasks(parse_inventory(args.inventory))
        for r in records[: args.max_tasks]:
            print(f"{r.difficulty}\t{r.category}\t{r.slug}")
        return 0

    state = _setup_run(args)
    print(f"[orchestrator] run_id={state.run_id} branch={state.branch}")
    print("[orchestrator] press Enter at any time to stop after the current task")
    threading.Thread(
        target=_watch_stdin_for_stop, args=(state,), daemon=True
    ).start()

    records = order_tasks(parse_inventory(args.inventory))[: args.max_tasks]
    print(f"[orchestrator] scheduling {len(records)} task(s)")

    halted = False
    for record in records:
        if not _should_continue(state):
            halted = True
            break
        _run_one(state, record, args)

    _write_summary(state, records, halted=halted)
    _merge_back(state)
    return 2 if halted else 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", type=Path, default=AUTHORING_DIR / "inventory.md")
    p.add_argument(
        "--prompt", type=Path, default=AUTHORING_DIR / "task-design-prompt.md"
    )
    p.add_argument("--max-tasks", type=int, default=36)
    p.add_argument("--per-task-timeout-min", type=int, default=60)
    p.add_argument(
        "--claude-bin",
        default="claude",
        help="Path to the claude CLI; default 'claude' on PATH",
    )
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def _setup_run(args: argparse.Namespace) -> RunState:
    today = dt.date.today().isoformat()
    suffix = "a"
    while _branch_exists(f"tasks-run-{today}-{suffix}"):
        suffix = chr(ord(suffix) + 1)
    branch = f"tasks-run-{today}-{suffix}"
    run_id = branch

    runs_dir = AUTHORING_DIR / "runs" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    if _is_git_repo():
        source_branch = _current_branch() or "main"
        _git("checkout", "-b", branch)
    else:
        print("[orchestrator] not a git repo — skipping branch creation")
        source_branch = "main"

    return RunState(
        run_id=run_id, branch=branch, source_branch=source_branch, runs_dir=runs_dir
    )


def _run_one(state: RunState, record: TaskRecord, args: argparse.Namespace) -> None:
    print(f"\n[orchestrator] === {record.slug} [{record.difficulty}] ===")
    task_dir = TASKS_DIR / record.slug
    notes_path = task_dir / "audit/AUTHORING_HISTORY.md"
    if notes_path.exists():
        existing = parse_notes(notes_path, record.slug)
        if existing.status != "unknown":
            print(
                f"[orchestrator] {record.slug} already finished "
                f"({existing.status}) — skipping"
            )
            return
    util = _five_hour_utilization()
    if util is not None:
        print(f"[orchestrator] 5h utilization: {util:.0f}%")
    task_dir.mkdir(parents=True, exist_ok=True)
    prompt = _build_prompt(record, args)

    try:
        rc = _spawn_agent(prompt, args, timeout_s=args.per_task_timeout_min * 60)
    except subprocess.TimeoutExpired:
        print(f"[orchestrator] {record.slug} timed out after {args.per_task_timeout_min} min")
        rc = -1

    notes = parse_notes(notes_path, record.slug)

    if rc == -1 or notes.status == "unknown":
        _record_blocked(state, record, "agent did not produce audit/AUTHORING_HISTORY.md")
        return

    if notes.status == "unsolvable":
        _record_blocked(state, record, notes.summary)
        return

    state.consecutive_unsolvable = 0

    pytest_ok = _run_pytest()
    if not pytest_ok:
        sys.exit(
            f"[orchestrator] FATAL: pytest failed after {record.slug}; "
            "library regression — pause for human review."
        )

    if notes.status == "completed":
        _commit_task(record, "completed")
        state.completed.append(record.slug)
        state.recent_high_severity = 0
    else:  # completed-with-caveats
        _commit_task(record, "completed-with-caveats")
        state.completed.append(record.slug)
        state.caveats.append(record.slug)
        if notes.has_high_severity:
            state.recent_high_severity += 1
        else:
            state.recent_high_severity = 0


def _build_prompt(record: TaskRecord, args: argparse.Namespace) -> str:
    static = args.prompt.read_text(encoding="utf-8")
    header = (
        "## Task\n\n"
        f"- task_id: `{record.slug}`\n"
        "\n"
        "### Inventory row (verbatim)\n\n"
        f"{record.block}\n\n"
        "---\n\n"
    )
    return header + static


def _spawn_agent(prompt: str, args: argparse.Namespace, timeout_s: int) -> int:
    """Invoke the Claude Code CLI in non-interactive print mode.

    Uses --output-format stream-json so we can read events as they
    arrive and pretty-print tool calls / messages live. Without this,
    `claude -p` only prints the final response after the agent finishes.
    """
    cmd = [
        args.claude_bin,
        "-p",
        prompt,
        "--verbose",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--permission-mode",
        "bypassPermissions",
    ]
    print(
        "[orchestrator] spawning: "
        f"{args.claude_bin} -p <prompt> --verbose "
        "--output-format stream-json --permission-mode bypassPermissions"
    )
    print("[orchestrator] ──────── agent output begins ────────", flush=True)
    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    deadline = time.monotonic() + timeout_s
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            _pretty_print_event(line)
            if time.monotonic() > deadline:
                proc.kill()
                raise subprocess.TimeoutExpired(cmd, timeout_s)
    finally:
        rc = proc.wait()
    print(f"[orchestrator] ──────── agent output ends (rc={rc}) ────────", flush=True)
    return rc


def _pretty_print_event(line: str) -> None:
    """Parse a single stream-json line and print a human-readable summary."""
    line = line.strip()
    if not line:
        return
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        # Not JSON — pass through verbatim (probably stderr noise from claude itself)
        print(line, flush=True)
        return

    et = event.get("type")
    if et == "system":
        subtype = event.get("subtype")
        if subtype == "init":
            tools = event.get("tools", [])
            print(f"[claude] init — tools: {len(tools)}, model: {event.get('model', '?')}", flush=True)
    elif et == "assistant":
        message = event.get("message", {})
        for block in message.get("content", []):
            bt = block.get("type")
            if bt == "text":
                text = block.get("text", "").strip()
                if text:
                    print(text, flush=True)
            elif bt == "tool_use":
                tool = block.get("name", "?")
                summary = _summarize_tool_input(tool, block.get("input", {}))
                print(f"  → {tool}({summary})", flush=True)
            elif bt == "thinking":
                snippet = block.get("thinking", "").strip().split("\n", 1)[0]
                if snippet:
                    print(f"  · thinking: {snippet[:120]}", flush=True)
    elif et == "user":
        message = event.get("message", {})
        for block in message.get("content", []):
            if block.get("type") == "tool_result":
                content = block.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                content = str(content).replace("\n", " ").strip()
                if len(content) > 160:
                    content = content[:160] + "…"
                if content:
                    print(f"  ← {content}", flush=True)
    elif et == "result":
        is_error = event.get("is_error", False)
        if is_error:
            print(f"[claude] result: ERROR {event.get('subtype', '')}", flush=True)
        else:
            duration = event.get("duration_ms", 0) / 1000
            cost = event.get("total_cost_usd", 0)
            print(
                f"[claude] result: ok ({duration:.1f}s, ${cost:.4f})",
                flush=True,
            )
    # stream_event partial deltas are noisy; skip them
    # (the complete assistant message lands as type=assistant when done)


def _summarize_tool_input(tool: str, inp: dict) -> str:
    """Pick the most informative field of a tool's input for one-line display."""
    if tool in {"Read", "Write", "Edit"}:
        return str(inp.get("file_path", ""))
    if tool == "Bash":
        cmd = str(inp.get("command", ""))
        return cmd[:100] + ("…" if len(cmd) > 100 else "")
    if tool in {"Glob", "Grep"}:
        return str(inp.get("pattern", ""))
    if tool == "WebFetch":
        return str(inp.get("url", ""))
    if tool == "Task":
        return str(inp.get("description", ""))[:80]
    keys = ("path", "url", "name", "query", "command", "file_path")
    for k in keys:
        if k in inp:
            return f"{k}={str(inp[k])[:80]}"
    return ""


def _run_pytest() -> bool:
    proc = subprocess.run(
        ["uv", "run", "pytest"],
        cwd=EVAL_DIR,
    )
    return proc.returncode == 0


def _commit_task(record: TaskRecord, status_tag: str) -> None:
    if not _is_git_repo():
        return
    _git("add", "tasks", "eval/geo_grading", "eval/tests")
    msg = f"task: {record.slug} [{status_tag}]"
    _git("commit", "-m", msg, allow_empty=True)


def _record_blocked(state: RunState, record: TaskRecord, reason: str) -> None:
    blocked_dir = TASKS_DIR / "_blocked"
    blocked_dir.mkdir(exist_ok=True)
    (blocked_dir / f"{record.slug}.md").write_text(
        f"# Blocked: {record.slug}\n\n"
        f"Difficulty: {record.difficulty}\n"
        f"Reason: {reason}\n\n"
        f"Run: {state.run_id}\n",
        encoding="utf-8",
    )
    state.consecutive_unsolvable += 1
    state.blocked.append(record.slug)
    print(f"[orchestrator] {record.slug} blocked ({reason})")


def _should_continue(state: RunState) -> bool:
    if state.stop_requested:
        print("[orchestrator] STOP: user-requested halt after current task")
        return False
    if state.consecutive_unsolvable >= 3:
        print("[orchestrator] CIRCUIT BREAK: 3 consecutive unsolvable tasks")
        return False
    if state.recent_high_severity >= 4:
        print("[orchestrator] CIRCUIT BREAK: 4+ recent high-severity caveats")
        return False
    util = _five_hour_utilization()
    if util is not None and util >= TOKEN_BUDGET_HALT_PCT:
        print(
            f"[orchestrator] STOP: 5h window utilization {util:.0f}% "
            f"(>= {TOKEN_BUDGET_HALT_PCT}%) — less than "
            f"{100 - TOKEN_BUDGET_HALT_PCT}% budget remaining"
        )
        return False
    return True


def _five_hour_utilization() -> float | None:
    """Read the statusline cache; return current 5h-window utilization (percent).

    Returns None if the cache is missing or malformed — caller should treat
    that as "unknown, don't halt on budget grounds".
    """
    try:
        data = json.loads(USAGE_CACHE_PATH.read_text(encoding="utf-8"))
        return float(data["five_hour"]["utilization"])
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _watch_stdin_for_stop(state: RunState) -> None:
    """Background thread: any line on stdin requests a graceful halt."""
    try:
        for _ in sys.stdin:
            if not state.stop_requested:
                state.stop_requested = True
                print(
                    "[orchestrator] stop requested — will halt after the "
                    "current task completes",
                    flush=True,
                )
    except Exception:
        pass


def _write_summary(
    state: RunState, records: list[TaskRecord], halted: bool
) -> None:
    summary_path = state.runs_dir / "morning-summary.md"
    lines = [
        f"# Morning summary — {state.run_id}",
        "",
        f"Branch: `{state.branch}`",
        f"Halted: {halted}",
        "",
        f"Completed ({len(state.completed)}): "
        + ", ".join(f"`{s}`" for s in state.completed),
        "",
        f"With caveats ({len(state.caveats)}): "
        + ", ".join(f"`{s}`" for s in state.caveats),
        "",
        f"Blocked ({len(state.blocked)}): "
        + ", ".join(f"`{s}`" for s in state.blocked),
        "",
        "## Per-task notes",
        "",
    ]
    for record in records:
        notes_path = TASKS_DIR / record.slug / "audit/AUTHORING_HISTORY.md"
        if not notes_path.exists():
            continue
        notes = parse_notes(notes_path, record.slug)
        lines.append(f"### `{record.slug}` — {notes.status}")
        if notes.open_issues:
            for issue in notes.open_issues:
                lines.append(f"- [{issue.severity}] {issue.text}")
        if notes.suggested_prompt_changes:
            lines.append("")
            lines.append(f"**Suggested prompt changes:** {notes.suggested_prompt_changes}")
        if notes.inventory_change_proposals:
            lines.append(f"**Inventory change proposals:** {notes.inventory_change_proposals}")
        if notes.library_extensions:
            lines.append(f"**Library extensions:** {notes.library_extensions}")
        lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[orchestrator] wrote morning summary to {summary_path}")


def _current_branch() -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    name = proc.stdout.strip()
    return name or None


def _merge_back(state: RunState) -> None:
    """Switch back to the source branch and fast-forward-merge the run branch."""
    if not _is_git_repo():
        return
    target = state.source_branch
    print(f"[orchestrator] merging {state.branch} back into {target}")
    try:
        _git("checkout", target)
        _git("merge", "--ff-only", state.branch)
        print(f"[orchestrator] merged {state.branch} into {target}")
    except subprocess.CalledProcessError as exc:
        print(
            f"[orchestrator] WARN: merge-back failed ({exc}); "
            f"left checked out on {state.branch}",
            flush=True,
        )


def _is_git_repo() -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    return proc.returncode == 0


def _branch_exists(name: str) -> bool:
    if not _is_git_repo():
        return False
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", name],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    return proc.returncode == 0


def _git(*args: str, allow_empty: bool = False) -> None:
    cmd = ["git", *args]
    if allow_empty and cmd[1] == "commit":
        cmd.append("--allow-empty")
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
