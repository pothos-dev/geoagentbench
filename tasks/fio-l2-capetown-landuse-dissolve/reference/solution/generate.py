"""Reference solution for fio-l2-capetown-landuse-dissolve.

Reads the bundled Cape Town land-use FlatGeobuf in EPSG:32734, dissolves
features by `class`, collects the per-class geometries into a single
MultiPolygon per class, computes `area_m2` (sum of dissolved geometry
area in projected metres) and `parcel_count` (input feature count per
class), and writes the result as a GeoParquet in EPSG:32734.

Determinism: rows are sorted by `class` (lexicographic) before writing.
GeoParquet writes are bit-stable for fixed input + GeoPandas/PyArrow
versions in the project Docker image.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "capetown_landuse.fgb"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "landuse_dissolved.geoparquet"

TARGET_CRS = "EPSG:32734"


def _to_multipolygon(geom):
    """Coerce a (Multi)Polygon-like geometry to MultiPolygon."""
    if geom is None or geom.is_empty:
        return MultiPolygon()
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    # Could be a GeometryCollection from union — keep only polygonal parts.
    polys = [g for g in geom.geoms if g.geom_type == "Polygon"]
    multis = [g for g in geom.geoms if g.geom_type == "MultiPolygon"]
    for m in multis:
        polys.extend(list(m.geoms))
    return MultiPolygon(polys) if polys else MultiPolygon()


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    src = gpd.read_file(INPUT)
    if src.crs is None or src.crs.to_epsg() != 32734:
        src = src.to_crs(TARGET_CRS)

    # Group by class, union geometries, collect to MultiPolygon, sum area.
    rows = []
    for cls, group in src.groupby("class", sort=True):
        merged = unary_union(group.geometry.tolist())
        merged = _to_multipolygon(merged)
        rows.append(
            {
                "class": cls,
                "parcel_count": int(len(group)),
                "area_m2": float(merged.area),
                "geometry": merged,
            }
        )

    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=TARGET_CRS)
    out = out.sort_values("class", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    out.to_parquet(OUT, index=False)

    print(f"Read {len(src)} parcels from {INPUT}")
    print(f"Wrote {len(out)} dissolved classes → {OUT}")
    print(out[["class", "parcel_count", "area_m2"]].to_string(index=False))


if __name__ == "__main__":
    main()
