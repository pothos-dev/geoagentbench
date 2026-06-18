"""Generate broken-solution outputs for fio-l2-cairo-mixedgeom-split.

Each broken solution targets a different failure class:

  * `broken_wrong_format`        — agent wrote a single GeoJSON
                                   instead of a multi-layer GPKG.
                                   Gate 1 fails. Score 0.
  * `broken_no_explode`          — agent wrote the three layers in
                                   the right CRS with site_id, but
                                   left MultiPolygons in the polygons
                                   layer (no explode). Gate 1 / 2
                                   pass; subchecks
                                   `polygons_singletons_only` and
                                   `polygons_count_within_tolerance`
                                   fail.
  * `broken_geom_corruption`     — agent wrote the three layers in
                                   EPSG:22992, exploded polygons, but
                                   reprojected with x/y swapped. Gate
                                   1 / 2 pass; geometry-related
                                   subchecks (polygons IoU, points
                                   per-site) fail.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l2-cairo-mixedgeom-split/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_GEOJSON = TASK_DIR / "inputs" / "heritage_sites.geojson"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "heritage.gpkg"
OUTPUT_NAME = "heritage.gpkg"

TARGET_CRS = "EPSG:22992"
KEEP_ATTRS = ["site_id", "feature_kind", "name_en", "name_ar"]
POLYGON_TYPES = {"Polygon", "MultiPolygon"}
LINE_TYPES = {"LineString", "MultiLineString"}
POINT_TYPES = {"Point", "MultiPoint"}


def _ensure(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / OUTPUT_NAME


def _normalise_timestamps(path: Path) -> None:
    """Stamp gpkg_contents.last_change to a fixed value (deterministic)."""
    with sqlite3.connect(path) as con:
        con.execute(
            "UPDATE gpkg_contents SET last_change = '2026-01-01T00:00:00.000Z'"
        )
        con.commit()
        con.execute("VACUUM")


def make_wrong_format() -> None:
    """Agent left output as a single mixed-geometry GeoJSON.
    Gate 1 fails — it's not even a GPKG.
    """
    target = _ensure(HERE / "broken_wrong_format" / "outputs")
    if target.exists():
        target.unlink()
    # Copy the original input across as if the agent forgot to convert.
    shutil.copyfile(INPUT_GEOJSON, target)


def _stratify_and_reproject(
    explode: bool, swap_xy: bool
) -> dict[str, gpd.GeoDataFrame]:
    src = gpd.read_file(INPUT_GEOJSON)
    if src.crs is None:
        src.set_crs("EPSG:4326", inplace=True)

    types = src.geometry.geom_type
    polys = src[types.isin(POLYGON_TYPES)].copy()
    lines = src[types.isin(LINE_TYPES)].copy()
    points = src[types.isin(POINT_TYPES)].copy()

    if explode:
        polys = polys.explode(index_parts=True, ignore_index=False)
        polys["part_index"] = polys.index.get_level_values(-1).astype(int).values
        polys = polys.reset_index(drop=True)
    else:
        polys["part_index"] = 0
    lines["part_index"] = 0
    points["part_index"] = 0

    polys = polys.to_crs(TARGET_CRS)
    lines = lines.to_crs(TARGET_CRS)
    points = points.to_crs(TARGET_CRS)

    if swap_xy:
        # Swap x/y after reprojecting — keeps coordinate magnitudes in
        # the right CRS-range (so the gate still passes) while breaking
        # the actual location of every feature.
        from shapely.affinity import affine_transform

        def _swap(g):
            if g is None:
                return None
            return affine_transform(g, [0, 1, 1, 0, 0, 0])

        polys["geometry"] = polys.geometry.map(_swap)
        lines["geometry"] = lines.geometry.map(_swap)
        points["geometry"] = points.geometry.map(_swap)

    sort_cols = ["site_id", "feature_kind", "part_index"]
    polys = polys.sort_values(sort_cols, kind="stable").reset_index(drop=True)
    lines = lines.sort_values(sort_cols, kind="stable").reset_index(drop=True)
    points = points.sort_values(sort_cols, kind="stable").reset_index(drop=True)

    output_cols = KEEP_ATTRS + ["part_index", "geometry"]
    return {
        "points": points[output_cols],
        "lines": lines[output_cols],
        "polygons": polys[output_cols],
    }


def _write_layers(layers: dict[str, gpd.GeoDataFrame], target: Path) -> None:
    if target.exists():
        target.unlink()
    layers["points"].to_file(target, layer="points", driver="GPKG")
    layers["lines"].to_file(target, layer="lines", driver="GPKG")
    layers["polygons"].to_file(target, layer="polygons", driver="GPKG")
    _normalise_timestamps(target)


def make_no_explode() -> None:
    target = _ensure(HERE / "broken_no_explode" / "outputs")
    layers = _stratify_and_reproject(explode=False, swap_xy=False)
    _write_layers(layers, target)


def make_geom_corruption() -> None:
    target = _ensure(HERE / "broken_geom_corruption" / "outputs")
    layers = _stratify_and_reproject(explode=True, swap_xy=True)
    _write_layers(layers, target)


def main() -> None:
    make_wrong_format()
    make_no_explode()
    make_geom_corruption()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
