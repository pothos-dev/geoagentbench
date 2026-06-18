"""Static configuration for the OpenRouter adapter."""

from __future__ import annotations

import os

BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.environ.get("OPENROUTER_DEFAULT_MODEL", "openai/gpt-4o-mini")

# Hard cap on tool-call rounds per session. Failures from hitting this are
# legitimate "model couldn't converge" signals, not harness bugs.
MAX_ITERATIONS = int(os.environ.get("OPENROUTER_MAX_ITERATIONS", "50"))

# Per-request timeout in seconds passed to the OpenAI client. The client
# handles retries (max_retries=3) with exponential backoff internally.
IDLE_TIMEOUT = int(os.environ.get("OPENROUTER_IDLE_TIMEOUT", "180"))

# Optional analytics headers OpenRouter recommends. Cosmetic; no defaults
# necessary, but a thesis project benefits from being identifiable in the
# OpenRouter dashboard.
HTTP_REFERER = os.environ.get(
    "OPENROUTER_REFERER", "https://github.com/dnlllr/bachelor-thesis"
)
APP_TITLE = os.environ.get("OPENROUTER_TITLE", "bachelor-thesis-benchmark")
