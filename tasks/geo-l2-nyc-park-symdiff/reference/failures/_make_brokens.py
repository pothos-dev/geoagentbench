"""Generate broken-solution outputs for geo-l2-nyc-park-symdiff.

Three failure classes:

  * `broken_wrong_format`  — anchors file is written as GeoParquet
                             (or any non-GeoJSON) under the GeoJSON
                             output name. Gate 1 rejects. Score 0.

  * `broken_partial`       — agent dropped ~30 % of clusters (e.g.
                             only emitted clusters from one side of
                             the symdiff). Subchecks
                             `count_within_tolerance`,
                             `total_area_within_tolerance`, and
                             `source_label_distribution` (per-source
                             count tolerance) all fail; multipolygon /
                             IoU / anchors-inside still pass.

  * `broken_centroids`     — agent used the geometric centroid as
                             the label anchor instead of
                             representative_point(). Centroids of
                             concave or multi-part disagreement
                             clusters often fall outside the geometry.
                             Subcheck `anchors_inside_disagreements`
                             fails; everything else passes.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REF_OUT = TASK_DIR / "reference" / "solution" / "outputs"
INPUT_GPKG = TASK_DIR / "inputs" / "nyc_parks.gpkg"
OUT_DISAGREEMENT = "parks_disagreement.geojson"
OUT_ANCHORS = "park_label_anchors.geojson"
TARGET_CRS = "EPSG:4326"


def _ensure(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def make_wrong_format() -> None:
    """Anchors file is GeoParquet under the GeoJSON-named path."""
    out_dir = _ensure(HERE / "broken_wrong_format" / "outputs")
    # Disagreement file: copy the reference (so Gate 1 only fails on
    # anchors). Demonstrates that gate-1 fails closed if any one of the
    # two outputs is malformed.
    shutil.copyfile(REF_OUT / OUT_DISAGREEMENT, out_dir / OUT_DISAGREEMENT)
    # Anchors written as GeoParquet under the GeoJSON name.
    ref_anchors = gpd.read_file(REF_OUT / OUT_ANCHORS)
    target = out_dir / OUT_ANCHORS
    if target.exists():
        target.unlink()
    ref_anchors.to_parquet(target, index=False)


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


def _polygon_parts(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return [p for p in geom.geoms if not p.is_empty]
    parts = []
    for g in getattr(geom, "geoms", []):
        parts.extend(_polygon_parts(g))
    return parts


def make_partial() -> None:
    """Agent emitted only the clusters from one side of the symdiff.

    Drops the `parks_official`-only clusters (20 of them) entirely,
    leaving 26 clusters out of the reference 46 (≈ 43 % drop). Gate 2
    (±50 %) still passes; count, area, and source-distribution
    subchecks all fail. Multipoly / IoU / anchors-inside pass.
    """
    out_dir = _ensure(HERE / "broken_partial" / "outputs")
    ref_d = gpd.read_file(REF_OUT / OUT_DISAGREEMENT)
    ref_a = gpd.read_file(REF_OUT / OUT_ANCHORS)
    keep_mask = ref_d["source"].astype(str) != "parks_official"
    sub_d = ref_d[keep_mask].copy().reset_index(drop=True)
    sub_a = ref_a[keep_mask.values].copy().reset_index(drop=True)
    target_d = out_dir / OUT_DISAGREEMENT
    target_a = out_dir / OUT_ANCHORS
    if target_d.exists():
        target_d.unlink()
    if target_a.exists():
        target_a.unlink()
    sub_d.to_file(target_d, driver="GeoJSON")
    sub_a.to_file(target_a, driver="GeoJSON")


def make_centroids() -> None:
    """Used centroid instead of representative_point for anchors."""
    out_dir = _ensure(HERE / "broken_centroids" / "outputs")
    shutil.copyfile(REF_OUT / OUT_DISAGREEMENT, out_dir / OUT_DISAGREEMENT)
    d = gpd.read_file(REF_OUT / OUT_DISAGREEMENT)
    a_rows = []
    for _, row in d.iterrows():
        a_rows.append(
            {
                "cluster_id": int(row.cluster_id),
                "source": row.source,
                "geometry": row.geometry.centroid,
            }
        )
    a_gdf = gpd.GeoDataFrame(a_rows, geometry="geometry", crs=TARGET_CRS)
    target_a = out_dir / OUT_ANCHORS
    if target_a.exists():
        target_a.unlink()
    a_gdf.to_file(target_a, driver="GeoJSON")


def main() -> None:
    make_wrong_format()
    make_partial()
    make_centroids()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
