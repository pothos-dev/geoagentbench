"""Grader for geo-l1-tokyo-busstop-buffer.

The task gives WGS84 connector points and asks for a 400 m buffer around each.
No output CRS is specified — the model must independently choose a projected
CRS suitable for metric buffering in the Tokyo region.

The grader reprojects the submission to EPSG:6677 (the reference CRS) for all
geometric comparisons, so the output CRS does not matter as long as the
buffering was done correctly in a metric CRS.

Hard gate (`format_schema_valid`) — file exists, parses as GeoParquet,
has `connector_id` column. No CRS check (grader reprojects).

Subchecks:
  1. connector_id populated for every row.
  2. connector_id set Jaccard vs reference >= 0.95.
  3. Per-id buffer area within ±2% of pi * 400^2 (after reprojection to
     EPSG:6677) for >= 95% of rows.
  4. Per-id IoU vs reference >= 0.95 (in EPSG:6677) for >= 95% of common
     ids.
  5. Each buffer polygon contains its source connector point.
  6. Geometry types are Polygon / MultiPolygon.
  7. Row count within ±5% of reference.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    feature_set_equality_by_id,
)

TASK_DIR = Path(__file__).resolve().parent
INPUT = TASK_DIR / "inputs" / "tokyo_connectors.geojson"
REFERENCE_OUT = (
    TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_stop_catchments.geoparquet"
)
OUTPUT_NAME = "tokyo_stop_catchments.geoparquet"

BUFFER_M = 400.0
EXPECTED_AREA = math.pi * BUFFER_M * BUFFER_M  # ~502 654.82 m^2
REFERENCE_EPSG = 6677


def _read_parquet_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_parquet(path)
    except Exception:
        return None


def _to_ref_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject to the reference CRS (EPSG:6677) for comparison."""
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    if gdf.crs.to_epsg() != REFERENCE_EPSG:
        return gdf.to_crs(epsg=REFERENCE_EPSG)
    return gdf


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="geo-l1-tokyo-busstop-buffer")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format / schema validity ------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing output file: {OUTPUT_NAME}",
            )
        )
        return report

    sub = _read_parquet_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GeoParquet")
        )
        return report

    if "connector_id" not in sub.columns:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "missing required column: connector_id",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    ref_gdf = gpd.read_parquet(REFERENCE_OUT)
    n_sub = len(sub)
    n_ref = len(ref_gdf)

    # ---- Reproject submission to reference CRS for comparison -----------
    sub_proj = _to_ref_crs(sub)

    # ---- Subchecks ------------------------------------------------------
    sub_proj["connector_id"] = sub_proj["connector_id"].fillna("").astype(str)

    # 1. connector_id populated.
    cid_pop = int((sub_proj["connector_id"].str.len() > 0).sum())
    report.subchecks.append(
        Subcheck(
            "connector_id_populated",
            cid_pop == len(sub_proj),
            detail=f"{cid_pop}/{len(sub_proj)} rows have non-empty connector_id",
        )
    )

    # 2. connector_id set Jaccard.
    id_jaccard = feature_set_equality_by_id(sub_proj, ref_gdf, key="connector_id")
    report.subchecks.append(
        Subcheck(
            "connector_id_set_preserved",
            id_jaccard >= 0.95,
            detail=f"connector_id Jaccard {id_jaccard:.4f}",
            weight=2.0,
        )
    )

    # 3. Per-row buffer area ~ pi*400^2 m^2 (within +-2%), computed in
    # the reference projected CRS.
    areas = sub_proj.geometry.area.tolist()
    area_lo = EXPECTED_AREA * 0.98
    area_hi = EXPECTED_AREA * 1.02
    in_range = sum(1 for a in areas if area_lo <= a <= area_hi)
    area_rate = in_range / len(areas) if areas else 0.0
    median_area = sorted(areas)[len(areas) // 2] if areas else 0.0
    report.subchecks.append(
        Subcheck(
            "buffer_area_400m",
            area_rate >= 0.95,
            detail=(
                f"{in_range}/{len(areas)} polygons within ±2% of "
                f"{EXPECTED_AREA:.1f} m² (median area {median_area:.1f} m²)"
            ),
            weight=4.0,
        )
    )

    # 4. Per-id IoU vs reference >= 0.95 on the common-id intersection,
    # both in EPSG:6677.
    sub_by = sub_proj.drop_duplicates("connector_id", keep="first").set_index(
        "connector_id"
    )
    ref_by = ref_gdf.drop_duplicates("connector_id", keep="first").set_index(
        "connector_id"
    )
    common_ids = sorted(set(sub_by.index) & set(ref_by.index))
    high_iou = 0
    if common_ids:
        for cid in common_ids:
            ga = sub_by.loc[cid, "geometry"]
            gb = ref_by.loc[cid, "geometry"]
            if ga is None or gb is None or ga.is_empty or gb.is_empty:
                continue
            inter = ga.intersection(gb).area
            union = ga.union(gb).area
            iou = inter / union if union > 0 else 0.0
            if iou >= 0.95:
                high_iou += 1
        iou_rate = high_iou / len(common_ids)
    else:
        iou_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "per_id_iou_high",
            iou_rate >= 0.95,
            detail=(
                f"{high_iou}/{len(common_ids)} buffers match reference at IoU >= 0.95"
            ),
            weight=4.0,
        )
    )

    # 5. Each buffer contains its source connector point (read WGS84
    # input, reproject to submission's CRS, check containment).
    inp = gpd.read_file(INPUT)
    inp_proj = _to_ref_crs(inp)
    inp_by = inp_proj.drop_duplicates("connector_id", keep="first").set_index(
        "connector_id"
    )
    common_for_pt = [
        cid for cid in sub_by.index if cid in inp_by.index
    ]
    contained = 0
    for cid in common_for_pt:
        poly = sub_by.loc[cid, "geometry"]
        pt = inp_by.loc[cid, "geometry"]
        if poly is None or pt is None or poly.is_empty or pt.is_empty:
            continue
        if poly.buffer(1e-6).covers(pt):
            contained += 1
    pt_rate = contained / len(common_for_pt) if common_for_pt else 0.0
    report.subchecks.append(
        Subcheck(
            "buffer_contains_source_point",
            pt_rate >= 0.99,
            detail=(
                f"{contained}/{len(common_for_pt)} buffers contain their "
                "source connector point"
            ),
            weight=3.0,
        )
    )

    # 6. Geometry types are Polygon / MultiPolygon.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    geom_type_ok = bool(geom_types) and geom_types.issubset(
        {"Polygon", "MultiPolygon"}
    )
    report.subchecks.append(
        Subcheck(
            "geometry_types_polygonal",
            geom_type_ok,
            detail=(
                f"geometry types: {sorted(geom_types)} "
                "(expected Polygon / MultiPolygon)"
            ),
        )
    )

    # 7. Row count within ±5%.
    count_ok = (
        abs(n_sub - n_ref) / max(n_sub, n_ref) <= 0.05 if max(n_sub, n_ref) else True
    )
    report.subchecks.append(
        Subcheck(
            "row_count_within_tolerance",
            count_ok,
            detail=f"submission {n_sub} vs reference {n_ref} (±5%)",
            weight=1.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
