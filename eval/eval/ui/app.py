"""Starlette + HTMX UI for browsing the task suite and launching/observing runs.

Live updates are HTMX polling at 1.5 s, not SSE. The UI re-reads `run.json`
from disk on each poll cycle; no in-memory cache. CLI- and UI-launched runs
are observed identically. Polling stops once all tasks reach a terminal status.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from eval.core.adapters import load_adapters
from eval.core.viz import make_layer
from eval.core.runner import (
    AdapterTarget,
    RunSpec,
    rerun_task as rerun_one_task,
    resume as resume_run,
    run as run_run,
)
from eval.core.storage import RUNS_DIR, RunStore, list_runs, utc_iso
from eval.core.tasks import Task, load_task, load_tasks

UI_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(UI_DIR / "templates"))
PROJECT_ROOT = UI_DIR.parents[3]


TERMINAL = {"done", "failed", "cancelled"}

# Maps file extension → highlight.js language ID. Membership here also
# determines whether a file is treated as "source" in the Outputs tab
# (clickable view) vs. download-only.
_SOURCE_LANG_MAP = {
    "py": "python", "pyi": "python",
    "js": "javascript", "mjs": "javascript", "cjs": "javascript",
    "ts": "typescript", "tsx": "typescript", "jsx": "javascript",
    "html": "xml", "htm": "xml", "xml": "xml", "svg": "xml",
    "css": "css", "scss": "scss",
    "json": "json", "geojson": "json", "ndjson": "json",
    "yaml": "yaml", "yml": "yaml",
    "toml": "ini", "ini": "ini", "cfg": "ini",
    "md": "markdown",
    "sh": "bash", "bash": "bash", "zsh": "bash",
    "sql": "sql",
    "go": "go", "rs": "rust", "rb": "ruby",
    "c": "c", "h": "c", "cpp": "cpp", "hpp": "cpp", "cc": "cpp",
    "java": "java", "kt": "kotlin", "swift": "swift",
    "dockerfile": "dockerfile", "tf": "hcl",
    "csv": "plaintext", "tsv": "plaintext", "wkt": "plaintext",
    "txt": "plaintext", "log": "plaintext",
}


def _detect_lang(filename: str) -> str | None:
    name = filename.lower()
    if "." not in name:
        return None
    ext = name.rsplit(".", 1)[-1]
    return _SOURCE_LANG_MAP.get(ext)

# Simple metadata cache: path → (mtime, metadata_dict)
_geo_meta_cache: dict[str, tuple[float, dict]] = {}




def _ensure_task_tiles(task: Task) -> list[dict]:
    """Lazily generate PMTiles for all geospatial inputs + reference outputs.

    Returns the full layer list. Layers are cached in
    ``<task_dir>/visualizations/`` alongside a ``layers.json`` manifest.
    A layer is only regenerated when its source file is newer than its
    ``.pmtiles`` output (or the output is missing).
    """
    import shutil

    viz_dir = task.dir / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = viz_dir / "layers.json"

    # Load existing manifest if present
    existing: dict[str, dict] = {}
    if manifest_path.is_file():
        try:
            for L in json.loads(manifest_path.read_text()).get("layers", []):
                existing[L.get("_source_key", L["name"])] = L
        except Exception:
            pass

    has_tippecanoe = shutil.which("tippecanoe") is not None

    layers: list[dict] = []

    def _maybe_add(source_path: Path, layer_name: str, group: str, source_key: str):
        if not source_path.is_file():
            return
        pmtiles_path = viz_dir / f"{layer_name}.pmtiles"
        # Check if up-to-date
        if source_key in existing and pmtiles_path.is_file():
            src_mtime = source_path.stat().st_mtime
            tile_mtime = pmtiles_path.stat().st_mtime
            if tile_mtime >= src_mtime:
                layers.append(existing[source_key])
                return
        # Need to generate — requires tippecanoe
        if not has_tippecanoe:
            return
        # Detect geometry type from metadata cache
        meta = _geo_metadata(source_path)
        if not meta.get("crs"):
            return  # not geospatial
        geom_type = meta.get("geometry_type", "Polygon")
        try:
            spec = make_layer(
                source_path.parent, viz_dir,
                source_path.name, layer_name, geom_type,
            )
            spec["_source_key"] = source_key
            spec["_group"] = group
            layers.append(spec)
        except Exception:
            pass  # skip silently (e.g. non-geo file)

    # Inputs
    for inp in task.inputs:
        key = f"input:{inp.name}"
        name = f"in_{inp.name}"
        _maybe_add(inp.path, name, "input", key)

    # Reference outputs
    ref_dir = task.dir / "reference" / "solution" / "outputs"
    for out in task.expected_outputs:
        key = f"output:{out.name}"
        name = f"out_{out.name.rsplit('.', 1)[0]}"
        _maybe_add(ref_dir / out.name, name, "output", key)

    # Write manifest
    manifest_path.write_text(json.dumps({"layers": layers, "error": None}, indent=2) + "\n")
    return layers


def _geo_metadata(path: Path) -> dict:
    """Return {crs, geometry_type, feature_count} for a geo file, with mtime cache."""
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    cached = _geo_meta_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        import geopandas as gpd
        suffix = path.suffix.lower()
        if suffix in (".geoparquet", ".parquet"):
            gdf = gpd.read_parquet(path)
        else:
            gdf = gpd.read_file(path)
        geom_types = sorted(set(gdf.geometry.geom_type.dropna())) if "geometry" in gdf.columns else []
        crs_str = None
        if gdf.crs:
            epsg = gdf.crs.to_epsg()
            crs_str = f"EPSG:{epsg}" if epsg else str(gdf.crs)
        meta = {
            "crs": crs_str,
            "geometry_type": ", ".join(geom_types) if geom_types else None,
            "feature_count": len(gdf),
        }
    except Exception:
        meta = {}
    _geo_meta_cache[key] = (mtime, meta)
    return meta


def _task_or_404(task_id: str) -> Task:
    try:
        return load_task(task_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _run_dir_or_404(run_id: str) -> Path:
    d = RUNS_DIR / run_id
    if not (d / "run.json").is_file():
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return d


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


async def index(request: Request):
    tasks = load_tasks()
    return TEMPLATES.TemplateResponse(
        request, "tasks_index.html", {"tasks": tasks}
    )


async def task_image(request: Request):
    task = _task_or_404(request.path_params["task_id"])
    path = task.dir / "assets" / "image.webp"
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/webp")


async def task_detail(request: Request):
    task = _task_or_404(request.path_params["task_id"])
    layers = _ensure_task_tiles(task)

    # Prev/next navigation
    all_tasks = load_tasks()
    task_ids = [t.task_id for t in all_tasks]
    idx = task_ids.index(task.task_id) if task.task_id in task_ids else -1
    prev_task_id = task_ids[idx - 1] if idx > 0 else None
    next_task_id = task_ids[idx + 1] if 0 <= idx < len(task_ids) - 1 else None
    # Geo metadata for inputs
    input_meta: dict[str, dict] = {}
    for inp in task.inputs:
        input_meta[inp.name] = _geo_metadata(inp.path)

    # Feature counts for expected outputs (from reference solution)
    output_meta: dict[str, dict] = {}
    ref_outputs_dir = task.dir / "reference" / "solution" / "outputs"
    for out in task.expected_outputs:
        ref_path = ref_outputs_dir / out.name
        if ref_path.is_file():
            meta = _geo_metadata(ref_path)
            output_meta[out.name] = {"feature_count": meta.get("feature_count")}

    recent_runs: list[dict] = []
    for r in list_runs():
        ts = (r.get("tasks") or {}).get(task.task_id)
        if not ts:
            continue
        adapter = r.get("adapter") or {}
        # Count tool-call steps from transcript if available
        step_count = None
        transcript_path = Path(r.get("_dir", "")) / task.task_id / "transcript.json"
        if not transcript_path.is_file():
            run_dir = RUNS_DIR / r["run_id"]
            transcript_path = run_dir / task.task_id / "transcript.json"
        if transcript_path.is_file():
            try:
                tx = json.loads(transcript_path.read_text())
                step_count = sum(1 for e in tx.get("events", []) if e.get("type") == "tool_call")
            except Exception:
                pass
        # Runs predating the version field record no task_version and are
        # treated as v0 — outdated against any task ≥ v1.
        recorded_version = ts.get("task_version", 0)
        recent_runs.append({
            "run_id": r["run_id"],
            "adapter": adapter.get("name") or adapter.get("label") or adapter.get("url") or "?",
            "started_at": r.get("started_at", ""),
            "status": ts.get("status"),
            "score": ts.get("score"),
            "error": ts.get("error"),
            "duration_s": ts.get("duration_s"),
            "estimated_cost_usd": ts.get("estimated_cost_usd"),
            "step_count": step_count,
            "task_version": recorded_version,
            "outdated": recorded_version < task.version,
        })
        if len(recent_runs) >= 5:
            break
    return TEMPLATES.TemplateResponse(
        request,
        "task_detail.html",
        {
            "task": task,
            "task_version": task.version,
            "input_meta": input_meta,
            "output_meta": output_meta,
            "layers": layers,
            "layer_names": {L["name"] for L in layers},
            "layers_base": f"/tasks/{task.task_id}/tiles/",
            "viz_globe": task.viz_globe,
            "recent_runs": recent_runs,
            "prev_task_id": prev_task_id,
            "next_task_id": next_task_id,
        },
    )


async def task_input_download(request: Request):
    task = _task_or_404(request.path_params["task_id"])
    name = request.path_params["name"]
    for inp in task.inputs:
        if inp.name == name:
            if inp.path.is_file():
                return FileResponse(inp.path, filename=inp.path.name)
            break
    raise HTTPException(404)



async def task_reference_output(request: Request):
    task = _task_or_404(request.path_params["task_id"])
    fname = request.path_params["fname"]
    path = task.dir / "reference" / "solution" / "outputs" / fname
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, filename=fname)


async def task_tiles_file(request: Request):
    task = _task_or_404(request.path_params["task_id"])
    path = task.dir / "visualizations" / request.path_params["fname"]
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


async def task_reference_file(request: Request):
    task = _task_or_404(request.path_params["task_id"])
    path = task.reference_visualizations_dir / request.path_params["fname"]
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


async def runs_list(request: Request):
    runs = list_runs()
    # Total spend per run is the sum of per-task estimates the harness
    # records on the run.json. Missing values are skipped, not zeroed —
    # an in-flight task that has not yet reported a cost shouldn't drag
    # the displayed total down.
    for r in runs:
        total = 0.0
        any_cost = False
        for ts in (r.get("tasks") or {}).values():
            c = ts.get("estimated_cost_usd")
            if isinstance(c, (int, float)):
                total += float(c)
                any_cost = True
        r["total_cost_usd"] = total if any_cost else None
    # Matrix view: oldest-first columns, union of task_ids as rows.
    matrix_runs = list(reversed(runs))
    task_ids: list[str] = []
    seen: set[str] = set()
    for r in matrix_runs:
        for tid in (r.get("tasks") or {}).keys():
            if tid not in seen:
                seen.add(tid)
                task_ids.append(tid)
    task_ids.sort()
    # Lookup table for current task content versions — drives the outdated
    # styling on each matrix cell.
    current_versions = {t.task_id: t.version for t in load_tasks()}
    return TEMPLATES.TemplateResponse(
        request,
        "runs_list.html",
        {
            "runs": runs,
            "matrix_runs": matrix_runs,
            "matrix_task_ids": task_ids,
            "current_versions": current_versions,
        },
    )


async def runs_new(request: Request):
    adapters = load_adapters()
    tasks = load_tasks()
    return TEMPLATES.TemplateResponse(
        request, "runs_new.html", {"adapters": adapters, "tasks": tasks}
    )


_active_runs: dict[str, threading.Thread] = {}


async def runs_create(request: Request):
    form = await request.form()
    adapter_name = (form.get("adapter") or "").strip()
    agent_url = (form.get("agent_url") or "").strip()
    label = (form.get("label") or "").strip() or None
    task_filter_raw = (form.get("tasks") or "").strip()
    max_parallel_raw = (form.get("max_parallel") or "").strip()

    task_filter = (
        [t for t in task_filter_raw.replace(",", " ").split() if t]
        or None
    )
    max_parallel = int(max_parallel_raw) if max_parallel_raw else None

    if agent_url:
        target = AdapterTarget(url=agent_url, name=None, label=agent_url)
    elif adapter_name:
        adapters = load_adapters()
        if adapter_name not in adapters:
            return PlainTextResponse(f"unknown adapter: {adapter_name}", 400)
        target = adapters[adapter_name]
    else:
        return PlainTextResponse("either adapter or agent_url required", 400)

    spec = RunSpec(
        adapter=target,
        task_filter=task_filter,
        max_parallel=max_parallel,
        label=label,
    )

    # Capture pre-existing runs so we can detect the new run_id.
    pre = set((p.name for p in RUNS_DIR.iterdir())) if RUNS_DIR.exists() else set()

    def _go():
        try:
            run_run(spec, RUNS_DIR)
        except Exception as exc:  # pragma: no cover
            print(f"runs_create: {exc}")

    t = threading.Thread(target=_go, daemon=True)
    t.start()

    # Wait briefly for the run dir to appear.
    for _ in range(50):
        if RUNS_DIR.exists():
            new = set((p.name for p in RUNS_DIR.iterdir())) - pre
            if new:
                run_id = sorted(new)[-1]
                _active_runs[run_id] = t
                return RedirectResponse(f"/runs/{run_id}", status_code=303)
        await asyncio.sleep(0.1)

    return PlainTextResponse("run did not start within timeout", 500)


async def run_detail(request: Request):
    run_dir = _run_dir_or_404(request.path_params["run_id"])
    state = json.loads((run_dir / "run.json").read_text())
    return TEMPLATES.TemplateResponse(
        request, "run_detail.html", {"state": state, "run_id": state["run_id"]}
    )


async def run_table_fragment(request: Request):
    run_dir = _run_dir_or_404(request.path_params["run_id"])
    state = json.loads((run_dir / "run.json").read_text())
    tasks = state.get("tasks", {})
    all_terminal = bool(tasks) and all(
        t.get("status") in TERMINAL for t in tasks.values()
    )
    now = datetime.now(timezone.utc)
    # Current task versions, so we can flag tasks whose recorded run version
    # has been left behind by a content change to task.json/grade.py/inputs.
    current_versions = {t.task_id: t.version for t in load_tasks()}
    # Enrich each task with tool-call count, elapsed time, and outdated flag.
    for task_id, t in tasks.items():
        transcript_path = run_dir / task_id / "transcript.json"
        if transcript_path.is_file():
            events = json.loads(transcript_path.read_text()).get("events", [])
            t["steps"] = sum(1 for e in events if e.get("type") == "tool_call")
        # Compute elapsed time for running tasks that have no duration yet
        if t.get("duration_s") is None and t.get("started_at"):
            try:
                started = datetime.fromisoformat(t["started_at"])
                t["elapsed_s"] = round((now - started).total_seconds(), 1)
            except Exception:
                pass
        recorded = t.get("task_version", 0)
        current = current_versions.get(task_id, recorded)
        t["task_version"] = recorded
        t["current_version"] = current
        t["outdated"] = recorded < current
    return TEMPLATES.TemplateResponse(
        request,
        "_run_table.html",
        {"state": state, "all_terminal": all_terminal},
    )


async def run_cancel(request: Request):
    run_id = request.path_params["run_id"]
    run_dir = _run_dir_or_404(run_id)
    (run_dir / "cancel.flag").write_text("")

    # If no active runner thread, the run is orphaned (e.g. process died).
    # Directly update run.json so it moves to cancelled state.
    thread = _active_runs.get(run_id)
    if thread is None or not thread.is_alive():
        store = RunStore.open(run_dir)
        for tid, t in store.state.get("tasks", {}).items():
            if t.get("status") in ("pending", "running"):
                store.update_task(tid, {
                    "status": "cancelled",
                    "finished_at": utc_iso(),
                    "last_event": "cancelled (orphaned)",
                })
        store.set_status("cancelled", finished_at=utc_iso())

    return RedirectResponse(f"/runs/{run_id}", status_code=303)


async def run_resume(request: Request):
    run_id = request.path_params["run_id"]
    run_dir = _run_dir_or_404(run_id)

    def _go():
        try:
            resume_run(run_dir)
        except Exception as exc:
            print(f"run_resume: {exc}")

    t = threading.Thread(target=_go, daemon=True)
    t.start()
    _active_runs[run_id] = t
    return RedirectResponse(f"/runs/{run_id}", status_code=303)


async def run_task_rerun(request: Request):
    run_id = request.path_params["run_id"]
    task_id = request.path_params["task_id"]
    run_dir = _run_dir_or_404(run_id)

    state = json.loads((run_dir / "run.json").read_text())
    task_state = state.get("tasks", {}).get(task_id)
    if task_state is None:
        raise HTTPException(404, f"task {task_id} not part of run {run_id}")
    if task_state.get("status") in ("pending", "running"):
        return PlainTextResponse(
            f"task already {task_state['status']} — cannot rerun", 409
        )

    def _go():
        try:
            rerun_one_task(run_dir, task_id)
        except Exception as exc:
            print(f"run_task_rerun: {exc}")

    t = threading.Thread(target=_go, daemon=True)
    t.start()
    _active_runs[run_id] = t
    return RedirectResponse(f"/runs/{run_id}/{task_id}", status_code=303)


def _outputs_as_table(path: Path) -> dict | None:
    """Render CSV/parquet (geometry-less) as table; return None if not tabular."""
    suffix = path.suffix.lower()
    rows: list[list[str]] = []
    headers: list[str] = []
    try:
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i == 0:
                        headers = row
                    else:
                        rows.append(row)
                    if i > 500:
                        break
        elif suffix == ".parquet":
            try:
                import pyarrow.parquet as pq

                tbl = pq.read_table(path)
                cols = [c for c in tbl.column_names if c.lower() != "geometry"]
                if not cols:
                    return None
                tbl = tbl.select(cols)
                headers = tbl.column_names
                py = tbl.slice(0, 500).to_pylist()
                rows = [[str(r.get(h, "")) for h in headers] for r in py]
            except Exception:
                return None
        else:
            return None
    except Exception:
        return None
    return {"name": path.name, "headers": headers, "rows": rows}


import re as _re

_EXIT_CODE_RE = _re.compile(r"<exit_code>(\d+)</exit_code>")
_STDOUT_RE = _re.compile(r"<stdout>\n?(.*?)</stdout>", _re.DOTALL)
_STDERR_RE = _re.compile(r"<stderr>\n?(.*?)</stderr>", _re.DOTALL)


def _parse_bash_output(raw: str) -> dict:
    """Parse the XML-ish bash output into structured fields."""
    m = _EXIT_CODE_RE.search(raw)
    exit_code = int(m.group(1)) if m else None
    m = _STDOUT_RE.search(raw)
    stdout = m.group(1).rstrip() if m else None
    m = _STDERR_RE.search(raw)
    stderr = m.group(1).rstrip() if m else None
    # If no XML tags, treat entire output as stdout
    if exit_code is None and stdout is None:
        stdout = raw.strip() or None
    return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr}


def _relative_ts(ts_str: str, start_str: str) -> str:
    """Convert absolute timestamp to relative 'm:ss' since session start."""
    try:
        ts = datetime.fromisoformat(ts_str)
        start = datetime.fromisoformat(start_str)
        delta = max(0, (ts - start).total_seconds())
        m, s = int(delta) // 60, int(delta) % 60
        return f"{m}:{s:02d}"
    except Exception:
        return ""


def _strip_session_root(path: str, session_id: str | None) -> str:
    """Strip the session working directory prefix, returning a relative path."""
    if not session_id:
        return path
    marker = f"/.sessions/{session_id}/"
    idx = path.find(marker)
    if idx != -1:
        return path[idx + len(marker):]
    return path


def _merge_tool_events(events: list[dict], session_id: str | None = None) -> list[dict]:
    """Merge consecutive tool_call + tool_result into single merged events."""
    # Compute relative timestamps from first event
    start_ts = events[0]["ts"] if events else ""

    merged: list[dict] = []
    i = 0
    while i < len(events):
        e = events[i]
        # Add relative timestamp to all events
        e["rel_ts"] = _relative_ts(e.get("ts", ""), start_ts)

        if e.get("type") == "tool_call":
            me = {**e, "type": "tool_merged", "result": None}
            # Look for matching tool_result next
            if i + 1 < len(events) and events[i + 1].get("type") == "tool_result":
                result = events[i + 1]["content"]
                me["result"] = result
                # Parse bash output structure
                if e["content"].get("name") == "Bash" and isinstance(result.get("output"), str):
                    me["result_parsed"] = _parse_bash_output(result["output"])
                i += 2
            else:
                i += 1
            # Build summary line
            call = me["content"]
            name = call.get("name", "")
            args = call.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {}
            if name == "Bash":
                desc = args.get("description")
                cmd = args.get("command", "")
                if desc:
                    me["summary"] = desc
                else:
                    first_line = cmd.split("\n")[0]
                    # Strip session root from summary
                    if session_id:
                        marker = f"/.sessions/{session_id}/"
                        first_line = first_line.replace(marker, "")
                        # Also strip common cd prefix to session dir
                        cd_prefix = f"cd /home/nhp/project/benchmark/harness/.sessions/{session_id} && "
                        if first_line.startswith(cd_prefix):
                            first_line = first_line[len(cd_prefix):]
                    me["summary"] = (first_line[:80] + "...") if len(first_line) > 80 else first_line
            elif name in ("Read", "Write"):
                raw_path = args.get("file_path", "")
                me["summary"] = _strip_session_root(raw_path, session_id)
            elif name == "Edit":
                raw_path = args.get("file_path", "")
                me["summary"] = _strip_session_root(raw_path, session_id)
            merged.append(me)
        elif e.get("type") == "tool_result":
            # Orphaned result (no preceding call) — keep as-is
            merged.append(e)
            i += 1
        else:
            # Pretty-print system JSON events for the template
            if e.get("type") == "system" and isinstance(e.get("content"), str):
                try:
                    parsed = json.loads(e["content"])
                    e = {**e, "content_json": json.dumps(parsed, indent=2)}
                except (json.JSONDecodeError, TypeError):
                    pass
            merged.append(e)
            i += 1
    return merged


async def run_task_detail(request: Request):
    run_dir = _run_dir_or_404(request.path_params["run_id"])
    task_id = request.path_params["task_id"]
    task = _task_or_404(task_id)
    state = json.loads((run_dir / "run.json").read_text())
    task_state = state.get("tasks", {}).get(task_id, {})
    task_run_dir = run_dir / task_id

    # Compute elapsed time for running tasks
    if task_state.get("duration_s") is None and task_state.get("started_at"):
        try:
            started = datetime.fromisoformat(task_state["started_at"])
            task_state["elapsed_s"] = round(
                (datetime.now(timezone.utc) - started).total_seconds(), 1
            )
        except Exception:
            pass

    transcript: dict | None = None
    if (task_run_dir / "transcript.json").is_file():
        try:
            transcript = json.loads((task_run_dir / "transcript.json").read_text())
            transcript["events"] = _merge_tool_events(
                transcript.get("events", []),
                session_id=task_state.get("session_id"),
            )
        except Exception:
            transcript = None

    score: dict | None = None
    if (task_run_dir / "score.json").is_file():
        try:
            score = json.loads((task_run_dir / "score.json").read_text())
        except Exception:
            score = None

    session: dict | None = None
    if (task_run_dir / "session.json").is_file():
        try:
            session = json.loads((task_run_dir / "session.json").read_text())
        except Exception:
            session = None

    retrospective: dict | None = None
    if (task_run_dir / "retrospective.json").is_file():
        try:
            retrospective = json.loads((task_run_dir / "retrospective.json").read_text())
        except Exception:
            retrospective = None

    outputs_dir = task_run_dir / "outputs"
    output_files: list[dict] = []
    tables: list[dict] = []
    if outputs_dir.exists():
        for p in sorted(outputs_dir.iterdir()):
            if p.is_file():
                output_files.append({
                    "name": p.name,
                    "is_source": _detect_lang(p.name) is not None,
                })
                tbl = _outputs_as_table(p)
                if tbl:
                    tables.append(tbl)

    # Agent + reference layers
    agent_layers_json = task_run_dir / "visualizations" / "layers.json"
    agent_layers = []
    if agent_layers_json.is_file():
        try:
            agent_layers = json.loads(agent_layers_json.read_text()).get("layers", [])
        except Exception:
            agent_layers = []
    ref_layers_json = task.reference_visualizations_dir / "layers.json"
    ref_layers = []
    if ref_layers_json.is_file():
        try:
            ref_layers = json.loads(ref_layers_json.read_text()).get("layers", [])
        except Exception:
            ref_layers = []

    return TEMPLATES.TemplateResponse(
        request,
        "run_task_detail.html",
        {
            "task": task,
            "task_state": task_state,
            "transcript": transcript,
            "score": score,
            "session": session,
            "retrospective": retrospective,
            "output_files": output_files,
            "tables": tables,
            "agent_layers": agent_layers,
            "ref_layers": ref_layers,
            "agent_layers_base": f"/runs/{state['run_id']}/{task_id}/visualizations/",
            "ref_layers_base": f"/tasks/{task_id}/visualizations/",
            "viz_globe": task.viz_globe,
            "run_id": state["run_id"],
        },
    )


async def run_task_viz_file(request: Request):
    run_dir = _run_dir_or_404(request.path_params["run_id"])
    task_id = request.path_params["task_id"]
    path = run_dir / task_id / "visualizations" / request.path_params["fname"]
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


async def run_task_output_file(request: Request):
    run_dir = _run_dir_or_404(request.path_params["run_id"])
    task_id = request.path_params["task_id"]
    path = run_dir / task_id / "outputs" / request.path_params["fname"]
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


async def run_task_output_view(request: Request):
    """Render a source file from a task's outputs/ with hljs highlighting."""
    import html as _html

    run_id = request.path_params["run_id"]
    task_id = request.path_params["task_id"]
    fname = request.path_params["fname"]
    run_dir = _run_dir_or_404(run_id)
    path = run_dir / task_id / "outputs" / fname
    if not path.is_file():
        raise HTTPException(404)
    lang = _detect_lang(fname)
    if lang is None:
        raise HTTPException(415, f"not a source file: {fname}")
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(500, f"failed to read {fname}: {e}")

    title = _html.escape(f"{fname} · {task_id}")
    safe_fname = _html.escape(fname)
    safe_task = _html.escape(task_id)
    safe_run = _html.escape(run_id)
    safe_body = _html.escape(content)
    download_url = f"/runs/{run_id}/{task_id}/outputs/{fname}"
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.10.0/styles/github.min.css">
<style>
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #232329; background: #fff; }}
  header {{ position: sticky; top: 0; background: #fafafa; border-bottom: 1px solid #e5e5e5; padding: 10px 18px; display: flex; gap: 14px; align-items: baseline; }}
  header h1 {{ margin: 0; font-size: 14px; font-family: 'JetBrains Mono', monospace; font-weight: 700; }}
  header .meta {{ font-size: 12px; color: #888; flex: 1 1 auto; }}
  header a {{ font-size: 12px; color: #3a5a80; text-decoration: none; }}
  header a:hover {{ text-decoration: underline; }}
  pre {{ margin: 0; padding: 14px 18px; font-family: 'JetBrains Mono', Menlo, monospace; font-size: 12.5px; line-height: 1.5; }}
  pre code.hljs {{ background: transparent; padding: 0; }}
</style>
</head>
<body>
<header>
  <h1>{safe_fname}</h1>
  <span class="meta">{safe_task} &middot; {safe_run}</span>
  <a href="{download_url}" download>Download</a>
</header>
<pre><code class="language-{lang}">{safe_body}</code></pre>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js"></script>
<script>hljs.highlightAll();</script>
</body>
</html>
"""
    return HTMLResponse(page)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> Starlette:
    static_dir = UI_DIR / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    routes = [
        Route("/", index),
        Route("/tasks/{task_id}/image", task_image),
        Route("/tasks/{task_id}", task_detail),
        Route("/tasks/{task_id}/inputs/{name}", task_input_download),
        Route("/tasks/{task_id}/reference/{fname}", task_reference_output),
        Route("/tasks/{task_id}/tiles/{fname}", task_tiles_file),
        Route(
            "/tasks/{task_id}/visualizations/{fname}",
            task_reference_file,
        ),
        Route("/runs", runs_list),
        Route("/runs/new", runs_new, methods=["GET"]),
        Route("/runs", runs_create, methods=["POST"]),
        Route("/runs/{run_id}", run_detail),
        Route("/runs/{run_id}/_table", run_table_fragment),
        Route("/runs/{run_id}/cancel", run_cancel, methods=["POST"]),
        Route("/runs/{run_id}/resume", run_resume, methods=["POST"]),
        Route("/runs/{run_id}/{task_id}", run_task_detail),
        Route(
            "/runs/{run_id}/{task_id}/rerun",
            run_task_rerun,
            methods=["POST"],
        ),
        Route(
            "/runs/{run_id}/{task_id}/visualizations/{fname}",
            run_task_viz_file,
        ),
        Route(
            "/runs/{run_id}/{task_id}/outputs/{fname}/view",
            run_task_output_view,
        ),
        Route(
            "/runs/{run_id}/{task_id}/outputs/{fname}",
            run_task_output_file,
        ),
        Mount("/static", StaticFiles(directory=str(static_dir)), name="static"),
    ]
    return Starlette(debug=False, routes=routes)
