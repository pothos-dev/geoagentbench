"""Model-name based adapter routing.

Only OpenRouter is supported. A valid ``X-Harness-Model`` value must contain
a ``/`` provider prefix (e.g. ``openai/gpt-4o``, ``google/gemma-4-26b-a4b-it``).
Bare model ids (``opus``, ``sonnet``, ``haiku``, …) used to route to the
Claude Code adapter; that adapter was removed in PR3 and the dispatcher
now rejects those requests with a 400 at session-start time.
"""

from __future__ import annotations

import logging

from adapter_core.sessions import Session
from openrouter.run import run_openrouter

log = logging.getLogger(__name__)


CLAUDE_CODE_REMOVED_ERROR = (
    'Claude Code adapter has been removed; route models via OpenRouter '
    '(model ID must contain a provider prefix, e.g. '
    '"google/gemma-4-26b-a4b-it").'
)


class UnsupportedModelError(ValueError):
    """Raised when the requested model id has no provider prefix (``/``).

    The HTTP layer surfaces this as a 400 Bad Request — the session never
    even gets created, so we never pretend to dispatch and crash later.
    """


def select_adapter(model: str | None) -> str:
    """Return ``"openrouter"`` for a routable model id; raise otherwise.

    OpenRouter is the only supported backend. A model id without a ``/``
    has no provider prefix and is rejected with :class:`UnsupportedModelError`.
    """
    if model and "/" in model:
        return "openrouter"
    raise UnsupportedModelError(CLAUDE_CODE_REMOVED_ERROR)


async def run_dispatcher(session: Session, instruction: str) -> None:
    # select_adapter() already ran at session-creation time via the HTTP
    # layer; by the time we get here the model is guaranteed to be valid.
    # Re-check defensively so a bug in the HTTP layer doesn't silently route
    # a bare model id to the wrong place.
    adapter = select_adapter(session.model_override)
    log.info(
        "dispatcher: routing session %s (model=%r) -> %s",
        session.session_id,
        session.model_override,
        adapter,
    )
    await run_openrouter(session, instruction)
