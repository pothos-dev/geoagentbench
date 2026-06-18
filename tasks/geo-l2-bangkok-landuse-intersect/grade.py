"""Grader for geo-l2-bangkok-landuse-intersect.

Skills under test:
  1. Repair invalid (self-intersecting) input geometries.
  2. Intersect each land-cover polygon with a study-area polygon.
  3. Coerce to MultiPolygon and simplify at 5 m tolerance.
  4. Compute per-feature `area_m2` and write GeoJSON in WGS 84.

Hard gate (`format_schema_valid`) — file present, parses as GeoJSON,
required columns (`class`, `area_m2`, geometry) present, and the
submission declares *some* usable CRS (or is RFC 7946 implicit WGS 84).
A submission with no declarable CRS is unrecoverable.

Subchecks (7):
  1. all_multipolygon — every geometry is MultiPolygon.
  2. count_within_tolerance — feature count within ±5 % of reference.
  3. class_set_jaccard — class set Jaccard ≥ 0.9 vs reference.
  4. total_area_within_tolerance — total `area_m2` sum within ±5 %.
  5. unioned_geometry_iou — IoU of unioned submission vs reference ≥ 0.9.
  6. crs_is_canonical — original declared CRS is EPSG:4326 (the spec'd
     output CRS).
  7. crs_in_meaningful_set — original declared CRS is in {EPSG:4326}.
     Any other CRS is docked an additional point.

Subcheck weights (severity-calibrated; total weight 15):
  - unioned_geometry_iou (4.0) and total_area_within_tolerance (4.0) are
    the central geometric-correctness checks: IoU is the most direct
    detector of a correct intersection/overlay, and total-area carries
    the explicit km²/m² unit gotcha and overall magnitude. Failing either
    means the core skill was not performed correctly.
  - count_within_tolerance (3.0) is a strong proxy for the same central
    operation (a skipped intersection ships ~21 k features instead of
    ~3.5 k) but is slightly less direct than IoU/area.
  - class_set_jaccard (1.0) is attribute-preservation (structural), not
    geometric-correctness — it passes for both the skipped-intersection
    and wrong-unit failures, so it barely discriminates the central skill.
  - all_multipolygon (1.0) is a structural geometry-type coercion.
  - crs_is_canonical (1.0) + crs_in_meaningful_set (1.0) price the
    RFC-7946 WGS84 output-convention gotcha as a light, recoverable
    deduction (2/15) rather than a hard fail.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd

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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "bma_landcover_intersect.geojson"
OUTPUT_NAME = "bma_landcover_intersect.geojson"

REQUIRED_COLS = ("class", "area_m2")
COUNT_TOL = 0.05
AREA_TOL = 0.05
JACCARD_THRESHOLD = 0.9
IOU_THRESHOLD = 0.9

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}


def _safe_read(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="geo-l2-bangkok-landuse-intersect")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format / schema validity ------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    # GeoJSON sniff: file must parse as JSON with FeatureCollection root.
    try:
        with submission_path.open("r", encoding="utf-8") as f:
            head = json.load(f)
        is_geojson = (
            isinstance(head, dict) and head.get("type") == "FeatureCollection"
        )
    except Exception:
        is_geojson = False
    if not is_geojson:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "output is not a GeoJSON FeatureCollection",
            )
        )
        return report

    sub = _safe_read(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GeoJSON via geopandas")
        )
        return report

    missing = [c for c in REQUIRED_COLS if c not in sub.columns]
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing required columns: {missing} (have {list(sub.columns)})",
            )
        )
        return report

    crs_res = grade_crs_soft(
        sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True
    )
    if not crs_res.gate_ok:
        report.gates.append(
            Gate("format_schema_valid", False, crs_res.gate_reason)
        )
        return report

    sub = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = gpd.read_file(REFERENCE_OUT)
    n_sub = len(sub)
    n_ref = len(ref)

    # 1. All geometries are MultiPolygon.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    multipoly_only = geom_types.issubset({"MultiPolygon"})
    report.subchecks.append(
        Subcheck(
            "all_multipolygon",
            multipoly_only,
            detail=f"geometry types: {sorted(geom_types)} (expected only MultiPolygon)",
        )
    )

    # 2. Feature count within ±5 %.
    count_ok = count_within_tolerance(n_sub, n_ref, pct=COUNT_TOL)
    report.subchecks.append(
        Subcheck(
            "count_within_tolerance",
            count_ok,
            detail=f"submission {n_sub} vs reference {n_ref} (±{int(COUNT_TOL * 100)} %)",
            weight=3.0,  # strong proxy for the central intersection step
        )
    )

    # 3. Class-set Jaccard.
    sub_classes = set(sub["class"].astype(str).tolist())
    ref_classes = set(ref["class"].astype(str).tolist())
    jacc = jaccard_similarity_set(sub_classes, ref_classes)
    report.subchecks.append(
        Subcheck(
            "class_set_jaccard",
            jacc >= JACCARD_THRESHOLD,
            detail=f"Jaccard {jacc:.4f} (threshold {JACCARD_THRESHOLD})",
            weight=1.0,  # attribute-preservation / structural, not geometric-correctness
        )
    )

    # 4. Total area_m2 within ±5 %.
    try:
        total_sub = float(sub["area_m2"].astype(float).sum())
    except (ValueError, TypeError):
        total_sub = float("nan")
    total_ref = float(ref["area_m2"].astype(float).sum())
    denom = max(abs(total_sub), abs(total_ref))
    if denom == 0:
        area_ok = total_sub == total_ref
        rel = 0.0
    else:
        rel = abs(total_sub - total_ref) / denom
        area_ok = rel <= AREA_TOL
    report.subchecks.append(
        Subcheck(
            "total_area_within_tolerance",
            bool(area_ok),
            detail=(
                f"submission total {total_sub:.0f} m² vs reference {total_ref:.0f} m² "
                f"(rel diff {rel:.4f}, threshold {AREA_TOL})"
            ),
            weight=4.0,  # central: metric-CRS area + the km2/m2 unit gotcha
        )
    )

    # 5. Unioned-geometry IoU.
    # Pass GeoDataFrames straight through so the library's defensive
    # make_valid step runs before unioning — guards against a pathological
    # submission geometry raising GEOSException and nulling the whole grade.
    iou = iou_with_tolerance(sub, ref, eps=0.0)
    report.subchecks.append(
        Subcheck(
            "unioned_geometry_iou",
            iou >= IOU_THRESHOLD,
            detail=f"unioned IoU {iou:.4f} (threshold {IOU_THRESHOLD})",
            weight=4.0,  # central: most direct detector of correct intersection/overlay
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
