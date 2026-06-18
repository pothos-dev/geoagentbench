"""Reference solution for fio-l2-cairo-mixedgeom-split.

Reads the bundled mixed-geometry GeoJSON in EPSG:4326, stratifies the
features by geometry type, explodes any multi-part polygons into
singletons, reprojects everything to EPSG:22992 (Egypt Red Belt), and
writes a single GPKG with three named layers — `points`, `lines`,
`polygons` — each carrying the originating `site_id`.

Determinism: features within each layer are sorted by `(site_id,
feature_kind, part_index)` before write. The reference run is
bit-stable: deleting and rewriting the GPKG with the same input
produces an identical file.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "heritage_sites.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "heritage.gpkg"

TARGET_CRS = "EPSG:22992"

POLYGON_TYPES = {"Polygon", "MultiPolygon"}
LINE_TYPES = {"LineString", "MultiLineString"}
POINT_TYPES = {"Point", "MultiPoint"}

KEEP_ATTRS = ["site_id", "feature_kind", "name_en", "name_ar"]


def _explode_singletons(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Explode multi-part geometries into one feature per part."""
    exploded = gdf.explode(index_parts=True, ignore_index=False)
    # Add a stable part_index column derived from the exploded MultiIndex.
    part_idx = exploded.index.get_level_values(-1)
    exploded = exploded.reset_index(drop=True)
    exploded["part_index"] = part_idx.astype(int).values
    return exploded


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    src = gpd.read_file(INPUT)
    if src.crs is None:
        src.set_crs("EPSG:4326", inplace=True)

    geom_types = src.geometry.geom_type

    polys = src[geom_types.isin(POLYGON_TYPES)].copy()
    lines = src[geom_types.isin(LINE_TYPES)].copy()
    points = src[geom_types.isin(POINT_TYPES)].copy()

    polys = _explode_singletons(polys)
    lines["part_index"] = 0
    points["part_index"] = 0

    # Reproject to EPSG:22992 (Egypt Red Belt — projected metres).
    polys = polys.to_crs(TARGET_CRS)
    lines = lines.to_crs(TARGET_CRS)
    points = points.to_crs(TARGET_CRS)

    sort_cols = ["site_id", "feature_kind", "part_index"]

    polys = polys.sort_values(sort_cols, kind="stable").reset_index(drop=True)
    lines = lines.sort_values(sort_cols, kind="stable").reset_index(drop=True)
    points = points.sort_values(sort_cols, kind="stable").reset_index(drop=True)

    output_cols = KEEP_ATTRS + ["part_index", "geometry"]
    polys = polys[output_cols]
    lines = lines[output_cols]
    points = points[output_cols]

    if OUT.exists():
        OUT.unlink()
    # Write three layers into the same GPKG.
    points.to_file(OUT, layer="points", driver="GPKG")
    lines.to_file(OUT, layer="lines", driver="GPKG")
    polys.to_file(OUT, layer="polygons", driver="GPKG")

    # GPKG embeds per-write timestamps in `gpkg_contents.last_change`,
    # which makes two consecutive runs differ at the byte level even
    # when the feature data is identical. Normalise the timestamps and
    # VACUUM the SQLite container so the bundled output is bit-stable.
    import sqlite3

    with sqlite3.connect(OUT) as con:
        con.execute(
            "UPDATE gpkg_contents SET last_change = '2026-01-01T00:00:00.000Z'"
        )
        con.commit()
        con.execute("VACUUM")

    print(f"Read {len(src)} mixed-geometry features from {INPUT}")
    print(f"Wrote {OUT}")
    print(f"  points layer:   {len(points)} features ({TARGET_CRS})")
    print(f"  lines layer:    {len(lines)} features ({TARGET_CRS})")
    print(f"  polygons layer: {len(polys)} features ({TARGET_CRS}, exploded)")


if __name__ == "__main__":
    main()
