"""Reference solution for crs-l1-london-laea-areas.

Reads the bundled WGS84 GeoJSON of London-area administrative units, reprojects
to EPSG:3035 (ETRS89-extended / LAEA Europe) for area-correct computation,
computes per-feature polygon area in square kilometres, and writes a CSV with
id, name, area_km2.

The task instruction does NOT specify which projection to use — the model must
independently recognise that computing area on WGS84 (lat/lon) coordinates is
meaningless and choose an appropriate projected CRS.  The reference uses
EPSG:3035 (equal-area); the grader accepts any reasonable projection within a
2 % per-feature tolerance.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent.parent
INPUT = TASK_DIR / "inputs" / "london_admin.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "borough_areas.csv"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)

    gdf = gdf.to_crs("EPSG:3035")

    gdf["area_km2"] = gdf.geometry.area / 1_000_000.0

    result = gdf[["id", "name", "area_km2"]].sort_values(
        ["name", "id"], kind="stable"
    ).reset_index(drop=True)

    result.to_csv(OUT, index=False)
    print(f"Wrote {len(result)} rows to {OUT}")


if __name__ == "__main__":
    main()
