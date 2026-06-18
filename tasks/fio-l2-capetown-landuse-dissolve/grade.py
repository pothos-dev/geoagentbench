"""Grader for fio-l2-capetown-landuse-dissolve.

Skills under test:
  1. Read a FlatGeobuf and dissolve features by an attribute.
  2. Collect grouped (Multi)Polygons into a single MultiPolygon per group.
  3. Compute per-group `area_m2` (in projected metres) and `parcel_count`.
  4. Write the result as GeoParquet in EPSG:32734.

Single hard gate (`format_schema_valid`): file present, parses as
GeoParquet, declares *some* usable CRS, and all required columns are
present (`class`, `parcel_count`, `area_m2`, geometry). A submission
with no declarable CRS is unrecoverable — the grader can't reproject
to canonical and downstream geometric subchecks become undefined.

Subchecks:
  - one row per class (no duplicates).
  - every geometry is MultiPolygon (collect step done).
  - class-set Jaccard ≥ 0.9 against the reference.
  - ≥ 95 % of common classes have matching `parcel_count`.
  - ≥ 90 % of common classes have `area_m2` within ±5 % of reference.
  - unioned geometry IoU ≥ 0.9.
  - row count within ±5 % of reference class count.
  - `crs_is_canonical` — original declared CRS is EPSG:32734.
  - `crs_in_meaningful_set` — original declared CRS is in {EPSG:32734}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
from shapely.ops import unary_union

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    count_within_tolerance,
    grade_crs_soft,
    iou_with_tolerance,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "landuse_dissolved.geoparquet"
OUTPUT_NAME = "landuse_dissolved.geoparquet"

TARGET_EPSG = 32734
CANONICAL_EPSG = 32734
MEANINGFUL_EPSGS = {32734}
REQUIRED_COLS = ("class", "parcel_count", "area_m2")
COUNT_TOL = 0.05
AREA_TOL = 0.05
JACCARD_THRESHOLD = 0.9
IOU_THRESHOLD = 0.9
PARCEL_MATCH_RATE = 0.95
AREA_MATCH_RATE = 0.90
def _safe_read(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_parquet(path)
    except Exception:
        try:
            return gpd.read_file(path)
        except Exception:
            return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="fio-l2-capetown-landuse-dissolve")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format / schema validity --------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    sub = _safe_read(submission_path)
    if sub is None:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "could not read output as GeoParquet (or any vector format)",
            )
        )
        return report

    # GeoParquet sniff: a parquet file should round-trip via gpd.read_parquet.
    try:
        _ = gpd.read_parquet(submission_path)
        is_geoparquet = True
    except Exception:
        is_geoparquet = False
    if not is_geoparquet:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "output is not a GeoParquet (gpd.read_parquet failed)",
            )
        )
        return report

    crs_res = grade_crs_soft(
        sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=False
    )
    if not crs_res.gate_ok:
        report.gates.append(
            Gate("format_schema_valid", False, crs_res.gate_reason)
        )
        return report

    sub = crs_res.normalized

    missing_cols = [c for c in REQUIRED_COLS if c not in sub.columns]
    if missing_cols:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing required columns: {missing_cols} (have {list(sub.columns)})",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = gpd.read_parquet(REFERENCE_OUT)
    n_sub = len(sub)
    n_ref = len(ref)

    # 1. One row per class.
    classes = sub["class"].astype(str)
    unique_ok = classes.is_unique
    report.subchecks.append(
        Subcheck(
            "one_row_per_class",
            bool(unique_ok),
            detail=(
                f"{n_sub} rows over {classes.nunique()} distinct class values"
                + ("" if unique_ok else " — duplicates present")
            ),
        )
    )

    # 2. Every geometry is MultiPolygon.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    multipoly_only = geom_types.issubset({"MultiPolygon"})
    report.subchecks.append(
        Subcheck(
            "multipolygon_only",
            multipoly_only,
            detail=f"geometry types: {sorted(geom_types)} (expected only MultiPolygon)",
        )
    )

    # 3. Class-set Jaccard.
    sub_classes = set(classes.tolist())
    ref_classes = set(ref["class"].astype(str).tolist())
    jacc = jaccard_similarity_set(sub_classes, ref_classes)
    report.subchecks.append(
        Subcheck(
            "class_set_jaccard",
            jacc >= JACCARD_THRESHOLD,
            detail=f"Jaccard {jacc:.4f} (threshold {JACCARD_THRESHOLD})",
            weight=3.0,
        )
    )

    # 4. parcel_count match for common classes.
    common = sorted(sub_classes & ref_classes)
    sub_idx = sub.set_index(classes)
    ref_idx = ref.set_index(ref["class"].astype(str))
    if common:
        matches = 0
        for c in common:
            try:
                if int(sub_idx.loc[c, "parcel_count"]) == int(ref_idx.loc[c, "parcel_count"]):
                    matches += 1
            except (ValueError, TypeError):
                pass
        rate_pc = matches / len(common)
    else:
        rate_pc = 0.0
    report.subchecks.append(
        Subcheck(
            "parcel_count_per_class",
            rate_pc >= PARCEL_MATCH_RATE,
            detail=(
                f"{int(rate_pc * len(common))}/{len(common)} common classes have matching "
                f"parcel_count (threshold {int(PARCEL_MATCH_RATE * 100)} %)"
            ),
            weight=3.0,
        )
    )

    # 5. area_m2 within ±5 % for common classes.
    if common:
        ok = 0
        for c in common:
            try:
                a_sub = float(sub_idx.loc[c, "area_m2"])
                a_ref = float(ref_idx.loc[c, "area_m2"])
            except (ValueError, TypeError):
                continue
            denom = max(abs(a_sub), abs(a_ref))
            if denom == 0:
                ok += 1
                continue
            if abs(a_sub - a_ref) / denom <= AREA_TOL:
                ok += 1
        rate_a = ok / len(common)
    else:
        rate_a = 0.0
    report.subchecks.append(
        Subcheck(
            "area_m2_per_class_within_tolerance",
            rate_a >= AREA_MATCH_RATE,
            detail=(
                f"{int(rate_a * len(common))}/{len(common)} common classes within "
                f"±{int(AREA_TOL * 100)} % area (threshold {int(AREA_MATCH_RATE * 100)} %)"
            ),
            weight=3.0,
        )
    )

    # 6. Unioned geometry IoU.
    sub_union = unary_union(sub.geometry.tolist())
    ref_union = unary_union(ref.geometry.tolist())
    iou = iou_with_tolerance(sub_union, ref_union, eps=0.0)
    report.subchecks.append(
        Subcheck(
            "unioned_geometry_iou",
            iou >= IOU_THRESHOLD,
            detail=f"unioned IoU {iou:.4f} (threshold {IOU_THRESHOLD})",
            weight=3.0,
        )
    )

    # 7. Row count within ±5 % of reference class count.
    count_ok = count_within_tolerance(n_sub, n_ref, pct=COUNT_TOL)
    report.subchecks.append(
        Subcheck(
            "row_count_within_tolerance",
            count_ok,
            detail=f"submission {n_sub} rows vs reference {n_ref} (±{int(COUNT_TOL * 100)} %)",
            weight=1.0,
        )
    )

    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            crs_res.is_canonical,
            detail=(
                f"original EPSG:{crs_res.original_epsg}; "
                f"canonical EPSG:{CANONICAL_EPSG}"
            ),
        )
    )
    report.subchecks.append(
        Subcheck(
            "crs_in_meaningful_set",
            crs_res.in_meaningful_set,
            detail=(
                f"original EPSG:{crs_res.original_epsg}; "
                f"meaningful set {sorted(MEANINGFUL_EPSGS)}"
            ),
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
