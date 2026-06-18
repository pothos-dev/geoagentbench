"""OpenRouter agent loop.

Drives a chat-completions loop against an OpenAI-compatible OpenRouter
endpoint. Non-streaming: one ``chat.completions.create`` per turn, full
message back. Parallel tool calls in a single assistant turn are executed
sequentially in returned order. Hard cap on iterations prevents runaway.

Cost is read from ``response.usage.cost`` (OpenRouter extension to the
OpenAI ``usage`` block, accessed via pydantic v2 ``model_extra``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from adapter_core.prompts import system_prompt
from adapter_core.sessions import Session
from openrouter.config import (
    APP_TITLE,
    BASE_URL,
    DEFAULT_MODEL,
    HTTP_REFERER,
    IDLE_TIMEOUT,
    MAX_ITERATIONS,
)
from openrouter.tools import (
    TOOL_SCHEMAS,
    ToolError,
    execute_tool,
)

log = logging.getLogger(__name__)


async def run_openrouter(session: Session, instruction: str) -> None:
    """Drive the agent loop until the model stops or the iteration cap hits."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not configured")

    # Import lazily so the dispatcher can start even if the openai package
    # isn't installed (it always will be in the production image, but unit
    # tests that don't touch OpenRouter shouldn't need to import it).
    from openai import AsyncOpenAI

    model = session.model_override or DEFAULT_MODEL
    session.set_model(model)

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        timeout=IDLE_TIMEOUT,
        max_retries=3,
        default_headers={
            "HTTP-Referer": HTTP_REFERER,
            "X-Title": APP_TITLE,
        },
    )

    # Synthetic system event for parity with Claude Code's stream-json init.
    session.append_event(
        type="system",
        content=json.dumps(
            {"adapter": "openrouter", "model": model, "base_url": BASE_URL},
            separators=(",", ":"),
        ),
    )

    messages: list[dict[str, Any]] = [
        # Tool calls execute inside the per-session sandbox container, whose
        # workdir is /work — NOT the host-side `session.work_dir` (that's the
        # eval-runner-visible staging dir for docker cp).
        {"role": "system", "content": system_prompt(session.prompt_variant, work_dir="/work")},
        {"role": "user", "content": instruction},
    ]

    try:
        for iteration in range(MAX_ITERATIONS):
            response = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                tools=TOOL_SCHEMAS,  # type: ignore[arg-type]
                tool_choice="auto",
            )
            _accumulate_cost(session, response)

            choice = response.choices[0]
            message = choice.message
            finish_reason = choice.finish_reason

            # Emit thinking event if the model surfaced reasoning content.
            reasoning = _extract_reasoning(message)
            if reasoning:
                session.append_event(
                    type="thinking", role="assistant", content=reasoning
                )

            # Emit assistant text (may be empty for tool-only turns).
            text_content = message.content or ""
            if text_content:
                session.append_event(
                    type="text", role="assistant", content=text_content
                )

            tool_calls = message.tool_calls or []

            # Build the assistant message echo for the next request. OpenAI
            # requires tool_calls to be present when we then send tool replies.
            assistant_echo: dict[str, Any] = {
                "role": "assistant",
                "content": text_content,
            }
            if tool_calls:
                assistant_echo["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ]
            messages.append(assistant_echo)

            if not tool_calls:
                # Natural stop. finish_reason may be "stop", "length", etc.
                if finish_reason and finish_reason != "stop":
                    log.info(
                        "openrouter loop ended with finish_reason=%r", finish_reason
                    )
                return

            # Execute tool calls sequentially in returned order.
            for tc in tool_calls:
                name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                arguments: dict[str, Any]
                try:
                    arguments = json.loads(raw_args)
                    if not isinstance(arguments, dict):
                        raise ValueError("arguments must decode to an object")
                except (json.JSONDecodeError, ValueError) as exc:
                    session.append_event(
                        type="tool_call",
                        role="assistant",
                        content={"name": name, "arguments": raw_args},
                    )
                    err_text = f"Invalid JSON arguments: {exc}"
                    session.append_event(
                        type="tool_result",
                        content={"name": name, "output": err_text, "is_error": True},
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": err_text,
                        }
                    )
                    continue

                session.append_event(
                    type="tool_call",
                    role="assistant",
                    content={"name": name, "arguments": arguments},
                )

                try:
                    output = await execute_tool(session, name, arguments)
                    is_error = False
                except ToolError as exc:
                    output = str(exc)
                    is_error = True

                session.append_event(
                    type="tool_result",
                    content={"name": name, "output": output, "is_error": is_error},
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output,
                    }
                )

        # Fell out of the for-loop: iteration cap hit.
        raise RuntimeError(f"max iterations exceeded ({MAX_ITERATIONS})")

    except asyncio.CancelledError:
        # Tool calls execute via docker exec on a worker thread; cancellation
        # at the asyncio level returns control here while the exec may still
        # be in flight on the daemon. Session teardown (stop_session_container
        # on DELETE) is what actually kills the in-flight command.
        raise


def _extract_reasoning(message: Any) -> str:
    """Pull reasoning content off a chat completion message if present.

    OpenRouter normalizes thinking-model output onto ``message.reasoning``
    (string). The official openai types don't declare it, so we check both
    the attribute and pydantic v2's ``model_extra`` bucket.
    """
    reasoning = getattr(message, "reasoning", None)
    if isinstance(reasoning, str) and reasoning:
        return reasoning
    extra = getattr(message, "model_extra", None) or {}
    val = extra.get("reasoning")
    if isinstance(val, str):
        return val
    return ""


def _accumulate_cost(session: Session, response: Any) -> None:
    """Read ``usage.cost`` (OpenRouter extension) and add to session usage.

    Returns silently if the field is missing (e.g., free-tier models, or a
    future API change), so a missing cost doesn't break the run."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    extra = getattr(usage, "model_extra", None) or {}
    cost = extra.get("cost")
    if isinstance(cost, (int, float)):
        session.add_cost(float(cost))
