"""Reference solution for geo-l1-tokyo-busstop-buffer.

Reads the bundled WGS84 Tokyo connectors GeoJSON, reprojects to EPSG:6677
(JGD2011 Plane IX — the canonical metric CRS for the Tokyo region), computes
a 400 m planar buffer around each Point, and writes the result as GeoParquet.

The task instruction does NOT specify which CRS to use — the model must
independently recognise that buffering in WGS84 degrees is meaningless and
choose an appropriate projected CRS.  The reference uses EPSG:6677.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "tokyo_connectors.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "tokyo_stop_catchments.geoparquet"

BUFFER_M = 400.0


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT)

    # Reproject to a metric CRS for honest buffering
    gdf = gdf.to_crs("EPSG:6677")

    buffered = gdf.geometry.buffer(BUFFER_M)
    out_gdf = gpd.GeoDataFrame(
        {
            "connector_id": gdf["connector_id"].astype(str),
            "geometry": buffered,
        },
        geometry="geometry",
        crs="EPSG:6677",
    )

    out_gdf = out_gdf.sort_values("connector_id", kind="stable").reset_index(
        drop=True
    )

    if OUT.exists():
        OUT.unlink()
    out_gdf.to_parquet(OUT)

    print(f"Read {len(gdf)} connector points from {INPUT}")
    print(f"Wrote {len(out_gdf)} buffer polygons to {OUT}")
    print(f"Output CRS: {out_gdf.crs}")
    print(f"Buffer radius: {BUFFER_M} m (planar, EPSG:6677)")


if __name__ == "__main__":
    main()
