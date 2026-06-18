"""Generate broken-solution outputs for dd-l2-bangkok-multicrs-audit.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l2-bangkok-multicrs-audit/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "crs_audit.csv"
OUTPUT_NAME = "crs_audit.csv"

CSV_FIELDS = (
    "layer_name",
    "declared_crs",
    "geometry_type",
    "feature_count",
    "sample_x",
    "sample_y",
    "encoding_detected",
)


def _load_ref() -> list[dict]:
    with REFERENCE_OUT.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write(out_dir: Path, rows: list[dict], fields=CSV_FIELDS) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fields})


def make_wrong_format() -> None:
    """Agent emitted a JSON file (still named crs_audit.csv) instead of a
    CSV — common confusion when the persona's instruction emphasises a
    structured table. Gate 1 rejects on parseable-CSV / required-columns.
    Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    with target.open("w", encoding="utf-8") as f:
        json.dump({"layers": _load_ref()}, f, indent=2)


def make_partial_layers() -> None:
    """Agent only opened the first layer it found and wrote a single
    audit row, ignoring the rest of the GPKG. `layers_complete` fails
    plus the two missing layers' 5×2 = 10 subchecks fail; the surviving
    layer's 5 subchecks pass. → 5 / 16 ≈ 0.3125.
    """
    ref = _load_ref()
    kept = [r for r in ref if r["layer_name"] == "markets"]
    _write(HERE / "broken_partial_layers" / "outputs", kept)


def make_wrong_encoding() -> None:
    """Agent enumerated all layers and read CRS / geometry / count
    correctly, but skipped the Latin-1 mojibake heuristic and reported
    every layer as `utf-8`. Two of three layers' encoding subchecks
    flip; everything else still passes.
    → 14 / 16 = 0.875.
    """
    ref = _load_ref()
    perturbed = [
        {**r, "encoding_detected": "utf-8"} for r in ref
    ]
    _write(HERE / "broken_wrong_encoding" / "outputs", perturbed)


def main() -> None:
    make_wrong_format()
    make_partial_layers()
    make_wrong_encoding()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
