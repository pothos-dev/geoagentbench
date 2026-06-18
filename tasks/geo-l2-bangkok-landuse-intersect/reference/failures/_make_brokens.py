"""Generate broken-solution outputs for geo-l2-bangkok-landuse-intersect.

Three failure classes:

  * `broken_wrong_format`     — agent wrote a GeoParquet (or anything
                                non-GeoJSON) under the expected name.
                                Gate 1 rejects. Score 0.
  * `broken_not_intersected`  — agent repaired and simplified but
                                forgot the intersection step. Output is
                                the full bundled land-cover (after
                                make_valid + simplify), in EPSG:32647,
                                with `class` and `area_m2`. Gate 2 still
                                passes (the loosened ±50 % gate accepts
                                ~21 k vs reference 3 453: |Δ|/max ≈
                                0.84 — wait, that exceeds 50 %. So we
                                instead emit *only the polygons fully
                                outside* the study area? No — emit a
                                middle-ground broken: agent applied a
                                bbox filter by study-area bbox but did
                                not do the geometric clip. Result count
                                is closer to the reference but areas
                                are wrong (uncliped polygons retain
                                their full extent, not the clipped
                                slice). Subchecks count, area, and IoU
                                fail; class set still passes;
                                multipolygon passes.
  * `broken_area_in_km2`      — agent did everything right but reported
                                `area_m2` in km² (off by 10⁶).
                                Subcheck `total_area_within_tolerance`
                                fails; everything else passes.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_LC = TASK_DIR / "inputs" / "bangkok_landcover.parquet"
INPUT_SA = TASK_DIR / "inputs" / "bma_study_area.geojson"
OUTPUT_NAME = "bma_landcover_intersect.geojson"
TARGET_CRS = "EPSG:32647"
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


def _ensure(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / OUTPUT_NAME


def _build(area_scale: float = 1.0, do_intersect: bool = True) -> gpd.GeoDataFrame:
    lc = gpd.read_parquet(INPUT_LC)
    if lc.crs is None or lc.crs.to_epsg() != 32647:
        lc = lc.to_crs(TARGET_CRS)
    sa = gpd.read_file(INPUT_SA)
    if sa.crs is None or sa.crs.to_epsg() != 32647:
        sa = sa.to_crs(TARGET_CRS)
    study_geom = unary_union(sa.geometry.tolist())
    sa_bounds = study_geom.bounds  # for non-intersected variant: bbox prefilter only

    rows = []
    for _, row in lc.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if not geom.is_valid:
            geom = make_valid(geom)
        if do_intersect:
            geom = geom.intersection(study_geom)
        else:
            # Cheaper bbox filter: drop polygons whose bbox does not
            # touch the study-area bbox at all. Keeps geometries
            # un-clipped — the explicit "forgot to clip" defect.
            minx, miny, maxx, maxy = geom.bounds
            if (
                maxx < sa_bounds[0]
                or minx > sa_bounds[2]
                or maxy < sa_bounds[1]
                or miny > sa_bounds[3]
            ):
                continue
        mp = _to_multipolygon(geom)
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
                "area_m2": float(mp.area) * area_scale,
                "geometry": mp,
            }
        )
    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=TARGET_CRS)
    return out.sort_values("id", kind="stable").reset_index(drop=True)


def make_wrong_format() -> None:
    """Agent emitted GeoParquet under the GeoJSON-named output path."""
    target = _ensure(HERE / "broken_wrong_format" / "outputs")
    if target.exists():
        target.unlink()
    out = _build(do_intersect=True)
    # Write GeoParquet bytes under the GeoJSON filename — Gate 1 sees
    # "looks-like-not-JSON" and rejects.
    out.to_parquet(target, index=False)


def make_not_intersected() -> None:
    """Agent applied bbox prefilter only, did not clip to study area."""
    target = _ensure(HERE / "broken_not_intersected" / "outputs")
    if target.exists():
        target.unlink()
    out = _build(do_intersect=False)
    out.to_file(target, driver="GeoJSON")


def make_area_in_km2() -> None:
    """Agent reported area_m2 in km² (off by 10⁶)."""
    target = _ensure(HERE / "broken_area_in_km2" / "outputs")
    if target.exists():
        target.unlink()
    out = _build(area_scale=1e-6, do_intersect=True)
    out.to_file(target, driver="GeoJSON")


def main() -> None:
    make_wrong_format()
    make_not_intersected()
    make_area_in_km2()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
