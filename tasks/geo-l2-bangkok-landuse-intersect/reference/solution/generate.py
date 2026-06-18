"""Reference solution for geo-l2-bangkok-landuse-intersect.

Pipeline:
  1. Read bundled Bangkok land-cover GeoParquet (EPSG:32647).
  2. Repair invalid geometries with shapely.make_valid (some features
     have self-intersecting bowtie rings — the persona's complaint).
  3. Read the BMA study-area GeoJSON and union into a single geometry.
  4. Intersect each repaired land-cover polygon with the study area;
     drop empty intersections.
  5. Coerce result geometry to MultiPolygon.
  6. Simplify each MultiPolygon at a 5 m tolerance (planar coords).
  7. Compute `area_m2` per surviving feature (planar metres² in
     EPSG:32647).
  8. Sort by stable Overture `id`, reproject to WGS84, and write
     GeoJSON in EPSG:4326. `area_m2` stays in projected metres².

Determinism: rows sorted by `id`. GeoPandas/pyogrio GeoJSON writes are
byte-stable for fixed inputs and pinned dependency versions.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_LC = TASK_DIR / "inputs" / "bangkok_landcover.parquet"
INPUT_SA = TASK_DIR / "inputs" / "bma_study_area.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "bma_landcover_intersect.geojson"

WORK_CRS = "EPSG:32647"  # metric CRS for all geometry + area math
OUTPUT_CRS = "EPSG:4326"  # WGS84; RFC 7946 GeoJSON write CRS
SIMPLIFY_TOL = 5.0


def _to_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    polys = []
    for g in getattr(geom, "geoms", []):
        if g.is_empty:
            continue
        if g.geom_type == "Polygon":
            polys.append(g)
        elif g.geom_type == "MultiPolygon":
            polys.extend(list(g.geoms))
    return MultiPolygon(polys) if polys else None


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    lc = gpd.read_parquet(INPUT_LC)
    if lc.crs is None or lc.crs.to_epsg() != 32647:
        lc = lc.to_crs(WORK_CRS)

    sa = gpd.read_file(INPUT_SA)
    if sa.crs is None or sa.crs.to_epsg() != 32647:
        sa = sa.to_crs(WORK_CRS)
    study_geom = unary_union(sa.geometry.tolist())

    rows = []
    for _, row in lc.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if not geom.is_valid:
            geom = make_valid(geom)
        clipped = geom.intersection(study_geom)
        mp = _to_multipolygon(clipped)
        if mp is None or mp.is_empty:
            continue
        simplified = mp.simplify(SIMPLIFY_TOL, preserve_topology=True)
        mp = _to_multipolygon(simplified)
        if mp is None or mp.is_empty:
            continue
        rows.append(
            {
                "id": row["id"],
                "class": row["class"],
                "area_m2": float(mp.area),
                "geometry": mp,
            }
        )

    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=WORK_CRS)
    out = out.sort_values("id", kind="stable").reset_index(drop=True)
    out = out.to_crs(OUTPUT_CRS)

    if OUT.exists():
        OUT.unlink()
    out.to_file(OUT, driver="GeoJSON")

    print(f"Read {len(lc)} land-cover polygons, study-area = {study_geom.area:.0f} m²")
    print(f"Wrote {len(out)} intersected features → {OUT}")
    print(out["class"].value_counts().to_string())
    print(f"Total intersected area: {out['area_m2'].sum():.0f} m²")


if __name__ == "__main__":
    main()
