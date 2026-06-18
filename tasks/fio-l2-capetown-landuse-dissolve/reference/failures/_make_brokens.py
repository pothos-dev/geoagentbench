"""Generate broken-solution outputs for fio-l2-capetown-landuse-dissolve.

Three failure classes:

  * `broken_wrong_format`     — agent did not convert the input. Output
                                is the original FlatGeobuf renamed,
                                not GeoParquet. Gate 1 fails. Score 0.
  * `broken_wrong_area_units` — agent dissolved correctly and produced
                                a valid GeoParquet in EPSG:32734 with
                                MultiPolygons, but reported
                                `area_m2` in km² (off by 10⁶). Subcheck
                                `area_m2_per_class_within_tolerance`
                                fails; everything else passes.
  * `broken_partial_classes`  — agent dissolved only the top 10
                                classes by parcel_count. Class-set
                                Jaccard, row count, and unioned IoU
                                fail; per-class subchecks pass on the
                                included subset.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l2-capetown-landuse-dissolve/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_FGB = TASK_DIR / "inputs" / "capetown_landuse.fgb"
OUTPUT_NAME = "landuse_dissolved.geoparquet"
TARGET_CRS = "EPSG:32734"


def _to_multipolygon(geom):
    if geom is None or geom.is_empty:
        return MultiPolygon()
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    polys = [g for g in geom.geoms if g.geom_type == "Polygon"]
    multis = [g for g in geom.geoms if g.geom_type == "MultiPolygon"]
    for m in multis:
        polys.extend(list(m.geoms))
    return MultiPolygon(polys) if polys else MultiPolygon()


def _ensure(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / OUTPUT_NAME


def _dissolve(area_scale: float = 1.0, classes_subset: set[str] | None = None) -> gpd.GeoDataFrame:
    src = gpd.read_file(INPUT_FGB)
    if src.crs is None or src.crs.to_epsg() != 32734:
        src = src.to_crs(TARGET_CRS)
    rows = []
    for cls, group in src.groupby("class", sort=True):
        if classes_subset is not None and cls not in classes_subset:
            continue
        merged = unary_union(group.geometry.tolist())
        merged = _to_multipolygon(merged)
        rows.append(
            {
                "class": cls,
                "parcel_count": int(len(group)),
                "area_m2": float(merged.area) * area_scale,
                "geometry": merged,
            }
        )
    out = gpd.GeoDataFrame(rows, geometry="geometry", crs=TARGET_CRS)
    return out.sort_values("class", kind="stable").reset_index(drop=True)


def make_wrong_format() -> None:
    target = _ensure(HERE / "broken_wrong_format" / "outputs")
    if target.exists():
        target.unlink()
    # Copy the FlatGeobuf input across as if the agent forgot to convert.
    shutil.copyfile(INPUT_FGB, target)


def make_wrong_area_units() -> None:
    target = _ensure(HERE / "broken_wrong_area_units" / "outputs")
    out = _dissolve(area_scale=1e-6)  # km² instead of m²
    if target.exists():
        target.unlink()
    out.to_parquet(target, index=False)


def make_partial_classes() -> None:
    """Top 50 classes by parcel_count only — drops the long tail of
    singleton / sub-five-feature classes."""
    src = gpd.read_file(INPUT_FGB)
    if src.crs is None or src.crs.to_epsg() != 32734:
        src = src.to_crs(TARGET_CRS)
    counts = src["class"].value_counts()
    top50 = set(counts.head(50).index.tolist())
    out = _dissolve(area_scale=1.0, classes_subset=top50)
    target = _ensure(HERE / "broken_partial_classes" / "outputs")
    if target.exists():
        target.unlink()
    out.to_parquet(target, index=False)


def main() -> None:
    make_wrong_format()
    make_wrong_area_units()
    make_partial_classes()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
