"""Reference solution for geo-l1-capetown-building-centroids.

Reads the bundled Cape Town buildings shapefile (EPSG:32734, UTM 34S),
computes a per-feature centroid in the projected CRS (the planar
centroid is the meaningful one for a metric municipal layer; computing
in degrees would skew toward the equator), then reprojects the centroid
points to EPSG:4326 and writes them as GeoJSON with the original
building IDs.

Determinism: the input shapefile is already sorted by `building_id`;
the reference re-sorts after the centroid + reproject roundtrip to
guard against any internal shuffling.

The Shapefile dBase column-name limit truncates `building_id` to
`building_i` on disk. The reference renames it back to `building_id`
on output, matching what the persona explicitly asked for.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "capetown_buildings.shp"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "building_centroids.geojson"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT)

    # Recover the truncated dBase column name.
    if "building_i" in gdf.columns and "building_id" not in gdf.columns:
        gdf = gdf.rename(columns={"building_i": "building_id"})

    centroids = gdf.geometry.centroid
    out_gdf = gpd.GeoDataFrame(
        {"building_id": gdf["building_id"].astype(str), "geometry": centroids},
        geometry="geometry",
        crs=gdf.crs,
    )

    out_gdf = out_gdf.to_crs("EPSG:4326")
    out_gdf = out_gdf.sort_values("building_id", kind="stable").reset_index(
        drop=True
    )

    if OUT.exists():
        OUT.unlink()
    out_gdf.to_file(OUT, driver="GeoJSON")

    print(f"Read {len(gdf)} building polygons from {INPUT}")
    print(f"Wrote {len(out_gdf)} centroid points to {OUT}")
    print(f"Output CRS: {out_gdf.crs}")


if __name__ == "__main__":
    main()
