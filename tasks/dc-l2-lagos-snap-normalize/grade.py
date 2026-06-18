"""Grader for dc-l2-lagos-snap-normalize.

The persona's question is "snap, drop zero-area, normalise the zoning
class to four canonical values, filter blanks, aggregate per class
with a recomputed `area_m2`". Each step is independently observable
in the output.

Single hard gate (`format_schema_valid`) when the file is missing,
unreadable, lacks a usable CRS, is missing required columns, or has
no geometry. Everything else is a one-point subcheck.

Subchecks:
  1. zoning_class set is exactly the four canonical TitleCase values
     {Residential, Commercial, Industrial, Agricultural}.
  2. zoning_class column has no blank / whitespace / null values
     (proves the blank-row filter ran).
  3. No zero-area geometries (proves the zero-area drop ran).
  4. area_m2 column is recomputed from the surviving geometry —
     compare the column to its own `geometry.area` within 1 m² /
     1e-3 relative tolerance (whichever is larger).
  5. Per-class area within ±0.5 % of the reference's 250 000 m²
     (proves the dissolve happened on the right rows; a missing
     normalisation step or an unfiltered ghost shifts this).
  6. Geometric IoU vs the reference dissolved polygons ≥ 0.99 (the
     four 500 m × 500 m squares).
  7. Geometry simplicity: every output polygon has zero interior
     holes (proves the snap worked — an unsnapped dissolve picks
     up hundreds of sub-mm sliver holes along internal grid lines).
  8. Strict Polygon geometry type: the inventory declares Polygon,
     and a clean snap+dissolve yields four single-part Polygons; a
     MultiPolygon row is itself evidence the snap or dissolve
     went wrong.
  9. `crs_is_canonical` — original declared CRS is EPSG:26331 (the
     spec'd output CRS).
 10. `crs_in_meaningful_set` — original declared CRS is in
     {EPSG:26331}. An agent that picked another CRS is docked an
     extra point.
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
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "zoning_aggregated.gpkg"
OUTPUT_NAME = "zoning_aggregated.gpkg"

REQUIRED_COLUMNS = {"zoning_class", "area_m2"}
CANONICAL_CLASSES = {"Residential", "Commercial", "Industrial", "Agricultural"}
EXPECTED_AREA_M2 = 500.0 * 500.0  # each canonical class is a 500m × 500m square
AREA_REL_TOL_RECOMPUTE = 1e-3
AREA_REL_TOL_VS_REF = 5e-3
AREA_ABS_TOL_RECOMPUTE_M2 = 1.0

CANONICAL_EPSG = 26331
MEANINGFUL_EPSGS = {26331}


def _read_gdf_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dc-l2-lagos-snap-normalize")
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

    sub = _read_gdf_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GPKG")
        )
        return report

    missing = REQUIRED_COLUMNS - set(sub.columns)
    columns_ok = not missing
    has_geometry = "geometry" in sub.columns and not sub.geometry.isna().all()

    crs_res = grade_crs_soft(sub, MEANINGFUL_EPSGS, CANONICAL_EPSG)

    if not (crs_res.gate_ok and columns_ok and has_geometry):
        reasons = []
        if not crs_res.gate_ok:
            reasons.append(crs_res.gate_reason)
        if not columns_ok:
            reasons.append(f"missing columns: {sorted(missing)}")
        if not has_geometry:
            reasons.append("missing or all-null geometry column")
        report.gates.append(Gate("format_schema_valid", False, "; ".join(reasons)))
        return report

    sub = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks -----------------------------------------------------
    ref = gpd.read_file(REFERENCE_OUT)

    # Geometry-type uniformity (Polygon or MultiPolygon). The stricter
    # `geometry_type_polygon_only` subcheck below grades single-part
    # Polygon strictness separately; this one only flags non-polygonal
    # stray rows.
    no_null_geom_present = bool(
        sub.geometry.notna().all() and (~sub.geometry.is_empty).all()
    )
    geom_types = set(sub.geometry.geom_type.unique()) if no_null_geom_present else set()
    geom_type_ok = no_null_geom_present and geom_types.issubset(
        {"Polygon", "MultiPolygon"}
    )
    report.subchecks.append(
        Subcheck(
            "geometry_type_polygonal",
            bool(geom_type_ok),
            detail=(
                f"got geometry types {sorted(geom_types)}, "
                "expected subset of {Polygon, MultiPolygon}"
            ),
        )
    )

    # No null or empty geometries in the output.
    report.subchecks.append(
        Subcheck(
            "no_null_or_empty_geometry",
            no_null_geom_present,
            detail=(
                "all geometries non-null and non-empty"
                if no_null_geom_present
                else "submission contains null or empty geometries"
            ),
            weight=2.0,
        )
    )

    # Row count within ±5% of the four-row reference.
    count_ok = count_within_tolerance(sub, ref, pct=0.05)
    report.subchecks.append(
        Subcheck(
            "feature_count_within_tolerance",
            bool(count_ok),
            detail=f"submission {len(sub)} vs reference {len(ref)} (±5%)",
            weight=2.0,
        )
    )

    sub_classes = (
        sub["zoning_class"].dropna().astype(str).str.strip().tolist()
    )

    # 1. zoning_class set matches the canonical four values exactly.
    class_set = set(sub_classes)
    classes_ok = class_set == CANONICAL_CLASSES
    report.subchecks.append(
        Subcheck(
            "canonical_class_vocabulary",
            classes_ok,
            detail=f"got {sorted(class_set)}, expected {sorted(CANONICAL_CLASSES)}",
            weight=1.0,
        )
    )

    # 2. No blank / whitespace / null zoning_class values.
    raw_classes = sub["zoning_class"]
    blanks = (
        raw_classes.isna()
        | (raw_classes.astype(str).str.strip() == "")
    )
    no_blanks = bool(~blanks.any())
    report.subchecks.append(
        Subcheck(
            "no_blank_class_rows",
            no_blanks,
            detail=f"{int(blanks.sum())} rows have blank/null zoning_class",
            weight=2.0,
        )
    )

    # 3. No zero-area geometries.
    sub_areas = sub.geometry.area
    n_zero = int((sub_areas <= 0).sum())
    report.subchecks.append(
        Subcheck(
            "no_zero_area_geometries",
            n_zero == 0,
            detail=f"{n_zero} rows have area ≤ 0",
            weight=2.0,
        )
    )

    # 4. area_m2 recomputed from the surviving geometry. Pass when ≥ 95 %
    #    of rows agree with their own geometry.area within
    #    max(1 m², 1e-3 relative).
    if "area_m2" in sub.columns:
        try:
            col = sub["area_m2"].astype(float)
            calc = sub.geometry.area
            denom = calc.abs().clip(lower=1e-12)
            rel = (col - calc).abs() / denom
            absdiff = (col - calc).abs()
            ok_mask = (rel <= AREA_REL_TOL_RECOMPUTE) | (
                absdiff <= AREA_ABS_TOL_RECOMPUTE_M2
            )
            n_ok = int(ok_mask.fillna(False).sum())
            recompute_pass = n_ok >= 0.95 * len(sub)
            recompute_detail = (
                f"{n_ok}/{len(sub)} rows have area_m2 within "
                f"max(1 m², 1e-3 rel) of geometry.area"
            )
        except Exception as exc:
            recompute_pass = False
            recompute_detail = (
                f"could not coerce area_m2 to float: {type(exc).__name__}: {exc}"
            )
    else:
        recompute_pass = False
        recompute_detail = "no area_m2 column"
    report.subchecks.append(
        Subcheck("area_m2_recomputed", bool(recompute_pass), detail=recompute_detail, weight=2.0)
    )

    # 5. Per-class area within ±0.5 % of the reference 250 000 m². The
    #    snap-then-dissolve operation is exact in principle (every
    #    coordinate rounds to a 1 mm grid; quadrants are 500 m squares)
    #    so a tighter tolerance than the L2 default 5 % is principled
    #    here. Applies only over classes the submission and reference
    #    both expose.
    # Match classes case-insensitively so an agent that picked the
    # wrong casing still gets credit on the per-class-area check —
    # the casing concern lives in canonical_class_vocabulary.
    sub_by_class = (
        sub.dropna(subset=["zoning_class"])
        .assign(_class=sub["zoning_class"].astype(str).str.strip().str.casefold())
        .groupby("_class")["geometry"]
        .apply(lambda gs: float(gs.area.sum()))
    )
    deviations = []
    per_class_pass = True
    for canonical in CANONICAL_CLASSES:
        key = canonical.casefold()
        if key not in sub_by_class.index:
            per_class_pass = False
            deviations.append(f"{canonical}=missing")
            continue
        a = sub_by_class[key]
        rel = abs(a - EXPECTED_AREA_M2) / EXPECTED_AREA_M2
        deviations.append(f"{canonical}={a:,.1f} (Δ={rel*100:.3f}%)")
        if rel > AREA_REL_TOL_VS_REF:
            per_class_pass = False
    report.subchecks.append(
        Subcheck(
            "per_class_area_matches_reference",
            bool(per_class_pass),
            detail="; ".join(deviations),
            weight=2.0,
        )
    )

    # 6. Geometric IoU vs the reference union ≥ 0.99.
    try:
        extent_iou = iou_with_tolerance(sub, ref, eps=0.0)
        extent_pass = extent_iou >= 0.99
        extent_detail = f"union IoU {extent_iou:.4f}"
    except Exception as exc:
        extent_iou = 0.0
        extent_pass = False
        extent_detail = f"union failed: {type(exc).__name__}: {exc}"
    report.subchecks.append(
        Subcheck("geometric_extent_matches_reference", bool(extent_pass), extent_detail, weight=2.0)
    )

    # 7. Geometry simplicity: zero interior holes anywhere. For
    #    MultiPolygon submissions we count holes across every part.
    n_holes = 0
    for g in sub.geometry:
        if g is None:
            continue
        if g.geom_type == "Polygon":
            n_holes += len(g.interiors)
        elif g.geom_type == "MultiPolygon":
            n_holes += sum(len(p.interiors) for p in g.geoms)
    report.subchecks.append(
        Subcheck(
            "no_interior_holes",
            n_holes == 0,
            detail=f"{n_holes} interior ring(s) found across all output polygons",
            weight=3.0,
        )
    )

    # 8. Strict Polygon-only geometry type. The inventory declares
    #    Polygon; a clean snap+dissolve yields four 500 m × 500 m
    #    single-part Polygons. A MultiPolygon means the snap or
    #    dissolve failed even if the grader admitted it through Gate 2.
    polygon_strict_ok = geom_types == {"Polygon"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_polygon_only",
            polygon_strict_ok,
            detail=f"got geometry types {sorted(geom_types)}",
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
