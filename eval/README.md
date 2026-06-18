# eval

CLI + Starlette/HTMX UI for driving benchmark runs against adapter HTTP
servers (the contract from `thesis/thesis.typ` §4.4), grading inline, and
browsing results.

## Install

```sh
cd benchmark/eval
uv sync
```

## CLI

```sh
uv run eval run <adapter|--agent-url URL> [--tasks ID...] [--max-parallel N] [--label STR]
uv run eval score <run-id|run-dir>
uv run eval ui [--port 8765]
uv run eval adapters
```

Adapter names come from `adapters.yaml`. `--agent-url` is the ad-hoc escape
hatch and bypasses the config entirely.

## UI

`eval ui` starts a local Starlette app on `http://127.0.0.1:8765`. Live
updates use HTMX polling at 1.5 s. Maps render `.pmtiles` directly via
MapLibre over HTTP range requests.

## System dependencies

- **tippecanoe** — required for generating `.pmtiles` from per-task
  `visualize.py` outputs. Install via your package manager
  (`pacman -S tippecanoe` on Arch). The runner catches per-task visualise
  failures and records them in `layers.json`, so a missing tippecanoe will
  not abort a run; the affected task's map pane will simply be empty.

## Layout

```
benchmark/eval/
  adapters.yaml                          # named adapter targets
  eval/
    core/                                # tasks, runner, scoring, storage
    cli.py
    ui/{app.py,templates,static}
  geo_grading/                           # grading primitives + ScoreReport
  tasks/                                 # task suite (task.json, grade.py, …)
  runs/                                  # run outputs (run.json, score.json, …)
```
