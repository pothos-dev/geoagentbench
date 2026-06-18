"""Load named adapter targets from `adapters.yaml`."""
from __future__ import annotations

from pathlib import Path

import yaml

from eval.core.runner import AdapterTarget

EVAL_ROOT = Path(__file__).resolve().parent.parent.parent
ADAPTERS_FILE = EVAL_ROOT / "adapters.yaml"


def load_adapters(path: Path = ADAPTERS_FILE) -> dict[str, AdapterTarget]:
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    out: dict[str, AdapterTarget] = {}
    for name, cfg in (raw.get("adapters") or {}).items():
        out[name] = AdapterTarget(
            url=cfg["url"],
            name=name,
            label=cfg.get("label"),
            headers=dict(cfg.get("headers") or {}),
            max_concurrent_sessions=cfg.get("max_concurrent_sessions"),
            attributes=dict(cfg.get("attributes") or {}),
        )
    return out


def get_adapter(name: str) -> AdapterTarget:
    adapters = load_adapters()
    if name not in adapters:
        raise SystemExit(
            f"unknown adapter {name!r}; known: {sorted(adapters)}"
        )
    return adapters[name]
