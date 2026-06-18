"""Grader for crs-l2-fiji-antimeridian.

One hard gate (``format_schema_valid``): the file exists, parses as
GeoJSON, declares some usable CRS (or is RFC 7946 implicit WGS84), and
carries the required schema (`transect_id`, `length_m`). A submission
with no declarable CRS is unrecoverable — the grader can't reproject to
canonical. Whenever the gate passes, the submission is reprojected into
Fiji Map Grid (EPSG:3460) before spatial subchecks run.

Subchecks are tighter than the heuristic L2 defaults because the
question is projection accuracy on a fixed bundled input — pyproj/PROJ
EPSG:4326 → EPSG:3460 is deterministic, so a correct solution agrees to
ppm on length and to sub-millimetre on geometry. Two CRS subchecks
grade the agent's CRS pick:
- `crs_is_canonical` — declared CRS is EPSG:3460 (Fiji Map Grid, the
  spec'd output CRS and the regional canonical).
- `crs_in_meaningful_set` — declared CRS is in {EPSG:3460,
  EPSG:32760}. UTM 60S is a defensible generic alternative; its band
  covers most of the bundled archipelago west of the antimeridian.
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
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "fiji_transects_fmg.geojson"
OUTPUT_NAME = "fiji_transects_fmg.geojson"

# Fiji 1986 / Fiji Map Grid (EPSG:3460) is Fiji's national projected
# metric CRS and the canonical pick. UTM 60S (EPSG:32760) is the
# defensible generic alternative — its band covers most of the bundled
# archipelago west of the antimeridian and an agent who picks it is
# reasoning generically rather than regionally.
CANONICAL_EPSG = 3460
MEANINGFUL_EPSGS = {3460, 32760}

# Fiji Map Grid (EPSG:3460) places Fiji easting around 1.6 – 2.5 × 10⁶
# and northing around 3.7 – 4.0 × 10⁶ for the bundled bbox. A correctly
# reprojected slice falls inside this generous Fiji envelope; degrees
# (lat/lon) or any non-FMG metric CRS lands orders of magnitude
# outside it.
FMG_X_MIN, FMG_X_MAX = 1_400_000, 2_700_000
FMG_Y_MIN, FMG_Y_MAX = 3_500_000, 4_100_000


def _read_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="crs-l2-fiji-antimeridian")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format/schema validity --------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output: {OUTPUT_NAME}")
        )
        return report

    sub = _read_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GeoJSON")
        )
        return report

    # Soft-grade the CRS pick. The gate fails only when the submission
    # has no usable CRS at all; any parseable CRS passes the gate and
    # gets reprojected into Fiji Map Grid for downstream spatial
    # subchecks. The two CRS subchecks (appended at the end) grade the
    # agent's canonical-vs-meaningful-vs-other pick.
    crs_res = grade_crs_soft(
        sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True
    )
    if crs_res.gate_ok:
        sub = crs_res.normalized
    has_geometry = sub.geometry is not None and not sub.geometry.is_empty.all()
    has_length = "length_m" in sub.columns
    has_id = "transect_id" in sub.columns

    if not (crs_res.gate_ok and has_geometry and has_length and has_id):
        reason_parts = []
        if not crs_res.gate_ok:
            reason_parts.append(crs_res.gate_reason)
        if not has_geometry:
            reason_parts.append("no usable geometry column")
        if not has_length:
            reason_parts.append("missing length_m column")
        if not has_id:
            reason_parts.append("missing transect_id column")
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(reason_parts))
        )
        return report

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

    # 1. Geometry type is MultiLineString throughout. The task asks for
    #    each transect re-assembled as MultiLineString; an SUT that
    #    leaves non-crossing transects as plain LineString fails this
    #    subcheck (but still passes the gate).
    multi_only = geom_types == {"MultiLineString"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_is_multilinestring",
            bool(multi_only),
            detail=f"types observed: {sorted(geom_types)}",
        )
    )

    # 2. transect_id set is preserved (Jaccard ≥ 0.95).
    id_jaccard = feature_set_equality_by_id(sub, ref, key="transect_id")
    report.subchecks.append(
        Subcheck(
            "transect_id_set_preserved",
            bool(id_jaccard >= 0.95),
            detail=f"Jaccard {id_jaccard:.4f}",
            weight=1.5,
        )
    )

    # 3. Coordinates fall inside the Fiji-area FMG envelope. The
    #    canonical catch for "stamped CRS as 3460 but didn't reproject"
    #    or "reprojected the antimeridian-crossing lines without
    #    splitting first, producing wild coordinates 20× wider than the
    #    Fiji bbox".
    xmin, ymin, xmax, ymax = sub.total_bounds
    in_envelope = (
        FMG_X_MIN <= xmin <= FMG_X_MAX
        and FMG_X_MIN <= xmax <= FMG_X_MAX
        and FMG_Y_MIN <= ymin <= FMG_Y_MAX
        and FMG_Y_MIN <= ymax <= FMG_Y_MAX
    )
    report.subchecks.append(
        Subcheck(
            "coordinates_within_fmg_fiji_envelope",
            bool(in_envelope),
            detail=(
                f"bbox=({xmin:.0f}, {ymin:.0f}, {xmax:.0f}, {ymax:.0f}); "
                f"expected x∈[{FMG_X_MIN}, {FMG_X_MAX}], "
                f"y∈[{FMG_Y_MIN}, {FMG_Y_MAX}]"
            ),
            weight=2.0,
        )
    )

    # 4. Per-transect length matches the reference within 1 %. This is
    #    the central correctness check — an SUT that fails to split at
    #    the antimeridian and reprojects the raw 359°-long line will
    #    produce length_m values orders of magnitude larger than
    #    reference for the 10 crossing transects.
    length_match = attribute_match(
        sub.drop(columns="geometry"),
        ref.drop(columns="geometry"),
        fields=["length_m"],
        key="transect_id",
        tolerance=0.01,
    )
    length_match_rate = length_match["length_m"]
    report.subchecks.append(
        Subcheck(
            "per_transect_length_matches",
            bool(length_match_rate >= 0.95),
            detail=f"per-id length_m match rate {length_match_rate:.4f}",
            weight=3.0,
        )
    )

    # 5. Total length within 1 % of reference. Catches systematic scale
    #    errors (wrong projection, length computed in degrees, length
    #    computed before splitting at antimeridian).
    sub_total = float(sub["length_m"].sum())
    ref_total = float(ref["length_m"].sum())
    total_pct_diff = abs(sub_total - ref_total) / max(ref_total, 1e-9)
    report.subchecks.append(
        Subcheck(
            "total_length_within_1_percent",
            bool(total_pct_diff <= 0.01),
            detail=(
                f"sub total {sub_total:.1f} m; ref total {ref_total:.1f} m; "
                f"rel diff {total_pct_diff:.4%}"
            ),
            weight=2.0,
        )
    )

    # 6. Multi-part assembly: the ten transects T001–T010 cross the
    #    antimeridian and *must* end up with ≥2 parts in their
    #    MultiLineString. An SUT that reprojects the 359°-long lines
    #    without splitting will land them as 1-part Multi (or as plain
    #    LineString upcast to Multi).
    crossing_ids = [f"T{i:03d}" for i in range(1, 11)]
    sub_indexed = sub.set_index(sub["transect_id"].astype(str))
    n_split_correctly = 0
    for tid in crossing_ids:
        if tid not in sub_indexed.index:
            continue
        g = sub_indexed.loc[tid].geometry
        n_parts = len(g.geoms) if hasattr(g, "geoms") else 1
        if n_parts >= 2:
            n_split_correctly += 1
    split_rate = n_split_correctly / len(crossing_ids)
    report.subchecks.append(
        Subcheck(
            "antimeridian_crossings_split_into_multi_parts",
            bool(split_rate >= 0.9),
            detail=(
                f"{n_split_correctly}/{len(crossing_ids)} crossing transects "
                f"have ≥2 parts in MultiLineString"
            ),
            weight=4.0,
        )
    )

    # 7. Identifying string attributes preserved (vessel, survey_date).
    attr_match = attribute_match(
        sub.drop(columns="geometry"),
        ref.drop(columns="geometry"),
        fields=["vessel", "survey_date"],
        key="transect_id",
    )
    attrs_preserved = (
        attr_match["vessel"] >= 0.95 and attr_match["survey_date"] >= 0.95
    )
    report.subchecks.append(
        Subcheck(
            "identifying_attributes_preserved",
            bool(attrs_preserved),
            detail=(
                f"vessel match {attr_match['vessel']:.4f}; "
                f"survey_date match {attr_match['survey_date']:.4f}"
            ),
            weight=1.0,
        )
    )

    # Fiji 1986 / Fiji Map Grid is the regional canonical pick. UTM 60S
    # is the defensible generic alternative — accepted as meaningful but
    # docked the canonical subcheck.
    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            crs_res.is_canonical,
            detail=(
                f"original EPSG:{crs_res.original_epsg}; "
                f"canonical EPSG:{CANONICAL_EPSG} (Fiji 1986 / Fiji Map Grid)"
            ),
            weight=0.5,
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
