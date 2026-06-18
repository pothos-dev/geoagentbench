"""Reference solution for dd-l1-london-parks-count.

Reads `data/london_parks.fgb` (FlatGeobuf, EPSG:27700, polygons of
OSM-style parks), filters to features whose footprint is at least
1 hectare (10 000 m²), and writes a JSON summary with three keys:
  * count           — int, number of parks above the threshold
  * total_area_ha   — float, sum of those parks' areas in hectares
  * bbox_wgs84      — list[float], [xmin, ymin, xmax, ymax] in EPSG:4326

Determinism notes: the bundled FlatGeobuf is committed; pyogrio reads
features in file order; the `.area` calculation is exact in
EPSG:27700 (planar metres). The output JSON is written with a fixed
key order and `total_area_ha` rounded to 4 decimal places (≈ 1 m²
resolution) so two consecutive runs are byte-identical.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "london_parks.fgb"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "parks_summary.json"

THRESHOLD_HA = 1.0
M2_PER_HA = 10_000.0


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)
    assert gdf.crs is not None and gdf.crs.to_epsg() == 27700, (
        f"Expected EPSG:27700 input, got {gdf.crs}"
    )

    area_m2 = gdf.geometry.area
    keep = area_m2 >= THRESHOLD_HA * M2_PER_HA
    subset = gdf.loc[keep].copy()

    count = int(len(subset))
    total_area_ha = round(float(area_m2[keep].sum()) / M2_PER_HA, 4)

    # Reproject the subset to WGS84 for the bbox; bbox is computed
    # *after* reprojection so the lat/lon extents enclose the actual
    # geometries, not the back-projected EPSG:27700 envelope corners.
    subset_wgs84 = subset.to_crs("EPSG:4326")
    xmin, ymin, xmax, ymax = (float(v) for v in subset_wgs84.total_bounds)

    summary = {
        "count": count,
        "total_area_ha": total_area_ha,
        "bbox_wgs84": [xmin, ymin, xmax, ymax],
    }

    if OUT.exists():
        OUT.unlink()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Read {len(gdf)} park polygons from {INPUT}")
    print(f"{count} parks ≥ {THRESHOLD_HA} ha, total {total_area_ha} ha")
    print(f"bbox_wgs84: [{xmin}, {ymin}, {xmax}, {ymax}]")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
