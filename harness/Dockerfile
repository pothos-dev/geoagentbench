# syntax=docker/dockerfile:1.7
#
# geoagentbench harness service image.
#
# Deployment model (post PR3 refactor): the harness no longer runs agent
# tools in-process. It runs as a container, mounts the host docker socket
# at /var/run/docker.sock, and spawns one sibling ``geoagentbench-sandbox``
# container per session. Tool calls (Bash/Read/Edit/Write) execute via
# ``docker exec`` into that sandbox; files cross the boundary via
# ``docker cp``. As a consequence this image only needs:
#   - Python 3.14 + the harness Python deps
#   - the ``docker`` CLI (to talk to the daemon over the mounted socket)
# It does NOT need Node, the Claude Code CLI, GDAL, fiona, osmnx, …  those
# live in the sandbox image (``benchmark/harness/sandbox/Dockerfile``).
#
# Build:
#   docker build -t geoagentbench-harness:latest -f benchmark/harness/Dockerfile benchmark/harness/
# Run:
#   docker run -d --name harness \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -e OPENROUTER_API_KEY \
#     -p 8080:8080 \
#     geoagentbench-harness:latest

# ---- builder: install python deps into a venv we copy out ----
FROM python:3.14-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock* ./
COPY adapter_core ./adapter_core
COPY openrouter ./openrouter
COPY dispatcher ./dispatcher

RUN uv venv /opt/venv && uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev


# ---- runtime ----
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/usr/local/bin:/usr/bin:/bin" \
    HARNESS_SESSIONS_DIR=/var/lib/harness/.sessions

# curl for the healthcheck and to fetch the docker CLI tarball; ca-certs
# for TLS. We grab the static docker client from download.docker.com rather
# than pulling Debian's ``docker.io`` package, which would also drag in the
# daemon (we only need the CLI — the daemon lives on the host).
ARG DOCKER_CLI_VERSION=27.4.0
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_CLI_VERSION}.tgz" \
        | tar -xz -C /usr/local/bin --strip-components=1 docker/docker \
    && docker --version

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY adapter_core ./adapter_core
COPY openrouter ./openrouter
COPY dispatcher ./dispatcher
COPY pyproject.toml ./

RUN mkdir -p /var/lib/harness/.sessions

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/health || exit 1

CMD ["python", "-m", "dispatcher"]
