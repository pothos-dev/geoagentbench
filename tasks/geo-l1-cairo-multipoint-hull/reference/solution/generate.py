"""Reference solution for geo-l1-cairo-multipoint-hull.

Reads `data/cairo_metro_stations.geojson` (one MultiPoint per station,
plus bilingual `station_name_ar` / `station_name_en` attributes) and
writes `outputs/cairo_metro_hulls.geojson` — one convex-hull Polygon
per station, attributes preserved.

Determinism: the input file is already sorted by `station_name_en`;
the reference re-sorts by the same key after the hull operation to
guard against any internal shuffling, then writes GeoJSON in
EPSG:4326.

Note on degenerate hulls: a station's MultiPoint with only 3 entrances
yields a triangle; with 4 collinear-ish points the hull may still be a
Polygon (shapely's convex_hull returns a Polygon when the points span
2-D, otherwise a LineString or Point). The bundled input is generated
with seeded uniform offsets and 3+ entrances, so every hull lands as a
Polygon — no special-casing needed here.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "cairo_metro_stations.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "cairo_metro_hulls.geojson"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    gdf = gpd.read_file(INPUT)

    hulls = gdf.geometry.convex_hull
    out_gdf = gpd.GeoDataFrame(
        {
            "station_name_en": gdf["station_name_en"].astype(str),
            "station_name_ar": gdf["station_name_ar"].astype(str),
            "geometry": hulls,
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    out_gdf = out_gdf.sort_values("station_name_en", kind="stable").reset_index(
        drop=True
    )

    if OUT.exists():
        OUT.unlink()
    out_gdf.to_file(OUT, driver="GeoJSON")

    print(f"Read {len(gdf)} stations from {INPUT}")
    print(f"Wrote {len(out_gdf)} hull polygons to {OUT}")
    geom_types = set(out_gdf.geom_type)
    print(f"Hull geometry types: {sorted(geom_types)}")


if __name__ == "__main__":
    main()
