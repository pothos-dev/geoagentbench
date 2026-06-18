"""Grader for dc-l3-vienna-overpass-historical.

L3 live-data task. The reference fetches Vienna's 23 Bezirke from
Overpass for both the current and 2014-01-01 snapshots, normalises
district names, and computes the per-district symmetric difference
(added / removed / unchanged).

Two consecutive runs differ on the current-side data (OSM drift), so
tolerances are intentionally generous on counts and geometry, while
principled checks (CRS, coordinate envelope, area dominance of the
unchanged class) catch real failures regardless of drift.

Single hard gate (`format_schema_valid`) when the GeoJSON is missing,
unreadable, empty, or missing required properties (`change_type`,
`district_name`, `touches_changed`, geometry). Everything else is a
one-point subcheck.

Subchecks:
  - CRS is EPSG:4326
  - Coordinates within Vienna envelope
  - Feature count within tolerance
  - District name set overlap (Jaccard)
  - touches_changed field present with boolean values
  - Unchanged area dominates total area
  - Overall coverage IoU vs reference
  - Per-type feature count balance
  - touches_changed accuracy vs reference
  - Added+removed area ratio plausible
  - All three change_type values present
  - Geometries are polygonal (Polygon/MultiPolygon)
  - Feature count is plausible (>= 20)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    count_within_tolerance,
    iou_with_tolerance,
    is_wgs84,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "vienna_boundary_changes.geojson"
OUTPUT_NAME = "vienna_boundary_changes.geojson"

# Vienna coordinate envelope (WGS84).
VIENNA_LON_MIN, VIENNA_LON_MAX = 16.1, 16.6
VIENNA_LAT_MIN, VIENNA_LAT_MAX = 48.1, 48.35

# Drift-tolerant thresholds.
COUNT_TOLERANCE = 0.20  # +-20% on total feature count
TYPE_COUNT_TOLERANCE = 0.25  # +-25% per change_type
DISTRICT_NAME_JACCARD_MIN = 0.75
COVERAGE_IOU_MIN = 0.80
UNCHANGED_AREA_FRACTION_MIN = 0.85  # unchanged >> changed for stable Vienna
TOUCHES_CHANGED_ACCURACY_MIN = 0.70


def _load_geojson(path: Path) -> gpd.GeoDataFrame | None:
    """Load a GeoJSON file into a GeoDataFrame."""
    try:
        gdf = gpd.read_file(path)
        return gdf
    except Exception:
        return None


def _load_reference() -> gpd.GeoDataFrame:
    return gpd.read_file(REFERENCE_OUT)


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dc-l3-vienna-overpass-historical")
    sub_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format / schema validity ----------------------------------
    if not sub_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output: {OUTPUT_NAME}")
        )
        return report

    sub = _load_geojson(sub_path)
    if sub is None or len(sub) == 0:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GeoJSON or empty")
        )
        return report

    required_cols = {"change_type", "district_name", "touches_changed"}
    missing = required_cols - set(sub.columns)
    if missing:
        report.gates.append(
            Gate("format_schema_valid", False, f"missing columns: {sorted(missing)}")
        )
        return report

    if sub.geometry.isna().all():
        report.gates.append(
            Gate("format_schema_valid", False, "no geometry found")
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    # ---- Load reference --------------------------------------------------
    ref = _load_reference()

    # ---- Salvageable structural subchecks --------------------------------
    expected_types = {"added_since_2014", "removed_since_2014", "unchanged"}
    change_types = set(sub["change_type"].dropna().unique())
    all_change_types_present = expected_types.issubset(change_types)
    report.subchecks.append(
        Subcheck(
            "all_change_types_present",
            bool(all_change_types_present),
            detail=f"change_type values {sorted(change_types)}; expected {sorted(expected_types)}",
        )
    )

    geom_types = set(sub.geometry.geom_type.unique())
    allowed = {"Polygon", "MultiPolygon"}
    geom_polygonal = geom_types.issubset(allowed)
    report.subchecks.append(
        Subcheck(
            "geometry_type_polygonal",
            bool(geom_polygonal),
            detail=f"got geometry types {sorted(geom_types)}; expected subset of {sorted(allowed)}",
        )
    )

    feature_count_plausible = len(sub) >= 20
    report.subchecks.append(
        Subcheck(
            "feature_count_plausible",
            bool(feature_count_plausible),
            detail=f"{len(sub)} features; expected >= 20",
        )
    )

    # ---- Subcheck 1: CRS is WGS84 ---------------------------------------
    crs_ok = is_wgs84(sub.crs)
    report.subchecks.append(
        Subcheck("crs_is_wgs84", crs_ok, f"crs={sub.crs}")
    )

    # ---- Subcheck 2: coordinates in Vienna envelope ----------------------
    bounds = sub.total_bounds  # minx, miny, maxx, maxy
    in_envelope = (
        VIENNA_LON_MIN <= bounds[0] <= VIENNA_LON_MAX
        and VIENNA_LON_MIN <= bounds[2] <= VIENNA_LON_MAX
        and VIENNA_LAT_MIN <= bounds[1] <= VIENNA_LAT_MAX
        and VIENNA_LAT_MIN <= bounds[3] <= VIENNA_LAT_MAX
    )
    report.subchecks.append(
        Subcheck(
            "coordinates_in_vienna_envelope",
            bool(in_envelope),
            f"bounds={bounds.tolist()}",
        )
    )

    # ---- Subcheck 3: total feature count within tolerance ----------------
    count_ok = count_within_tolerance(len(sub), len(ref), pct=COUNT_TOLERANCE)
    report.subchecks.append(
        Subcheck(
            "total_feature_count",
            bool(count_ok),
            f"sub={len(sub)} ref={len(ref)} tol={COUNT_TOLERANCE:.0%}",
            weight=2.0,
        )
    )

    # ---- Subcheck 4: district name set overlap ---------------------------
    sub_names = set(sub["district_name"].dropna().astype(str).unique())
    ref_names = set(ref["district_name"].dropna().astype(str).unique())
    name_jaccard = jaccard_similarity_set(sub_names, ref_names)
    report.subchecks.append(
        Subcheck(
            "district_name_set_overlap",
            name_jaccard >= DISTRICT_NAME_JACCARD_MIN,
            f"Jaccard={name_jaccard:.4f} (min {DISTRICT_NAME_JACCARD_MIN})",
            weight=2.0,
        )
    )

    # ---- Subcheck 5: touches_changed values are boolean ------------------
    tc_col = sub["touches_changed"]
    tc_valid = tc_col.dropna().apply(lambda v: isinstance(v, bool) or v in (0, 1, True, False)).all()
    report.subchecks.append(
        Subcheck(
            "touches_changed_is_boolean",
            bool(tc_valid) and len(tc_col.dropna()) > 0,
            f"valid_booleans={tc_valid}, non_null={len(tc_col.dropna())}",
        )
    )

    # ---- Subcheck 6: unchanged area dominates total area -----------------
    unchanged_geoms = sub.loc[sub["change_type"] == "unchanged", "geometry"]
    all_geoms = sub["geometry"]
    if len(unchanged_geoms) > 0 and len(all_geoms) > 0:
        unchanged_area = float(unchanged_geoms.area.sum())
        total_area = float(all_geoms.area.sum())
        frac = unchanged_area / total_area if total_area > 0 else 0.0
    else:
        frac = 0.0
    report.subchecks.append(
        Subcheck(
            "unchanged_area_dominates",
            frac >= UNCHANGED_AREA_FRACTION_MIN,
            f"unchanged_fraction={frac:.4f} (min {UNCHANGED_AREA_FRACTION_MIN})",
            weight=4.0,
        )
    )

    # ---- Subcheck 7: overall coverage IoU vs reference -------------------
    try:
        sub_union = unary_union(sub.geometry.tolist())
        ref_union = unary_union(ref.geometry.tolist())
        coverage_iou = iou_with_tolerance(sub_union, ref_union)
    except Exception:
        coverage_iou = 0.0
    report.subchecks.append(
        Subcheck(
            "overall_coverage_iou",
            coverage_iou >= COVERAGE_IOU_MIN,
            f"IoU={coverage_iou:.4f} (min {COVERAGE_IOU_MIN})",
            weight=4.0,
        )
    )

    # ---- Subcheck 8: per-type feature count balance ----------------------
    type_counts_ok = True
    details = []
    for ct in expected_types:
        sub_n = int((sub["change_type"] == ct).sum())
        ref_n = int((ref["change_type"] == ct).sum())
        ok = count_within_tolerance(sub_n, ref_n, pct=TYPE_COUNT_TOLERANCE)
        if not ok:
            type_counts_ok = False
        details.append(f"{ct}: sub={sub_n} ref={ref_n}")
    report.subchecks.append(
        Subcheck(
            "per_type_feature_count",
            type_counts_ok,
            "; ".join(details),
            weight=4.0,
        )
    )

    # ---- Subcheck 9: touches_changed accuracy vs reference ---------------
    # Match features by (change_type, district_name) and compare.
    sub_tc = {}
    for _, row in sub.iterrows():
        key = (str(row.get("change_type", "")), str(row.get("district_name", "")))
        sub_tc[key] = bool(row.get("touches_changed", False))
    ref_tc = {}
    for _, row in ref.iterrows():
        key = (str(row.get("change_type", "")), str(row.get("district_name", "")))
        ref_tc[key] = bool(row.get("touches_changed", False))
    common_keys = set(sub_tc) & set(ref_tc)
    if common_keys:
        matches = sum(1 for k in common_keys if sub_tc[k] == ref_tc[k])
        tc_accuracy = matches / len(common_keys)
    else:
        tc_accuracy = 0.0
    report.subchecks.append(
        Subcheck(
            "touches_changed_accuracy",
            tc_accuracy >= TOUCHES_CHANGED_ACCURACY_MIN,
            f"accuracy={tc_accuracy:.4f} on {len(common_keys)} matched features "
            f"(min {TOUCHES_CHANGED_ACCURACY_MIN})",
            weight=2.0,
        )
    )

    # ---- Subcheck 10: added+removed area ratio plausible -----------------
    # For stable Vienna, added and removed areas should each be < 5% of total.
    added_area = float(
        sub.loc[sub["change_type"] == "added_since_2014", "geometry"].area.sum()
    )
    removed_area = float(
        sub.loc[sub["change_type"] == "removed_since_2014", "geometry"].area.sum()
    )
    total_area = float(sub.geometry.area.sum()) if len(sub) > 0 else 1.0
    changed_frac = (added_area + removed_area) / total_area if total_area > 0 else 1.0
    report.subchecks.append(
        Subcheck(
            "changed_area_is_small",
            changed_frac < 0.15,
            f"changed_fraction={changed_frac:.6f} (must be < 0.15)",
            weight=4.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
