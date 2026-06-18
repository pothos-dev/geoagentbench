"""Tool implementations mirroring Claude Code's observable semantics.

Four tools are exposed: ``Bash``, ``Read``, ``Edit``, ``Write``. Names,
JSON schemas, and error-message shapes are kept close to what Claude Code's
built-in tools produce so a model can recover from errors the same way as
the reference agent.

Per-session state (which files have been ``Read`` so far) lives on
``session.adapter_state["openrouter.read_files"]`` and gates Edit/Write.

Every tool call routes through ``docker exec`` into the session's
sandbox container (see ``adapter_core.container``). The agent only ever
touches files inside ``/work`` in the container; absolute paths are
validated against that root, relative paths are joined onto it.
"""

from __future__ import annotations

import asyncio
import posixpath
import subprocess
from typing import Any

from adapter_core.container import copy_from, exec_in
from adapter_core.sessions import Session

# ---------------------------------------------------------------- constants

BASH_DEFAULT_TIMEOUT_MS = 120_000
BASH_MAX_TIMEOUT_MS = 600_000
BASH_OUTPUT_LIMIT = 30_000  # chars per stream (stdout, stderr each)

# Read tool limits. The default line cap matches Claude Code's Read tool
# so that a model trained on that workflow does not blow up its context
# by reading a 50k-line file without offset/limit. The byte cap is a
# safety net against binary or pathological files — head -c stops the
# pull at the docker exec layer so the harness never buffers GBs.
READ_DEFAULT_LIMIT = 2000  # lines, when caller omits `limit`
READ_MAX_BYTES = 2 * 1024 * 1024

_TRUNC_SUFFIX = "\n[... truncated ...]"

# Container workdir. Mirrors WORKDIR in sandbox/Dockerfile.
_CONTAINER_WORKDIR = "/work"


# ---------------------------------------------------------------- schemas

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "Read",
            "description": (
                "Read a text file from disk. Returns content with cat -n style "
                "line numbers (6-char right-aligned line number, tab, content). "
                "Relative paths are resolved against the working directory. "
                "By default returns the first 2000 lines; use offset/limit to "
                "page through larger files. Binary files (anything containing "
                "NUL bytes) are refused — use a domain tool such as duckdb, "
                "geopandas, pyogrio, or sqlite3 instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "1-based line number to start reading from.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read.",
                    },
                },
                "required": ["file_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Write",
            "description": (
                "Write content to a file, overwriting if it exists. If the "
                "file already exists, you must Read it in this session first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file contents.",
                    },
                },
                "required": ["file_path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Edit",
            "description": (
                "Replace exactly one occurrence of old_string with new_string "
                "in a file. Fails if old_string is not unique unless "
                "replace_all is true. The file must have been Read in this "
                "session first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file.",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Exact text to replace.",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement text.",
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace every occurrence instead of requiring uniqueness.",
                    },
                },
                "required": ["file_path", "old_string", "new_string"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Bash",
            "description": (
                "Run a shell command in the session working directory. Returns "
                "stdout, stderr, and exit_code. Default timeout 120s, max 600s. "
                "Output is truncated past 30000 chars per stream."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in milliseconds (default 120000, max 600000).",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
]


# ---------------------------------------------------------------- per-session state


def _read_set(session: Session) -> set[str]:
    """Set of container-side ``/work/...`` paths the model has Read in this
    session."""
    state = session.adapter_state.setdefault("openrouter.read_files", set())
    assert isinstance(state, set)
    return state


def _active_proc_slot(session: Session) -> str:
    return "openrouter.active_proc"


def get_active_proc(session: Session) -> asyncio.subprocess.Process | None:
    proc = session.adapter_state.get(_active_proc_slot(session))
    if isinstance(proc, asyncio.subprocess.Process):
        return proc
    return None


# ---------------------------------------------------------------- error type


class ToolError(Exception):
    """Tool-level failure: the run loop emits a tool_result with is_error=true
    and lets the model recover. Not a session-fatal error."""


# ---------------------------------------------------------------- dispatcher


def _require_container(session: Session) -> str:
    """Return the session's container id or raise — every tool call needs one."""
    cid = session.container_id
    if cid is None:
        raise ToolError(
            "session has no sandbox container; this is a harness bug "
            "(container should have been provisioned at session creation)."
        )
    return cid


async def execute_tool(
    session: Session, name: str, arguments: dict[str, Any]
) -> str:
    """Run a single tool call. Returns the string output that goes back to
    the model. Raises ``ToolError`` for tool-level failures (caught by the
    run loop and surfaced as a tool_result with is_error=true)."""
    if name == "Bash":
        return await _bash(session, arguments)
    if name == "Read":
        return await _read(session, arguments)
    if name == "Edit":
        return await _edit(session, arguments)
    if name == "Write":
        return await _write(session, arguments)
    raise ToolError(f"Unknown tool: {name!r}")


# ---------------------------------------------------------------- helpers


def _require_str(args: dict[str, Any], key: str) -> str:
    val = args.get(key)
    if not isinstance(val, str):
        raise ToolError(f"missing or non-string argument: {key!r}")
    return val


def _validate_in_workdir(path: str) -> str:
    """Validate / normalize a tool-supplied path to a container-side path.

    Returns a normalized absolute path guaranteed to sit under ``/work``.
    Absolute inputs must start with ``/work/`` (or *be* ``/work``);
    relative inputs are joined onto ``/work``. ``..`` traversal that
    escapes ``/work`` is rejected.
    """
    if not path:
        raise ToolError("file_path must not be empty")
    if posixpath.isabs(path):
        candidate = posixpath.normpath(path)
    else:
        candidate = posixpath.normpath(posixpath.join(_CONTAINER_WORKDIR, path))
    if candidate != _CONTAINER_WORKDIR and not candidate.startswith(
        _CONTAINER_WORKDIR + "/"
    ):
        raise ToolError(
            f"file_path must be inside the working directory "
            f"({_CONTAINER_WORKDIR}): {path!r}"
        )
    return candidate


def _truncate(s: str) -> str:
    if len(s) <= BASH_OUTPUT_LIMIT:
        return s
    # Middle-truncation: keep head + tail so the model sees both
    # initial context and final errors/results.
    half = BASH_OUTPUT_LIMIT // 2
    return s[:half] + _TRUNC_SUFFIX + s[-half:]


async def _docker_exec(
    cid: str,
    argv: list[str],
    *,
    timeout_s: int,
    stdin: str | None = None,
) -> subprocess.CompletedProcess:
    """Run ``exec_in`` on a worker thread so the event loop stays free.

    ``subprocess.run`` (which ``exec_in`` wraps) is blocking, so naive use
    inside the async loop would serialize concurrent sessions on the
    network/docker call. ``to_thread`` keeps the loop responsive without
    pulling in an async docker client.
    """
    return await asyncio.to_thread(
        exec_in, cid, argv, timeout_s=timeout_s, stdin=stdin
    )


# ---------------------------------------------------------------- Bash


async def _bash(session: Session, args: dict[str, Any]) -> str:
    command = _require_str(args, "command")
    timeout_ms_raw = args.get("timeout", BASH_DEFAULT_TIMEOUT_MS)
    try:
        timeout_ms = int(timeout_ms_raw)
    except (TypeError, ValueError):
        raise ToolError(f"timeout must be an integer, got: {timeout_ms_raw!r}")
    timeout_ms = max(1, min(timeout_ms, BASH_MAX_TIMEOUT_MS))
    timeout_s = timeout_ms / 1000.0

    cid = _require_container(session)
    try:
        res = await _docker_exec(
            cid,
            ["bash", "-lc", command],
            # exec_in expects int seconds; round up so sub-second timeouts
            # still get at least 1s of headroom.
            timeout_s=max(1, int(timeout_s + 0.999)),
        )
    except subprocess.TimeoutExpired:
        return (
            f"<exit_code>-1</exit_code>\n"
            f"<error>Command timed out after {int(timeout_s * 1000)}ms</error>"
        )

    stdout = _truncate(res.stdout)
    stderr = _truncate(res.stderr)
    exit_code = res.returncode

    parts = [f"<exit_code>{exit_code}</exit_code>"]
    if stdout:
        parts.append(f"<stdout>\n{stdout}</stdout>")
    if stderr:
        parts.append(f"<stderr>\n{stderr}</stderr>")
    return "\n".join(parts)


# ---------------------------------------------------------------- Read


def _format_lines(lines: list[str], start_line: int) -> str:
    """cat -n style: 6-char right-aligned line number, tab, content."""
    out_parts: list[str] = []
    for idx, line in enumerate(lines):
        n = start_line + idx
        # Strip a single trailing newline before reattaching so the format
        # is exact: "{lineno}\t{content}\n".
        content = line.rstrip("\n")
        out_parts.append(f"{n:6d}\t{content}\n")
    return "".join(out_parts)


def _slice_text(text: str, offset_i: int, limit_i: int) -> str:
    """Apply (offset, limit) to *text* and format via _format_lines.

    Appends a system-reminder when the slice did not reach the end of
    the file so the model knows it can page further with offset/limit.
    """
    all_lines = text.splitlines(keepends=True)
    if not all_lines:
        return "<system-reminder>File exists but is empty.</system-reminder>"
    start_idx = max(0, offset_i - 1)
    total = len(all_lines)
    end_idx = min(total, start_idx + limit_i)
    chunk = all_lines[start_idx:end_idx]
    body = _format_lines(chunk, start_idx + 1)
    if end_idx < total:
        body += (
            f"<system-reminder>Showed lines {start_idx + 1}-{end_idx} of "
            f"{total}. Re-call Read with offset={end_idx + 1} to continue, "
            f"or raise limit.</system-reminder>"
        )
    return body


def _parse_offset_limit(args: dict[str, Any]) -> tuple[int, int]:
    offset = args.get("offset")
    limit = args.get("limit")
    try:
        offset_i = int(offset) if offset is not None else 1
        limit_i = int(limit) if limit is not None else READ_DEFAULT_LIMIT
    except (TypeError, ValueError):
        raise ToolError("offset and limit must be integers")
    if offset_i < 1:
        offset_i = 1
    if limit_i < 1:
        limit_i = 1
    return offset_i, limit_i


async def _read(session: Session, args: dict[str, Any]) -> str:
    file_path = _require_str(args, "file_path")
    cpath = _validate_in_workdir(file_path)
    cid = _require_container(session)

    # `head -c CAP` caps raw bytes at the docker layer so a multi-MB
    # binary blob can never be buffered into the harness or shipped to
    # the LLM. Same failure modes (missing file, is a directory) as cat.
    res = await _docker_exec(
        cid, ["head", "-c", str(READ_MAX_BYTES), cpath], timeout_s=30
    )
    if res.returncode != 0:
        # Distinguish "is a directory" from "no such file" using `test`
        # rather than parsing head's stderr (locale-dependent).
        probe = await _docker_exec(cid, ["test", "-d", cpath], timeout_s=10)
        if probe.returncode == 0:
            raise ToolError(f"path is a directory, not a file: {file_path}")
        probe = await _docker_exec(cid, ["test", "-e", cpath], timeout_s=10)
        if probe.returncode != 0:
            raise ToolError(f"file does not exist: {file_path}")
        raise ToolError(f"failed to read {file_path}: {res.stderr.strip()}")

    raw = res.stdout
    # Binary detection: a NUL byte in the head is the standard heuristic
    # (file(1), git). Refuse loudly so the model picks a domain tool
    # instead of dumping a SQLite/Parquet blob into its context.
    if "\x00" in raw[:8192]:
        raise ToolError(
            f"binary file: {file_path} contains NUL bytes. Use a domain "
            f"tool to inspect it (duckdb, geopandas, pyogrio, sqlite3, ...)."
        )

    offset_i, limit_i = _parse_offset_limit(args)
    formatted = _slice_text(raw, offset_i, limit_i)
    _read_set(session).add(cpath)
    return formatted


# ---------------------------------------------------------------- Edit


def _apply_edit(
    text: str, old_string: str, new_string: str, replace_all: bool, file_path: str
) -> tuple[str, int]:
    """Pure in-process substitution. Returns (new_text, count). Raises
    ToolError if the substitution can't proceed."""
    count = text.count(old_string)
    if count == 0:
        raise ToolError(f"old_string not found in {file_path}")
    if count > 1 and not replace_all:
        raise ToolError(
            f"old_string appears {count} times in {file_path}; "
            f"either provide more surrounding context to make it unique, "
            f"or pass replace_all=true."
        )
    new_text = (
        text.replace(old_string, new_string)
        if replace_all
        else text.replace(old_string, new_string, 1)
    )
    return new_text, count


async def _edit(session: Session, args: dict[str, Any]) -> str:
    file_path = _require_str(args, "file_path")
    old_string = _require_str(args, "old_string")
    new_string = args.get("new_string", "")
    if not isinstance(new_string, str):
        raise ToolError("new_string must be a string")
    replace_all = bool(args.get("replace_all", False))
    if old_string == new_string:
        raise ToolError("old_string and new_string are identical; no edit to make")

    cpath = _validate_in_workdir(file_path)
    cid = _require_container(session)

    if cpath not in _read_set(session):
        raise ToolError(
            f"file has not been Read in this session yet: {file_path}. "
            f"Use the Read tool first."
        )

    res = await _docker_exec(cid, ["cat", cpath], timeout_s=30)
    if res.returncode != 0:
        raise ToolError(f"file does not exist: {file_path}")

    new_text, count = _apply_edit(
        res.stdout, old_string, new_string, replace_all, file_path
    )

    write_res = await _docker_exec(
        cid,
        ["sh", "-c", 'mkdir -p "$(dirname "$1")" && cat > "$1"', "_", cpath],
        timeout_s=30,
        stdin=new_text,
    )
    if write_res.returncode != 0:
        raise ToolError(
            f"failed to write {file_path}: {write_res.stderr.strip()}"
        )

    if replace_all:
        return f"Edited {file_path}: replaced {count} occurrence(s)."
    return f"Edited {file_path}."


# ---------------------------------------------------------------- Write


async def _write(session: Session, args: dict[str, Any]) -> str:
    file_path = _require_str(args, "file_path")
    content = args.get("content", "")
    if not isinstance(content, str):
        raise ToolError("content must be a string")

    cpath = _validate_in_workdir(file_path)
    cid = _require_container(session)

    # If the file exists, enforce the Read-first guard.
    exists = await _docker_exec(cid, ["test", "-e", cpath], timeout_s=10)
    if exists.returncode == 0 and cpath not in _read_set(session):
        raise ToolError(
            f"file exists and has not been Read in this session yet: {file_path}. "
            f"Use the Read tool first."
        )

    write_res = await _docker_exec(
        cid,
        ["sh", "-c", 'mkdir -p "$(dirname "$1")" && cat > "$1"', "_", cpath],
        timeout_s=30,
        stdin=content,
    )
    if write_res.returncode != 0:
        raise ToolError(
            f"failed to write {file_path}: {write_res.stderr.strip()}"
        )

    # Writing counts as a Read for future Edits.
    _read_set(session).add(cpath)
    return f"Wrote {file_path} ({len(content)} chars)."


# ---------------------------------------------------------------- exports

# Re-exported for tests that want to drive copy_from directly.
__all__ = [
    "BASH_DEFAULT_TIMEOUT_MS",
    "BASH_MAX_TIMEOUT_MS",
    "BASH_OUTPUT_LIMIT",
    "TOOL_SCHEMAS",
    "ToolError",
    "execute_tool",
    "get_active_proc",
    "copy_from",
]
