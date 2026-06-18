"""Entry point: `python -m dispatcher` runs the harness under uvicorn."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "dispatcher.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("HARNESS_PORT", "8080")),
        log_config=None,  # logging is configured by dispatcher.app at import
    )


if __name__ == "__main__":
    main()
