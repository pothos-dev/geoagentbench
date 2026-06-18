"""Grader for crs-l1-paris-lambert93.

One hard gate (``format_schema_valid``): the file exists, parses as a
readable geospatial file (GeoPackage), has a usable geometry column, and
declares some usable CRS. A submission with no declarable CRS is
unrecoverable — the grader can't reproject to canonical.

Subchecks are tighter than the heuristic L1 defaults because the task's
central skill is *projection accuracy* — pyproj/PROJ is deterministic
for EPSG:4326 → EPSG:2154, so a correct projection produces
near-identical coordinates and per-feature areas. Two CRS subchecks at
the end grade the agent's CRS pick:
- `crs_is_canonical` — declared CRS is EPSG:2154 (Lambert-93, the
  spec'd output CRS).
- `crs_in_meaningful_set` — declared CRS is in {EPSG:2154,
  EPSG:32631}. UTM 31N (EPSG:32631) is the defensible generic metric
  CRS for Paris; an agent that picked it instead of Lambert-93 loses
  the canonical subcheck but stays inside the meaningful set.

Subcheck weights (per-task reasoned, replacing the project-wide
05b389b 3x-content weighting on 2026-06-14). This is a
CRS-selection-primary task, so CRS-correctness dominates the budget.
Two groups carry the high weight:
- CRS-declaration (weight 5): `crs_is_canonical`, `crs_in_meaningful_set`
  — did the agent pick the official French grid?
- CRS-correctness / transform-proof: `coordinates_within_lambert93_paris_envelope`
  (weight 5, functionally a CRS check — it proves the reprojection
  actually happened), `geometry_iou_high`, `per_feature_area_matches`,
  `total_area_within_1_percent` (weight 3 each).
Data-content (`feature_count_within_5_percent`, `feature_id_set_preserved`,
`identifying_attributes_preserved`) and structural
(`geometry_type_is_polygon`, `original_columns_preserved`) checks carry
weight 1. Total weight 29.

This weighting penalises BOTH CRS brokens hard while avoiding a
severity inversion: the honestly-unprojected file (declares 4326, fails
the two declaration checks; geometry passes because the grader
reprojects it) loses 10/29 → 0.655; the silent-corruption file (stamps
2154 but coords still in degrees, so it passes the declaration checks
but fails the four transform-proof checks) loses 14/29 → 0.517. Because
the high-weight envelope check is a transform-proof check rather than a
declaration label, the silent corruption scores *below* the honest
miss, which is the correct severity ordering.
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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "paris_buildings_lambert93.gpkg"
OUTPUT_NAME = "paris_buildings_lambert93.gpkg"

CANONICAL_EPSG = 2154
MEANINGFUL_EPSGS = {2154, 32631}

# Lambert-93 (EPSG:2154) places Paris in the ~ 650 km easting / 6862 km
# northing band (false easting 700 km, false northing 6 600 km). A correctly
# reprojected Marais slice falls inside a generous Paris-area envelope; a
# slice in lon/lat or in any other projection lands degrees-of-magnitude
# outside this box.
PARIS_LAMBERT93_X_MIN, PARIS_LAMBERT93_X_MAX = 600_000, 700_000
PARIS_LAMBERT93_Y_MIN, PARIS_LAMBERT93_Y_MAX = 6_800_000, 6_900_000


def _read_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="crs-l1-paris-lambert93")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format/schema validity --------------------------------
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
            Gate("format_schema_valid", False, "could not read output file")
        )
        return report

    crs_res = grade_crs_soft(
        sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True
    )
    has_geometry = sub.geometry is not None and not sub.geometry.is_empty.all()

    if not (crs_res.gate_ok and has_geometry):
        reason_parts = []
        if not crs_res.gate_ok:
            reason_parts.append(crs_res.gate_reason)
        if not has_geometry:
            reason_parts.append("no usable geometry column")
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(reason_parts))
        )
        return report

    sub = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    ref = gpd.read_file(REFERENCE_OUT)
    geom_types = set(sub.geometry.geom_type.unique())

    # ---- Subchecks ------------------------------------------------------
    # 0. Feature count within 5 % of reference.
    count_ok = count_within_tolerance(sub, ref, pct=0.05)
    report.subchecks.append(
        Subcheck(
            "feature_count_within_5_percent",
            bool(count_ok),
            detail=f"sub rows {len(sub)}; ref rows {len(ref)}",
            weight=1.0,
        )
    )

    # 1. Geometry type is Polygon (the input is Polygon-only; an SUT that
    #    upcasts everything to MultiPolygon still passes the structural gate
    #    but does not earn this subcheck).
    polygon_only = geom_types == {"Polygon"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_is_polygon",
            bool(polygon_only),
            detail=f"types observed: {sorted(geom_types)}",
        )
    )

    # 2. Feature-id Jaccard ≥ 0.95 (preserved through reprojection).
    id_jaccard = feature_set_equality_by_id(sub, ref, key="id")
    report.subchecks.append(
        Subcheck(
            "feature_id_set_preserved",
            bool(id_jaccard >= 0.95),
            detail=f"Jaccard {id_jaccard:.4f}",
            weight=1.0,
        )
    )

    # 3. Coordinates fall inside the Paris-area Lambert-93 envelope. This is
    #    the canonical catch for "stamped CRS as 2154 but did not actually
    #    reproject" — WGS84 longitudes for Paris are ~ 2.36° / 48.86°,
    #    nowhere near the 6.5e5 / 6.86e6 metres band.
    xmin, ymin, xmax, ymax = sub.total_bounds
    in_paris_envelope = (
        PARIS_LAMBERT93_X_MIN <= xmin <= PARIS_LAMBERT93_X_MAX
        and PARIS_LAMBERT93_X_MIN <= xmax <= PARIS_LAMBERT93_X_MAX
        and PARIS_LAMBERT93_Y_MIN <= ymin <= PARIS_LAMBERT93_Y_MAX
        and PARIS_LAMBERT93_Y_MIN <= ymax <= PARIS_LAMBERT93_Y_MAX
    )
    report.subchecks.append(
        Subcheck(
            "coordinates_within_lambert93_paris_envelope",
            bool(in_paris_envelope),
            detail=(
                f"bbox=({xmin:.0f}, {ymin:.0f}, {xmax:.0f}, {ymax:.0f}); "
                f"expected x∈[{PARIS_LAMBERT93_X_MIN}, {PARIS_LAMBERT93_X_MAX}], "
                f"y∈[{PARIS_LAMBERT93_Y_MIN}, {PARIS_LAMBERT93_Y_MAX}]"
            ),
            weight=5.0,
        )
    )

    # 4. Geometric IoU on dissolved polygons. Catches CRS-wrong reprojections
    #    that happen to land in the right numeric range with distorted shape,
    #    plus geometry-perturbation errors. With pyproj/PROJ on both sides
    #    the IoU should be ≥ 0.999; the 0.95 floor absorbs the buffer/de-buffer
    #    eps inside `iou_with_tolerance` and minor sanitisation by the SUT's
    #    GeoJSON writer.
    iou = iou_with_tolerance(sub, ref, eps=0.001)
    report.subchecks.append(
        Subcheck(
            "geometry_iou_high",
            bool(iou >= 0.95),
            detail=f"IoU {iou:.6f}",
            weight=3.0,
        )
    )

    # 5. Per-feature area match. A correct EPSG:2154 reprojection produces
    #    `.area` values (in m²) that agree to ppm with the reference; 1 %
    #    absorbs minor numeric drift through e.g. WKT round-trips.
    sub_areas = sub.assign(_area_m2=sub.geometry.area).loc[:, ["id", "_area_m2"]]
    ref_areas = ref.assign(_area_m2=ref.geometry.area).loc[:, ["id", "_area_m2"]]
    area_match = attribute_match(
        sub_areas,
        ref_areas,
        fields=["_area_m2"],
        key="id",
        tolerance=0.01,
    )
    area_match_rate = area_match["_area_m2"]
    report.subchecks.append(
        Subcheck(
            "per_feature_area_matches",
            bool(area_match_rate >= 0.95),
            detail=f"per-id area match rate {area_match_rate:.4f}",
            weight=3.0,
        )
    )

    # 6. Total polygon area within 1 % of reference. Catches systematic scale
    #    errors (e.g., reprojecting into the wrong metric CRS).
    sub_total = float(sub.geometry.area.sum())
    ref_total = float(ref.geometry.area.sum())
    total_pct_diff = abs(sub_total - ref_total) / max(ref_total, 1e-9)
    report.subchecks.append(
        Subcheck(
            "total_area_within_1_percent",
            bool(total_pct_diff <= 0.01),
            detail=(
                f"sub total {sub_total:.1f} m²; "
                f"ref total {ref_total:.1f} m²; rel diff {total_pct_diff:.4%}"
            ),
            weight=3.0,
        )
    )

    # 7. Identifying string attributes preserved (class, subtype, name).
    #    Reprojection must not touch attributes; this catches accidental drop /
    #    rename / blanking and the "I forgot to carry the metadata" failure
    #    mode. height / num_floors are mostly NaN in this slice and are
    #    covered by the column-presence subcheck instead.
    attr_match = attribute_match(
        sub.drop(columns="geometry"),
        ref.drop(columns="geometry"),
        fields=["class", "subtype", "name"],
        key="id",
    )
    attrs_preserved = (
        attr_match["class"] >= 0.95
        and attr_match["subtype"] >= 0.95
        and attr_match["name"] >= 0.95
    )
    report.subchecks.append(
        Subcheck(
            "identifying_attributes_preserved",
            bool(attrs_preserved),
            detail=(
                f"class match {attr_match['class']:.4f}; "
                f"subtype match {attr_match['subtype']:.4f}; "
                f"name match {attr_match['name']:.4f}"
            ),
            weight=1.0,
        )
    )

    # 8. Original column set preserved. Catches the case where the SUT
    #    silently drops the (mostly-NaN but still meaningful) `height` /
    #    `num_floors` columns — they would matter for the downstream
    #    heat-loss model even if many slice rows lack values.
    required = {"id", "class", "subtype", "name", "height", "num_floors"}
    missing = required - set(sub.columns)
    report.subchecks.append(
        Subcheck(
            "original_columns_preserved",
            bool(not missing),
            detail=(
                f"missing columns: {sorted(missing)}" if missing else "all present"
            ),
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
            weight=5.0,
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
            weight=5.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
