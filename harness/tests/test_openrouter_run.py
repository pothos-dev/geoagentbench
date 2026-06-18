"""Unit tests for the OpenRouter agent loop.

The OpenAI ``AsyncOpenAI`` client is replaced with a scripted mock that
emits a pre-baked sequence of ChatCompletion-shaped responses. The loop
runs against the mock, then we assert on the events appended to the
session and the request history captured by the mock.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from adapter_core.sessions import Session


# ---------------------------------------------------------------- mock plumbing


class _MockFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _MockToolCall:
    def __init__(self, id: str, name: str, arguments: dict | str) -> None:
        self.id = id
        self.function = _MockFunction(
            name, arguments if isinstance(arguments, str) else json.dumps(arguments)
        )


class _MockMessage:
    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[_MockToolCall] | None = None,
        reasoning: str | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls
        self.reasoning = reasoning
        self.model_extra: dict[str, Any] = {}
        if reasoning is not None:
            self.model_extra["reasoning"] = reasoning


class _MockChoice:
    def __init__(self, message: _MockMessage, finish_reason: str = "stop") -> None:
        self.message = message
        self.finish_reason = finish_reason


class _MockUsage:
    def __init__(self, cost: float = 0.0) -> None:
        self.prompt_tokens = 10
        self.completion_tokens = 5
        self.total_tokens = 15
        self.model_extra: dict[str, Any] = {"cost": cost}


class _MockResponse:
    def __init__(
        self,
        message: _MockMessage,
        finish_reason: str = "stop",
        cost: float = 0.001,
    ) -> None:
        self.choices = [_MockChoice(message, finish_reason)]
        self.usage = _MockUsage(cost)


class _MockCompletions:
    def __init__(self, scripted: list[_MockResponse]) -> None:
        self._scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> _MockResponse:
        self.calls.append(kwargs)
        if not self._scripted:
            raise RuntimeError("mock ran out of scripted responses")
        return self._scripted.pop(0)


class _MockChat:
    def __init__(self, scripted: list[_MockResponse]) -> None:
        self.completions = _MockCompletions(scripted)


class _MockAsyncOpenAI:
    """Stand-in for openai.AsyncOpenAI that returns scripted responses."""

    last_instance: "_MockAsyncOpenAI | None" = None

    def __init__(self, scripted: list[_MockResponse], **_kwargs: Any) -> None:
        self.chat = _MockChat(scripted)
        type(self).last_instance = self


def _patch_openai(scripted: list[_MockResponse]):
    """Patch openai.AsyncOpenAI to return a scripted mock."""

    def factory(**kwargs: Any) -> _MockAsyncOpenAI:
        return _MockAsyncOpenAI(scripted, **kwargs)

    return patch("openai.AsyncOpenAI", factory)


# ---------------------------------------------------------------- fixtures


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    s = Session(session_id="sid", work_dir=tmp_path)
    s.model_override = "openai/gpt-4o-mini"
    return s


# ---------------------------------------------------------------- tests


async def test_stop_immediately(session: Session) -> None:
    """No tool calls → loop emits text and returns."""
    scripted = [_MockResponse(_MockMessage(content="hello"), cost=0.0005)]
    with _patch_openai(scripted):
        from openrouter.run import run_openrouter

        await run_openrouter(session, "say hi")

    types = [(e.type, e.role) for e in session.events]
    assert ("system", None) in types
    assert ("text", "assistant") in types
    assert session.usage.estimated_cost_usd == pytest.approx(0.0005)
    assert session.usage.model == "openai/gpt-4o-mini"


async def test_single_tool_call_then_stop(session: Session) -> None:
    scripted = [
        _MockResponse(
            _MockMessage(
                content=None,
                tool_calls=[_MockToolCall("c1", "Bash", {"command": "echo hi"})],
            ),
            finish_reason="tool_calls",
            cost=0.0001,
        ),
        _MockResponse(_MockMessage(content="done"), cost=0.0002),
    ]
    with _patch_openai(scripted):
        from openrouter.run import run_openrouter

        await run_openrouter(session, "echo hi")

    types = [e.type for e in session.events]
    assert "tool_call" in types
    assert "tool_result" in types
    # Cost accumulated across both turns.
    assert session.usage.estimated_cost_usd == pytest.approx(0.0003)


async def test_parallel_tool_calls_executed_in_order(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Mock execute_tool so the test doesn't need a real sandbox container.
    # We just want to assert that the two tool calls are dispatched in
    # the order they appear on the assistant turn.
    seen_calls: list[str] = []

    async def fake_execute_tool(sess, name, args):
        seen_calls.append(args["file_path"])
        return f"output for {args['file_path']}"

    monkeypatch.setattr("openrouter.run.execute_tool", fake_execute_tool)

    scripted = [
        _MockResponse(
            _MockMessage(
                content=None,
                tool_calls=[
                    _MockToolCall("c1", "Read", {"file_path": "/work/a.txt"}),
                    _MockToolCall("c2", "Read", {"file_path": "/work/b.txt"}),
                ],
            ),
            finish_reason="tool_calls",
        ),
        _MockResponse(_MockMessage(content="done")),
    ]
    with _patch_openai(scripted):
        from openrouter.run import run_openrouter

        await run_openrouter(session, "read both")

    assert seen_calls == ["/work/a.txt", "/work/b.txt"]
    tool_results = [e for e in session.events if e.type == "tool_result"]
    assert len(tool_results) == 2
    assert "/work/a.txt" in tool_results[0].content["output"]
    assert "/work/b.txt" in tool_results[1].content["output"]


async def test_malformed_tool_args_become_error_result(session: Session) -> None:
    scripted = [
        _MockResponse(
            _MockMessage(
                content=None,
                tool_calls=[_MockToolCall("c1", "Bash", "not json {{")],
            ),
            finish_reason="tool_calls",
        ),
        _MockResponse(_MockMessage(content="recovered")),
    ]
    with _patch_openai(scripted):
        from openrouter.run import run_openrouter

        await run_openrouter(session, "x")

    tool_result = next(e for e in session.events if e.type == "tool_result")
    assert tool_result.content["is_error"] is True
    assert "Invalid JSON" in tool_result.content["output"]


async def test_unknown_tool_name_becomes_error_result(session: Session) -> None:
    scripted = [
        _MockResponse(
            _MockMessage(
                content=None,
                tool_calls=[_MockToolCall("c1", "Frobnicate", {})],
            ),
            finish_reason="tool_calls",
        ),
        _MockResponse(_MockMessage(content="ok")),
    ]
    with _patch_openai(scripted):
        from openrouter.run import run_openrouter

        await run_openrouter(session, "x")

    tool_result = next(e for e in session.events if e.type == "tool_result")
    assert tool_result.content["is_error"] is True
    assert "Unknown tool" in tool_result.content["output"]


async def test_thinking_event_emitted_when_reasoning_present(session: Session) -> None:
    scripted = [
        _MockResponse(_MockMessage(content="hi", reasoning="step 1: hello"))
    ]
    with _patch_openai(scripted):
        from openrouter.run import run_openrouter

        await run_openrouter(session, "x")

    thinking = [e for e in session.events if e.type == "thinking"]
    assert len(thinking) == 1
    assert thinking[0].content == "step 1: hello"


async def test_missing_api_key_fails_session(tmp_path: Path) -> None:
    s = Session(session_id="sid", work_dir=tmp_path)
    s.model_override = "openai/gpt-4o-mini"
    # No OPENROUTER_API_KEY set.
    import os

    os.environ.pop("OPENROUTER_API_KEY", None)
    from openrouter.run import run_openrouter

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        await run_openrouter(s, "x")


async def test_max_iterations_exceeded(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("openrouter.run.MAX_ITERATIONS", 3)
    # Always returns a tool call → loop never terminates naturally.
    def looping_response() -> _MockResponse:
        return _MockResponse(
            _MockMessage(
                content=None,
                tool_calls=[_MockToolCall("c", "Bash", {"command": "echo loop"})],
            ),
            finish_reason="tool_calls",
        )

    scripted = [looping_response() for _ in range(10)]
    with _patch_openai(scripted):
        from openrouter.run import run_openrouter

        with pytest.raises(RuntimeError, match="max iterations"):
            await run_openrouter(session, "loop")
