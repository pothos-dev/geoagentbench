"""Wires the dispatcher run loop into the shared adapter app factory."""

from __future__ import annotations

import logging
import os

from adapter_core.app import create_app
from adapter_core.logging_config import configure_logging
from dispatcher import __version__
from dispatcher.dispatch import run_dispatcher, select_adapter

configure_logging()
log = logging.getLogger(__name__)


def _warn_missing_keys() -> None:
    if not os.environ.get("OPENROUTER_API_KEY"):
        log.warning(
            "OPENROUTER_API_KEY not set; all sessions will fail at agent start."
        )


_warn_missing_keys()


def _validate_model(model: str) -> None:
    """Front-door model validator. Raises ``ValueError`` on bare model ids."""
    select_adapter(model)


app = create_app(
    run_fn=run_dispatcher,
    adapter_name="harness",
    adapter_version=__version__,
    model_validator=_validate_model,
)
