"""Unit tests for the slash-heuristic adapter routing.

After PR3 only OpenRouter is supported. A model id without a provider
prefix (``/``) raises ``UnsupportedModelError`` so the HTTP layer can
surface a 400 at session-creation time.
"""

from __future__ import annotations

import pytest

from dispatcher.dispatch import (
    CLAUDE_CODE_REMOVED_ERROR,
    UnsupportedModelError,
    select_adapter,
)


def test_openrouter_ids_have_provider_slash() -> None:
    for m in (
        "openai/gpt-4o-mini",
        "anthropic/claude-3-opus",
        "google/gemini-2.5-pro",
        "deepseek/deepseek-v3",
    ):
        assert select_adapter(m) == "openrouter"


def test_no_header_rejected() -> None:
    with pytest.raises(UnsupportedModelError):
        select_adapter(None)


def test_empty_string_rejected() -> None:
    with pytest.raises(UnsupportedModelError):
        select_adapter("")


def test_bare_model_id_rejected() -> None:
    for m in ("opus", "sonnet", "haiku", "claude-opus-4-7", "gpt-4o-mini"):
        with pytest.raises(UnsupportedModelError) as exc_info:
            select_adapter(m)
        # The error message tells the caller how to fix it.
        assert "OpenRouter" in str(exc_info.value)


def test_error_message_is_actionable() -> None:
    """The 400 body should point at the provider-prefix requirement."""
    assert "provider prefix" in CLAUDE_CODE_REMOVED_ERROR
    assert "/" in CLAUDE_CODE_REMOVED_ERROR
