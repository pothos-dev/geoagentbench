"""Structured JSON logging configuration."""

from __future__ import annotations

import logging
import os

from pythonjsonlogger import jsonlogger


def configure_logging() -> None:
    level = os.environ.get("HARNESS_LOG_LEVEL", "info").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "ts", "levelname": "level"},
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Quiet noisy libraries.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
