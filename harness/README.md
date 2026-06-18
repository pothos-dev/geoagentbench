# geoagentbench harness

HTTP service that drives one OpenRouter-routed agent per session against a
geospatial-benchmark task. The service itself never executes agent tool
calls in-process — every Bash/Read/Edit/Write call is forwarded into a
per-session sandbox container.

## Architecture

```
   eval CLI / curl
        |
        v
  +--------------+      starts/stops via docker.sock
  |   harness    |  -------------------------------+
  |  (this svc)  |                                 |
  +--------------+                                 v
        |                            +----------------------------+
        |  docker exec / docker cp   |  geoagentbench-sandbox          |
        +--------------------------> |  (one container/session)   |
                                     |  /work  (writable layer)   |
                                     +----------------------------+
```

- One Linux container per agent session, spawned at `POST /sessions` and
  torn down on `DELETE /sessions/{id}`. No host bind mount: the sandbox
  workdir lives in the container's writable layer, which keeps the
  setup correct when the harness itself runs as a sibling container.
- The `Bash`, `Read`, `Edit`, `Write` tools the OpenRouter agent calls
  route through `docker exec` into the sandbox. File transfer at session
  start/end uses `docker cp`, which streams via the docker API rather
  than relying on a host path being visible inside the harness.
- Only OpenRouter-routed model IDs (containing a `/` provider prefix)
  are supported. The Claude Code adapter was removed in the PR3 sandbox
  refactor; a bare model id now produces a `400 Bad Request` at
  session-creation time with an actionable message.

## Quickstart

Build both images:

```bash
docker build -t geoagentbench-sandbox -f benchmark/harness/sandbox/Dockerfile benchmark/harness/sandbox/
docker build -t geoagentbench-harness -f benchmark/harness/Dockerfile         benchmark/harness/
```

Run the harness as a container, mounting the host docker socket so it can
spawn sibling sandbox containers:

```bash
docker run -d --name harness \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e OPENROUTER_API_KEY \
  -p 8080:8080 \
  geoagentbench-harness
```

Or, for local development on the host:

```bash
cd benchmark/harness
.venv/bin/python -m dispatcher
```

Both modes listen on port `8080` (override with `HARNESS_PORT`).

## Environment

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENROUTER_API_KEY` | yes | - | OpenRouter auth; all sessions fail without it |
| `HARNESS_PORT` | no | `8080` | Listen port |
| `HARNESS_PROMPT_VARIANT` | no | `gis_detailed` | `basic` or `gis_detailed` |
| `OPENROUTER_MAX_ITERATIONS` | no | `50` | Tool-call round cap |
| `HARNESS_MAX_CONCURRENT_SESSIONS` | no | `4` | Parallelism limit |
| `GEOAGENTBENCH_SANDBOX_IMAGE` | no | `geoagentbench-sandbox:latest` | Override the per-session sandbox image tag |
| `HARNESS_BEARER_TOKEN` | no | - | If set, requires `Authorization: Bearer ...` on all non-`/health` routes |

## Routing

The `X-Harness-Model` header is required on `POST /sessions`. The value
must contain a `/` (e.g. `openai/gpt-4o-mini`, `google/gemma-4-26b-a4b-it`).
Bare ids like `opus`, `sonnet`, `haiku`, or `claude-opus-4-7` are rejected
with `400`: the Claude Code adapter that used to handle them was removed.
