"""Grader for dc-l2-cairo-invalid-dedup.

Single hard gate (`format_schema_valid`) when the file is missing,
unreadable, lacks a usable CRS, is missing required columns, or has
no geometry. Everything else is a one-point subcheck.

The task chains four data-cleaning operations (make-valid, sliver
removal, deduplicate, Polygon → MultiPolygon coercion); each subcheck
targets one of those operations independently so partial
implementations land in distinct score ranges.

The agent's choice of CRS is graded as two soft subchecks
(`crs_is_canonical`, `crs_in_meaningful_set`) so a wrong-but-reasonable
CRS still scores the geometric work.
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
    attribute_match,
    count_within_tolerance,
    feature_set_equality_by_id,
    grade_crs_soft,
    iou_with_tolerance,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "parcels_canonical.geoparquet"
OUTPUT_NAME = "parcels_canonical.geoparquet"

REQUIRED_COLUMNS = {"parcel_id", "parcel_class", "district", "area_m2"}
ATTRIBUTE_FIELDS = ["parcel_class", "district"]

SLIVER_AREA_THRESHOLD_M2 = 1.0
AREA_REL_TOL = 1e-3

CANONICAL_EPSG = 22992
MEANINGFUL_EPSGS = {22992}


def _read_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_parquet(path)
    except Exception:
        try:
            return gpd.read_file(path)
        except Exception:
            return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dc-l2-cairo-invalid-dedup")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format / schema validity --------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing output file: {OUTPUT_NAME}",
            )
        )
        return report

    sub = _read_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GeoParquet")
        )
        return report

    missing = REQUIRED_COLUMNS - set(sub.columns)
    columns_ok = not missing
    has_geometry = "geometry" in sub.columns and not sub.geometry.isna().all()

    crs_res = grade_crs_soft(sub, MEANINGFUL_EPSGS, CANONICAL_EPSG)

    if not (crs_res.gate_ok and columns_ok and has_geometry):
        reason_parts = []
        if not crs_res.gate_ok:
            reason_parts.append(crs_res.gate_reason)
        if not columns_ok:
            reason_parts.append(f"missing columns: {sorted(missing)}")
        if not has_geometry:
            reason_parts.append("missing or all-null geometry column")
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(reason_parts))
        )
        return report

    sub = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = gpd.read_parquet(REFERENCE_OUT)

    # Feature count within ±5% of the reference — salvageable subcheck.
    # A broad detector for a skipped drop/collapse step (dedup or sliver):
    # a wrong count is a strong symptom, so this stays high (3.0).
    count_ok = count_within_tolerance(sub, ref, pct=0.05)
    report.subchecks.append(
        Subcheck(
            "feature_count_within_tolerance",
            bool(count_ok),
            detail=f"submission {len(sub)} vs reference {len(ref)} (±5%)",
            weight=3.0,
        )
    )

    # Geometry-type uniformity (Polygon or MultiPolygon). The stricter
    # `all_multipolygon` subcheck below grades the Polygon → MultiPolygon
    # coercion separately; this one only flags non-polygonal stray rows
    # (e.g., a stray LineString or GeometryCollection).
    geom_types = set(sub.geometry.geom_type.unique())
    geom_type_ok = geom_types.issubset({"MultiPolygon", "Polygon"})
    report.subchecks.append(
        Subcheck(
            "geometry_type_polygonal",
            bool(geom_type_ok),
            detail=(
                f"got geometry types {sorted(geom_types)}, expected subset of "
                "{Polygon, MultiPolygon}"
            ),
        )
    )

    # No null or empty geometries in the output.
    no_null_geom = bool(sub.geometry.notna().all() and (~sub.geometry.is_empty).all())
    report.subchecks.append(
        Subcheck(
            "no_null_or_empty_geometry",
            no_null_geom,
            detail=(
                "all geometries non-null and non-empty"
                if no_null_geom
                else "submission contains null or empty geometries"
            ),
            # Geometry integrity, but a correct pipeline never emits a
            # null/empty row — a supporting invariant, not a central
            # cleaning operation. Medium weight (2.0).
            weight=2.0,
        )
    )

    # 1. Every geometry is valid (the make-valid step actually worked).
    valid_mask = sub.geometry.is_valid
    n_valid = int(valid_mask.sum())
    n_total = len(sub)
    all_valid = n_valid == n_total
    report.subchecks.append(
        Subcheck(
            "all_geometries_valid",
            bool(all_valid),
            detail=f"{n_valid}/{n_total} valid",
            # Central skill: this is the make-valid step's primary
            # detector. Highest weight (4.0).
            weight=4.0,
        )
    )

    # 2. Every geometry is a MultiPolygon (Polygon → MultiPolygon
    #    coercion). Strict equality: a single stray Polygon means the
    #    schema-consistency promise is broken.
    n_mp = int((sub.geometry.geom_type == "MultiPolygon").sum())
    all_multi = n_mp == n_total
    report.subchecks.append(
        Subcheck(
            "all_multipolygon",
            bool(all_multi),
            detail=f"{n_mp}/{n_total} MultiPolygon",
            # Central skill: the Polygon → MultiPolygon coercion is one
            # of the four named cleaning operations. Highest weight
            # (4.0). Under the old 3x-content policy this sat at
            # weight 1, so skipping coercion cost almost nothing (0.97).
            weight=4.0,
        )
    )

    # 3. No slivers: every geometry has area ≥ 1 m² (strictly above the
    #    threshold the persona requested).
    sub_areas = sub.geometry.area
    n_slivers = int((sub_areas < SLIVER_AREA_THRESHOLD_M2).sum())
    no_slivers = n_slivers == 0
    report.subchecks.append(
        Subcheck(
            "no_slivers",
            bool(no_slivers),
            detail=(
                f"{n_slivers} geometries below {SLIVER_AREA_THRESHOLD_M2} m²"
            ),
            # Central skill: sliver removal is one of the four named
            # cleaning operations. Highest weight (4.0).
            weight=4.0,
        )
    )

    # 4. No exact-duplicate geometries: the dedup step actually
    #    collapsed identical geometries.
    wkb_counts = sub.geometry.apply(lambda g: g.wkb).value_counts()
    n_dup_groups = int((wkb_counts > 1).sum())
    no_dups = n_dup_groups == 0
    report.subchecks.append(
        Subcheck(
            "no_exact_duplicate_geometries",
            bool(no_dups),
            detail=f"{n_dup_groups} duplicate WKB groups",
            # Central skill: the dedup step's primary detector. Highest
            # weight (4.0).
            weight=4.0,
        )
    )

    # 5. parcel_id set matches reference (Jaccard ≥ 0.95). Catches
    #    an agent that dedup'd the wrong way (kept the duplicate's
    #    synthetic id instead of the original) or dropped real parcels.
    sub_ids = sub.copy()
    ref_ids = ref.copy()
    sub_ids["parcel_id"] = sub_ids["parcel_id"].astype(str)
    ref_ids["parcel_id"] = ref_ids["parcel_id"].astype(str)
    id_jaccard = feature_set_equality_by_id(sub_ids, ref_ids, key="parcel_id")
    report.subchecks.append(
        Subcheck(
            "parcel_id_set_matches_reference",
            bool(id_jaccard >= 0.95),
            detail=f"parcel_id Jaccard {id_jaccard:.4f}",
            weight=3.0,
        )
    )

    # 6. area_m2 column was recomputed from the kept geometry rather
    #    than carried over from the legacy stale value. We compare the
    #    submission's area_m2 column to its own `geometry.area`. Pass
    #    if ≥ 95 % of rows match within 1e-3 relative tolerance.
    sub_with_calc = sub.copy()
    sub_with_calc["_calc_area"] = sub_with_calc.geometry.area
    diff = (
        (sub_with_calc["area_m2"] - sub_with_calc["_calc_area"]).abs()
        / sub_with_calc["_calc_area"].abs().clip(lower=1e-12)
    )
    n_recomputed = int((diff <= AREA_REL_TOL).sum())
    area_ok = n_recomputed >= 0.95 * n_total
    report.subchecks.append(
        Subcheck(
            "area_m2_recomputed",
            bool(area_ok),
            detail=(
                f"{n_recomputed}/{n_total} rows have area_m2 matching "
                f"geometry.area within {AREA_REL_TOL:.0e} relative tolerance"
            ),
            # Implicit attribute-recompute step — real, but secondary to
            # the geometry-cleaning operations. Medium weight (2.0).
            weight=2.0,
        )
    )

    # 7. Identifying attributes (parcel_class, district) match the
    #    reference per parcel_id. Catches an agent that dedup'd by
    #    keeping the *latest* row's metadata (giving the conflicting
    #    duplicate's parcel_class) instead of the earliest.
    attr_match = attribute_match(
        sub_ids, ref_ids, fields=ATTRIBUTE_FIELDS, key="parcel_id"
    )
    attrs_ok = all(attr_match[f] >= 0.95 for f in ATTRIBUTE_FIELDS)
    report.subchecks.append(
        Subcheck(
            "identifying_attributes_match_reference",
            bool(attrs_ok),
            detail="; ".join(
                f"{f}={attr_match[f]:.3f}" for f in ATTRIBUTE_FIELDS
            ),
            weight=3.0,
        )
    )

    # 8. Geometric extent preserved at the union level: the agent
    #    must not have moved, simplified, or buffered geometry beyond
    #    what make_valid required. IoU ≥ 0.99 against the reference
    #    union. If the submission contains invalid geometries (e.g.,
    #    the agent skipped make_valid) shapely's unary_union raises
    #    TopologyException; we catch and treat as a failed subcheck.
    try:
        extent_iou = iou_with_tolerance(sub, ref, eps=0.0)
        extent_detail = f"union IoU {extent_iou:.4f}"
        extent_pass = extent_iou >= 0.99
    except Exception as exc:
        extent_iou = 0.0
        extent_detail = f"union failed: {type(exc).__name__}: {exc}"
        extent_pass = False
    report.subchecks.append(
        Subcheck(
            "geometric_extent_preserved",
            bool(extent_pass),
            detail=extent_detail,
            weight=3.0,
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
