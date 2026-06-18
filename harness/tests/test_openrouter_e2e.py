"""End-to-end tests against the real OpenRouter API.

Skipped when ``OPENROUTER_API_KEY`` is not set. Uses ``openai/gpt-4o-mini``
($0.15/$0.60 per Mtok) — a full run of this file is typically <$0.05.

Mark: ``e2e``. Run with ``pytest -m e2e``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from adapter_core.sessions import Session

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get("OPENROUTER_API_KEY"),
        reason="OPENROUTER_API_KEY not set",
    ),
]


CHEAP_MODEL = "openai/gpt-4o-mini"


@pytest.fixture
def session(tmp_path: Path) -> Session:
    s = Session(session_id="e2e-sid", work_dir=tmp_path)
    s.model_override = CHEAP_MODEL
    return s


async def test_empty_task_records_cost(session: Session) -> None:
    """Smoke test: tiny prompt, no tools, assert cost is captured."""
    from openrouter.run import run_openrouter

    await run_openrouter(session, "Say exactly the word 'hi' and nothing else.")

    types = [e.type for e in session.events]
    assert "system" in types
    assert "text" in types
    assert session.usage.estimated_cost_usd > 0
    assert session.usage.model == CHEAP_MODEL


async def test_single_bash_tool_call(session: Session) -> None:
    """Model uses Bash to produce a file in the working directory."""
    from openrouter.run import run_openrouter

    await run_openrouter(
        session,
        "Use the Bash tool to create a file named 'hi.txt' in the current "
        "directory containing exactly the text 'hello'. Then stop.",
    )

    target = session.work_dir / "hi.txt"
    assert target.exists(), f"model did not create hi.txt; events={session.events}"
    assert "hello" in target.read_text()

    types = [e.type for e in session.events]
    assert "tool_call" in types
    assert "tool_result" in types


async def test_write_then_run_python(session: Session) -> None:
    """Multi-turn: model writes a script and executes it."""
    from openrouter.run import run_openrouter

    await run_openrouter(
        session,
        "Write a Python file named 'solve.py' that prints exactly the line "
        "'OK 42'. Then run it with 'python3 solve.py' and stop.",
    )

    assert (session.work_dir / "solve.py").exists()
    # Check the tool_result captured the expected output.
    tool_results = [e for e in session.events if e.type == "tool_result"]
    combined = " ".join(
        r.content.get("output", "") if isinstance(r.content, dict) else ""
        for r in tool_results
    )
    assert "OK 42" in combined
