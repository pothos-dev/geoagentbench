"""Reference solution for crs-l1-nyc-webmercator-cycleways.

Reads the bundled NYC cycleway segments in EPSG:3857 (Web Mercator), reprojects
to EPSG:4326 (WGS84), and writes the result as GeoParquet.

Determinism: input is already sorted by `id` at authoring time; we sort again
defensively and write with pyarrow so two consecutive runs produce byte-
identical output. No attribute changes — Marcus asked for the data unchanged
otherwise.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent.parent
INPUT = TASK_DIR / "inputs" / "nyc_cycleways_webmercator.geoparquet"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "nyc_cycleways_wgs84.geoparquet"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_parquet(INPUT)

    gdf = gdf.to_crs("EPSG:4326")

    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    gdf.to_parquet(OUT)
    print(f"Wrote {len(gdf)} features to {OUT}")
    print(f"CRS: {gdf.crs.to_epsg()}")
    print(f"Bounds: {tuple(round(v, 6) for v in gdf.total_bounds)}")


if __name__ == "__main__":
    main()
