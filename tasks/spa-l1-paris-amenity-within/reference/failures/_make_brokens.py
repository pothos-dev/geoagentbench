"""Generate broken-solution outputs for spa-l1-paris-amenity-within.

Three classes, chosen to give the grader resolution along the
*format / number-shape / name-shape* axes the task probes:

  - broken_wrong_format         — Gate 1 fail. The agent dropped the
                                  ``arrondissement_number`` column
                                  entirely. Score collapses to 0.

  - broken_kept_ordinal_suffix  — Gate 1 / 2 pass. The agent did the
                                  spatial join correctly but left
                                  ``arrondissement_number`` as the
                                  French ordinal string ("1er", "2e",
                                  …, "20e") — exactly the gotcha the
                                  persona warned about. Two subchecks
                                  fail: ``arrondissement_number_is_
                                  integer_1_to_20`` and the per-row
                                  number match. → 4/6 ≈ 0.67.

  - broken_name_used_id         — Gate 1 / 2 pass. The agent did the
                                  spatial join correctly but pulled
                                  the arrondissement *Overture id*
                                  instead of the *name* into the
                                  ``arrondissement_name`` column (a
                                  common confusion when both layers
                                  carry an ``id`` and a ``name``).
                                  Only the per-row name match fails.
                                  → 5/6 ≈ 0.83.

Each broken score range is recorded in metadata.yaml.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l1-paris-amenity-within/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_GPKG = TASK_DIR / "inputs" / "paris_amenities.gpkg"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "amenity_to_arrondissement.csv"
OUTPUT_NAME = "amenity_to_arrondissement.csv"

ORDINAL_MAP = {
    1: "1er",
    **{n: f"{n}e" for n in range(2, 21)},
}


def _write_csv(target: Path, df: pd.DataFrame) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    df.to_csv(target, index=False)


def make_wrong_format() -> None:
    """Drop ``arrondissement_number`` from a copy of the reference.
    Gate 1's required-column check fails. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    target = out_dir / OUTPUT_NAME
    ref = pd.read_csv(REFERENCE_OUT)
    ref = ref.drop(columns=["arrondissement_number"])
    _write_csv(target, ref)


def make_kept_ordinal_suffix() -> None:
    """Re-emit the reference but with ``arrondissement_number`` left as
    the French ordinal string ("1er", "2e", …, "20e") — the gotcha
    spelled out in the persona's instruction.
    """
    out_dir = HERE / "broken_kept_ordinal_suffix" / "outputs"
    target = out_dir / OUTPUT_NAME
    ref = pd.read_csv(REFERENCE_OUT)
    ref["arrondissement_number"] = ref["arrondissement_number"].map(ORDINAL_MAP)
    _write_csv(target, ref)


def make_name_used_id() -> None:
    """Re-emit the reference but swap ``arrondissement_name`` for the
    arrondissement Overture *id* (the agent confused id and name when
    projecting from the spatial-join result).
    """
    out_dir = HERE / "broken_name_used_id" / "outputs"
    target = out_dir / OUTPUT_NAME

    arr = gpd.read_file(INPUT_GPKG, layer="arrondissements")
    name_to_id = dict(zip(arr["name"], arr["id"]))

    ref = pd.read_csv(REFERENCE_OUT)
    ref["arrondissement_name"] = ref["arrondissement_name"].map(name_to_id)
    if ref["arrondissement_name"].isna().any():
        raise RuntimeError("name_to_id mapping incomplete; check inputs.")
    _write_csv(target, ref)


def main() -> None:
    make_wrong_format()
    make_kept_ordinal_suffix()
    make_name_used_id()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
