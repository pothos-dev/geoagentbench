"""Generate broken-solution outputs by perturbing the reference output.

Run inside Docker:
    docker run --rm -v "$PWD":/work geo-bench-author \
        uv run python tasks/crs-l1-london-laea-areas/reference/failures/_make_brokens.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent.parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "borough_areas.csv"
INPUT_WGS84 = TASK_DIR / "inputs" / "london_admin.geojson"


def make_wrong_format() -> None:
    """The agent wrote GeoJSON instead of CSV.

    Gate 1 fails because the expected CSV file is missing. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT_WGS84)
    gdf["area_km2"] = gdf.geometry.area
    gdf.to_file(out_dir / "borough_areas.geojson", driver="GeoJSON")
    # The grader looks for borough_areas.csv, which is absent → score 0


def make_degrees_area() -> None:
    """The agent computed .area on WGS84 geometry without reprojecting.

    Values are in degrees² — orders of magnitude wrong. Gate 1 passes (CSV
    with correct columns), gate 2 passes (correct row count), but area
    subchecks fail catastrophically. Name/id subchecks pass.
    """
    out_dir = HERE / "broken_degrees_area" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT_WGS84)
    # degrees² — completely wrong for area in km²
    result = gdf[["id", "name"]].copy()
    result["area_km2"] = gdf.geometry.area
    result = result.sort_values(["name", "id"], kind="stable").reset_index(drop=True)
    result.to_csv(out_dir / "borough_areas.csv", index=False)


def make_area_m2() -> None:
    """The agent reprojected correctly but reported area in m² not km².

    Off by a factor of 1e6. Name/id checks pass, area checks fail.
    """
    out_dir = HERE / "broken_area_m2" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ref = pd.read_csv(REFERENCE_OUT)
    ref["area_km2"] = ref["area_km2"] * 1_000_000.0
    ref.to_csv(out_dir / "borough_areas.csv", index=False)


def main() -> None:
    make_wrong_format()
    make_degrees_area()
    make_area_m2()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
