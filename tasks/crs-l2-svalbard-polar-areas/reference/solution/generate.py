"""Reference solution for crs-l2-svalbard-polar-areas.

Pipeline:
1. Read the bundled named-glacier polygons over Svalbard in EPSG:4326.
2. Reproject to EPSG:3575 (WGS 84 / North Pole LAEA Europe). LAEA is
   equal-area by construction, so polygon areas are mathematically
   exact rather than approximate-via-conformal-stretch. The "Europe"
   variant places Svalbard near the central meridian (10°E), giving
   bbox values aligned with the longitude band.
3. Compute per-feature polygon area in km² and the per-feature
   axis-aligned bounding box, both in the projected CRS.
4. Sort by area descending and keep the top 20.
5. Write the result as CSV with columns
   ``name, area_km2, bbox_minx_polar, bbox_miny_polar,
   bbox_maxx_polar, bbox_maxy_polar, crs_epsg`` — where
   ``crs_epsg`` declares the projection used (3575) so the
   grader can validate against the same frame.

Determinism: input is pre-sorted by name+id at authoring time, the
top-20 ranking is by a strict numeric area, and ties (none expected
here) would be broken by the stable name+id input order. No random
state, no dict-ordering reliance.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent  # reference/solution/
TASK_DIR = HERE.parent.parent  # task root
INPUT = TASK_DIR / "inputs" / "svalbard_glaciers_wgs84.gpkg"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "svalbard_glaciers_top20.csv"

TARGET_EPSG = 3575  # WGS 84 / North Pole LAEA Europe (equal-area)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)

    polar = gdf.to_crs(epsg=TARGET_EPSG)

    polar["area_km2"] = polar.geometry.area / 1_000_000.0

    bounds = polar.geometry.bounds.rename(
        columns={
            "minx": "bbox_minx_polar",
            "miny": "bbox_miny_polar",
            "maxx": "bbox_maxx_polar",
            "maxy": "bbox_maxy_polar",
        }
    )
    polar = pd.concat([polar.drop(columns=[]), bounds], axis=1)
    polar["crs_epsg"] = TARGET_EPSG

    polar = polar.sort_values(
        ["area_km2", "name", "id"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)

    top20 = polar.head(20)[
        [
            "name",
            "area_km2",
            "bbox_minx_polar",
            "bbox_miny_polar",
            "bbox_maxx_polar",
            "bbox_maxy_polar",
            "crs_epsg",
        ]
    ]

    if OUT.exists():
        OUT.unlink()
    top20.to_csv(OUT, index=False)
    print(f"Wrote {len(top20)} rows to {OUT}")
    print(top20.to_string())


if __name__ == "__main__":
    main()
