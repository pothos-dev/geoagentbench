"""Reference solution for spa-l1-paris-amenity-within.

Reads the bundled two-layer GPKG (``amenities`` Points + ``arrondissements``
Polygons, both in EPSG:2154 Lambert-93), runs a ``within`` spatial join,
parses the integer arrondissement number out of the Overture-style French
ordinal name (``Paris 1er Arrondissement`` → 1, ``Paris 20e Arrondissement``
→ 20), and writes a flat CSV with one row per amenity:
``osm_id, amenity_class, arrondissement_number, arrondissement_name``.

Why this is straightforward at L1: both layers share a metric CRS, every
amenity in the bundle falls inside exactly one arrondissement (the
authoring helper clips amenities to the union of the 20 polygons), and
the only attribute-side wrinkle is parsing the French ordinal suffix.

Determinism: the output CSV is sorted by ``osm_id`` (a stable integer
assigned at authoring time). CSV has no metadata-timestamp wrinkle, so
two consecutive runs are byte-identical.

Output: ``outputs/amenity_to_arrondissement.csv`` with columns
``osm_id`` (int), ``amenity_class`` (str), ``arrondissement_number``
(int, 1–20), ``arrondissement_name`` (str, verbatim Overture name).
"""
from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_GPKG = TASK_DIR / "inputs" / "paris_amenities.gpkg"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "amenity_to_arrondissement.csv"

# Match the integer prefix on a Paris arrondissement name. Overture
# values are "Paris 1er Arrondissement" (1st, masculine ordinal),
# "Paris 2e Arrondissement", …, "Paris 20e Arrondissement". The
# leading "Paris " and the trailing " Arrondissement" are constant; the
# integer between them is what we want, suffix and all stripped.
_ARR_NUMBER_RE = re.compile(r"Paris\s+(\d+)\s*(?:er|e|ᵉ|ème)\s+Arrondissement", re.IGNORECASE)


def _arr_number(name: str) -> int:
    match = _ARR_NUMBER_RE.match(name)
    if match is None:
        raise ValueError(f"Could not parse arrondissement number from {name!r}")
    return int(match.group(1))


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    amen = gpd.read_file(INPUT_GPKG, layer="amenities")
    arr = gpd.read_file(INPUT_GPKG, layer="arrondissements")

    if amen.crs is None or amen.crs.to_epsg() != 2154:
        raise RuntimeError(f"Expected amenities CRS EPSG:2154; got {amen.crs}.")
    if arr.crs is None or arr.crs.to_epsg() != 2154:
        raise RuntimeError(f"Expected arrondissements CRS EPSG:2154; got {arr.crs}.")

    # Avoid the column-name collision on ``name`` from the join. The
    # arrondissement layer's ``name`` is what we want under
    # ``arrondissement_name``; the amenity layer's ``name`` we discard.
    arr_for_join = arr[["name", "geometry"]].rename(
        columns={"name": "arrondissement_name"}
    )

    joined = gpd.sjoin(
        amen[["osm_id", "amenity_class", "geometry"]],
        arr_for_join,
        how="left",
        predicate="within",
    )

    if joined["arrondissement_name"].isna().any():
        n_miss = int(joined["arrondissement_name"].isna().sum())
        raise RuntimeError(
            f"{n_miss} amenities did not fall inside any arrondissement; "
            "the bundled input is supposed to be pre-clipped."
        )

    joined["arrondissement_number"] = joined["arrondissement_name"].map(_arr_number)

    out = joined[
        ["osm_id", "amenity_class", "arrondissement_number", "arrondissement_name"]
    ].copy()
    out = out.sort_values("osm_id", kind="stable").reset_index(drop=True)

    out["osm_id"] = out["osm_id"].astype("int64")
    out["arrondissement_number"] = out["arrondissement_number"].astype("int64")

    if OUT.exists():
        OUT.unlink()
    out.to_csv(OUT, index=False)

    print(f"Wrote {len(out)} amenity-to-arrondissement rows to {OUT}")
    print("Sample (first 5):")
    print(out.head().to_string(index=False))
    by_arr = out.groupby("arrondissement_number").size().sort_index()
    print(f"\nAmenities per arrondissement:\n{by_arr.to_string()}")


if __name__ == "__main__":
    main()
