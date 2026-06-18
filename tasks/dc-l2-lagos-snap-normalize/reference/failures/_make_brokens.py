"""Generate broken-solution outputs for dc-l2-lagos-snap-normalize.

Three classes, each isolating a different operation in the pipeline so
the grader's subchecks land in distinct score ranges:

  - broken_wrong_format        — Output reprojected to EPSG:3857 instead
                                 of EPSG:26331. Gate 1 rejects → 0.0.
  - broken_no_snap             — Skip the 1 mm vertex snap; every other
                                 step (drop zero-area, normalise,
                                 filter blanks, dissolve, recompute
                                 area) runs. unary_union still
                                 produces four polygonal results but
                                 each is a MultiPolygon riddled with
                                 sub-mm sliver holes. Strict
                                 Polygon-only and no-interior-holes
                                 subchecks fail; per-class area, IoU,
                                 and the rest pass. Mid score.
  - broken_wrong_canonical     — Snap, drop zero-area, dissolve,
                                 recompute area, but emit the four
                                 canonical classes as ALL-CAPS
                                 (`RESIDENTIAL`/`COMMERCIAL`/...) instead
                                 of the persona's TitleCase. Only the
                                 canonical-vocabulary subcheck fails;
                                 every other check passes. High
                                 partial score.

Run inside Docker:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dc-l2-lagos-snap-normalize/reference/failures/_make_brokens.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT = TASK_DIR / "inputs" / "lagos_zoning_legacy.gpkg"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "zoning_aggregated.gpkg"
OUTPUT_NAME = "zoning_aggregated.gpkg"

FIXED_GPKG_TIMESTAMP = "2026-05-08T00:00:00.000Z"

CANONICAL_CLASSES = ("Residential", "Commercial", "Industrial", "Agricultural")
_PREFIX_TABLE = (
    ("resi", "Residential"),
    ("comm", "Commercial"),
    ("indus", "Industrial"),
    ("ind", "Industrial"),
    ("agri", "Agricultural"),
)


def _normalise_class(raw: object) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    key = s.casefold().rstrip(".").rstrip()
    for prefix, canonical in _PREFIX_TABLE:
        if key.startswith(prefix):
            return canonical
    return ""


def _stamp(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            "UPDATE gpkg_contents SET last_change = ?", (FIXED_GPKG_TIMESTAMP,)
        )
        con.commit()
    finally:
        con.close()


def _write(out_dir: Path, gdf: gpd.GeoDataFrame) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_NAME
    if target.exists():
        target.unlink()
    gdf.to_file(target, driver="GPKG", layer="zoning_aggregated")
    _stamp(target)


def make_wrong_format() -> None:
    """Write the reference output reprojected to EPSG:3857. Gate 1's
    CRS check rejects it. Score = 0.
    """
    out_dir = HERE / "broken_wrong_format" / "outputs"
    gdf = gpd.read_file(REFERENCE_OUT).to_crs(3857)
    _write(out_dir, gdf)


def make_no_snap() -> None:
    """Skip the 1 mm snap. Run every other step (drop zero-area,
    normalise class, filter blanks, dissolve, recompute area). The
    per-quadrant areas drift below 250 000 m² because adjacent parcels
    no longer share vertices exactly — the dissolved polygons pick up
    interior holes along every internal grid line. Gate 1 / Gate 2 /
    canonical-class / no-blank / no-zero / area-recompute pass; the
    per-class-area, IoU, and no-interior-holes subchecks fail.
    """
    out_dir = HERE / "broken_no_snap" / "outputs"

    gdf = gpd.read_file(INPUT)
    gdf = gdf[gdf.geometry.area > 0].reset_index(drop=True)
    gdf = gdf.assign(zoning_class=gdf["zoning_class"].map(_normalise_class))
    gdf = gdf[gdf["zoning_class"].astype(str).str.len() > 0].reset_index(drop=True)

    out_rows: list[dict] = []
    for canonical in sorted(CANONICAL_CLASSES):
        sub = gdf[gdf["zoning_class"] == canonical]
        if sub.empty:
            continue
        merged = unary_union(sub.geometry.tolist())
        out_rows.append(
            {
                "zoning_class": canonical,
                "area_m2": float(merged.area),
                "geometry": merged,
            }
        )

    out = gpd.GeoDataFrame(
        pd.DataFrame(out_rows), geometry="geometry", crs=gdf.crs
    )
    out = out.sort_values("zoning_class", kind="stable").reset_index(drop=True)
    out["area_m2"] = out["area_m2"].astype(float).round(4)
    _write(out_dir, out)


def make_wrong_canonical() -> None:
    """Run every step correctly but emit the four canonical classes as
    ALL-CAPS instead of the persona's TitleCase. The
    canonical_class_vocabulary subcheck fails; every other check
    passes.
    """
    out_dir = HERE / "broken_wrong_canonical" / "outputs"
    gdf = gpd.read_file(REFERENCE_OUT)
    gdf = gdf.assign(zoning_class=gdf["zoning_class"].str.upper())
    _write(out_dir, gdf)


def main() -> None:
    make_wrong_format()
    make_no_snap()
    make_wrong_canonical()
    print("Wrote three broken solutions.")


if __name__ == "__main__":
    main()
