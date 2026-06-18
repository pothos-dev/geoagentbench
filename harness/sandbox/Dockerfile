# syntax=docker/dockerfile:1.7
#
# Per-session sandbox image for the harness.
#
# Each agent session spawns one throwaway container from this image. The
# harness drives tool calls via `docker exec` against the container and
# moves files in/out via `docker cp` at session boundaries (no host bind
# mount), so the agent's filesystem activity is contained to /work inside
# the container.
#
# Build:
#   docker build -t geoagentbench-sandbox:latest -f benchmark/harness/sandbox/Dockerfile benchmark/harness/sandbox/
#
# GIS deps (geopandas, pyosmium, osmnx, duckdb, ...) are pre-installed
# into the system site-packages so agents can `python solve.py` directly
# without dealing with venvs, PEP 723 metadata, or `uv run`.

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libsqlite3-dev \
        zlib1g-dev \
        gdal-bin \
        libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# NOTE: `pyrosm` is intentionally omitted. Its transitive build-dep
# `pyrobuf` (unmaintained since 2020) fails to build on Python 3.14.
# Use `pyosmium` for PBF reads instead; agents that still need pyrosm can
# pull it lazily via `pip install --user pyrosm`.
RUN pip install \
        geopandas \
        shapely \
        pyproj \
        pyogrio \
        fiona \
        pandas \
        pyarrow \
        duckdb \
        osmnx \
        osmium \
        overturemaps

# Non-root agent user (UID 1000). System site-packages is read-only for
# this user; extras go to ~/.local via `pip install --user`.
RUN useradd --create-home --uid 1000 --shell /bin/bash agent
USER agent
WORKDIR /work

ENTRYPOINT ["sleep", "infinity"]
