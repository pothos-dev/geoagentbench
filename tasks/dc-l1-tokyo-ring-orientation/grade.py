"""Grader for dc-l1-tokyo-ring-orientation.

Single hard gate (`format_schema_valid`) when the file is missing,
unreadable, lacks a usable CRS, or is missing required columns.
Everything else is a one-point subcheck.

The task's central skill is RFC 7946 §3.1.6 *ring-orientation repair*,
so the two orientation subchecks (exterior CCW, interior CW) are tested
independently from geometric- and attribute-preservation subchecks. An
agent that left the file untouched passes every preservation subcheck
but fails both orientation subchecks; an agent that fixed exteriors but
missed interiors fails only the interior subcheck.

Subcheck weights are tiered by error severity rather than uniform:
- Central skill, weight 5: `exterior_rings_ccw`, `interior_rings_cw`.
  These are the operation the task asks for; failing them means the
  core work was not done.
- Structural-identity preservation, weight 3: `feature_id_set_preserved`,
  `polygons_with_holes_preserved`, `attributes_preserved`. Losing an id,
  a hole, or an attribute is unrecoverable data corruption.
- Geometric-drift guards, weight 2: `feature_count_within_tolerance`,
  `geometric_extent_preserved`, `per_feature_geometry_preserved`. These
  catch a stray simplify/buffer/filter — a quality degradation rather
  than the central skill or an identity loss.
- Cosmetic, weight 1: `geometry_type_polygon_only`, `crs_is_canonical`,
  `crs_in_meaningful_set`. A wrong-but-reasonable CRS only lightly docks
  the score; the geometric work is still graded on its own merits.
Weighted denominator: 28. Both orientation checks failing -> 0.643;
interior-only failing -> 0.821; a CRS slip alone -> 0.964.

The agent's choice of CRS is graded as two soft subchecks
(`crs_is_canonical`, `crs_in_meaningful_set`) so a wrong-but-reasonable
CRS still scores the geometric work. RFC 7946 implicit WGS84 is
honoured for GeoJSON inputs whose `crs` member is absent.
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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_buildings_fixed.geojson"
OUTPUT_NAME = "tokyo_buildings_fixed.geojson"

REQUIRED_COLUMNS = {
    "feature_id",
    "overture_id",
    "name_primary",
    "building_class",
    "height",
}
ATTRIBUTE_FIELDS = ["overture_id", "name_primary", "building_class"]

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}


def _read_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def _ring_orientation_summary(gdf: gpd.GeoDataFrame) -> tuple[int, int, int, int]:
    """Return (n_polygons, n_with_holes, n_exterior_ccw, n_interior_cw_rings).

    `n_interior_cw_rings` counts interior rings (across all polygons)
    that satisfy `not is_ccw` (i.e., CW = RFC-7946-compliant). The total
    number of interior rings is reported separately by callers.
    """
    n_polys = 0
    n_with_holes = 0
    n_ext_ccw = 0
    n_int_cw = 0
    for geom in gdf.geometry:
        if geom is None or geom.is_empty:
            continue
        if geom.geom_type != "Polygon":
            continue
        n_polys += 1
        if geom.exterior.is_ccw:
            n_ext_ccw += 1
        interiors = list(geom.interiors)
        if interiors:
            n_with_holes += 1
            for ring in interiors:
                if not ring.is_ccw:
                    n_int_cw += 1
    return n_polys, n_with_holes, n_ext_ccw, n_int_cw


def _total_interior_rings(gdf: gpd.GeoDataFrame) -> int:
    return sum(
        len(list(g.interiors))
        for g in gdf.geometry
        if g is not None and not g.is_empty and g.geom_type == "Polygon"
    )


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dc-l1-tokyo-ring-orientation")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format/schema validity ----------------------------------
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
            Gate("format_schema_valid", False, "could not read GeoJSON")
        )
        return report

    missing = REQUIRED_COLUMNS - set(sub.columns)
    columns_ok = not missing

    crs_res = grade_crs_soft(
        sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True
    )

    if not (crs_res.gate_ok and columns_ok):
        reason_parts = []
        if not crs_res.gate_ok:
            reason_parts.append(crs_res.gate_reason)
        if not columns_ok:
            reason_parts.append(f"missing columns: {sorted(missing)}")
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(reason_parts))
        )
        return report

    sub = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = gpd.read_file(REFERENCE_OUT)

    # Geometry-type uniformity (Polygon) — salvageable subcheck.
    geom_types = set(sub.geometry.geom_type.unique())
    geom_type_ok = geom_types == {"Polygon"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_polygon_only",
            bool(geom_type_ok),
            detail=f"got geometry types {sorted(geom_types)}, expected Polygon",
        )
    )

    # Feature count within ±5% of the reference.
    # Geometric-drift guard (weight 2): a gross row drop/dup is real
    # corruption but not the central ring-orientation skill, and the
    # ±5% window only bites on coarse changes — finer set drift is
    # caught by feature_id_set_preserved (weight 3).
    count_ok = count_within_tolerance(sub, ref, pct=0.05)
    report.subchecks.append(
        Subcheck(
            "feature_count_within_tolerance",
            bool(count_ok),
            detail=f"submission {len(sub)} vs reference {len(ref)} (±5%)",
            weight=2.0,
        )
    )

    n_sub_polys, n_sub_holes, n_sub_ext_ccw, n_sub_int_cw = _ring_orientation_summary(
        sub
    )
    sub_total_interiors = _total_interior_rings(sub)

    # 1. RFC 7946 §3.1.6 — every exterior ring must be CCW.
    #    The central skill of the task, so this carries the top weight
    #    (5). Strict 100% pass: a Polygon's signed area is well-defined
    #    for all non-degenerate footprints in the bundled fixture, so a
    #    partial pass would silently accept a bug.
    ext_pass = n_sub_polys > 0 and n_sub_ext_ccw == n_sub_polys
    report.subchecks.append(
        Subcheck(
            "exterior_rings_ccw",
            bool(ext_pass),
            detail=(
                f"{n_sub_ext_ccw}/{n_sub_polys} polygons have CCW exterior "
                "(RFC 7946 §3.1.6 requires CCW exterior)"
            ),
            weight=5.0,
        )
    )

    # 2. RFC 7946 §3.1.6 — every interior ring must be CW.
    #    Vacuously true if the submission has no interior rings, but only
    #    if the reference also has no interior rings; otherwise the agent
    #    has likely dropped holes and the next subcheck will catch that.
    if sub_total_interiors == 0:
        # Reference does have holes; vacuous pass here would mask hole loss.
        # We still award the orientation subcheck if there are no interiors
        # to grade, because the rule has no targets — the dropped-holes
        # failure is caught by `polygons_with_holes_preserved`.
        int_pass = True
        int_detail = "no interior rings in submission (vacuously satisfied)"
    else:
        int_pass = n_sub_int_cw == sub_total_interiors
        int_detail = (
            f"{n_sub_int_cw}/{sub_total_interiors} interior rings are CW "
            "(RFC 7946 §3.1.6 requires CW interior)"
        )
    #    Interior orientation is the second clause of the central skill,
    #    so it carries the same top weight (5) as the exterior check.
    report.subchecks.append(
        Subcheck("interior_rings_cw", bool(int_pass), detail=int_detail, weight=5.0)
    )

    # 3. The set of `feature_id`s is preserved. Catches accidental row
    #    drops or duplications that slip through the ±5% count subcheck.
    #    Structural-identity preservation (weight 3): losing the id set is
    #    unrecoverable corruption, more severe than a geometric-drift slip.
    id_jaccard = feature_set_equality_by_id(sub, ref, key="feature_id")
    report.subchecks.append(
        Subcheck(
            "feature_id_set_preserved",
            bool(id_jaccard >= 0.95),
            detail=f"feature_id Jaccard {id_jaccard:.4f}",
            weight=3.0,
        )
    )

    # 4. Geometric extent preserved. Orientation repair must not move,
    #    simplify, or buffer any vertex; the union of polygons must be
    #    geometrically equal to the reference's union (IoU ≥ 0.99).
    #    Geometric-drift guard (weight 2): catches an unintended
    #    simplify/buffer/vertex edit, a quality degradation rather than
    #    the central orientation skill or a structural-identity loss.
    extent_iou = iou_with_tolerance(sub, ref, eps=0.0)
    report.subchecks.append(
        Subcheck(
            "geometric_extent_preserved",
            bool(extent_iou >= 0.99),
            detail=f"union IoU {extent_iou:.4f}",
            weight=2.0,
        )
    )

    # 5. Polygons-with-holes preserved. Some agents fix orientation by
    #    extracting and re-encoding only the exterior ring, silently
    #    dropping every interior ring; that change is invisible to a
    #    pure-area metric (a polygon with a small hole has nearly the
    #    same area as the polygon with the hole filled in) but matters
    #    structurally. We require the count of polygons-with-holes to
    #    match the reference. Structural-identity preservation (weight 3).
    n_ref_polys, n_ref_holes, _, _ = _ring_orientation_summary(ref)
    holes_ok = n_sub_holes == n_ref_holes
    report.subchecks.append(
        Subcheck(
            "polygons_with_holes_preserved",
            bool(holes_ok),
            detail=(
                f"{n_sub_holes} polygons with holes in submission, "
                f"{n_ref_holes} in reference"
            ),
            weight=3.0,
        )
    )

    # 6. Attributes preserved verbatim per `feature_id`. Structural-
    #    identity preservation (weight 3): silently corrupting an
    #    attribute is unrecoverable, on the same tier as id/hole loss.
    sub_attrs = sub[["feature_id"] + ATTRIBUTE_FIELDS].copy()
    ref_attrs = ref[["feature_id"] + ATTRIBUTE_FIELDS].copy()
    sub_attrs["feature_id"] = sub_attrs["feature_id"].astype(str)
    ref_attrs["feature_id"] = ref_attrs["feature_id"].astype(str)
    attr_match = attribute_match(
        sub_attrs, ref_attrs, fields=ATTRIBUTE_FIELDS, key="feature_id"
    )
    attrs_ok = all(attr_match[f] >= 0.95 for f in ATTRIBUTE_FIELDS)
    report.subchecks.append(
        Subcheck(
            "attributes_preserved",
            bool(attrs_ok),
            detail="; ".join(
                f"{f}={attr_match[f]:.3f}" for f in ATTRIBUTE_FIELDS
            ),
            weight=3.0,
        )
    )

    # 7. Per-feature geometric equality. Joins by `feature_id` and checks
    #    that each pair of polygons has IoU ≥ 0.99 — orientation flip is
    #    a no-op on geometry, so any drift here flags an unintended edit
    #    (simplification, buffering, vertex deletion).
    sub_geom = sub[["feature_id", "geometry"]].copy()
    ref_geom = ref[["feature_id", "geometry"]].copy()
    sub_geom["feature_id"] = sub_geom["feature_id"].astype(str)
    ref_geom["feature_id"] = ref_geom["feature_id"].astype(str)
    sub_geom = sub_geom.set_index("feature_id")
    ref_geom = ref_geom.set_index("feature_id")
    common = sorted(set(sub_geom.index) & set(ref_geom.index))
    if not common:
        per_id_pass_rate = 0.0
    else:
        passes = 0
        for fid in common:
            sg = sub_geom.loc[fid, "geometry"]
            rg = ref_geom.loc[fid, "geometry"]
            if sg is None or rg is None or sg.is_empty or rg.is_empty:
                continue
            if iou_with_tolerance(sg, rg, eps=0.0) >= 0.99:
                passes += 1
        per_id_pass_rate = passes / len(common)
    #    Geometric-drift guard (weight 2): same severity tier as the
    #    union-extent check — a moved vertex degrades quality but is not
    #    the central orientation skill or a structural-identity loss.
    report.subchecks.append(
        Subcheck(
            "per_feature_geometry_preserved",
            bool(per_id_pass_rate >= 0.95),
            detail=(
                f"{per_id_pass_rate:.4f} of {len(common)} matched "
                "feature_ids have IoU ≥ 0.99"
            ),
            weight=2.0,
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
