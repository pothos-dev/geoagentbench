"""Grader for crs-l1-nyc-webmercator-cycleways.

One hard gate (``format_schema_valid``): the file exists, parses as
GeoParquet, has a usable geometry column, and declares some usable CRS.
A submission with no declarable CRS is unrecoverable — the grader can't
reproject to canonical and downstream geometric subchecks become
undefined.

Subchecks are tighter than the heuristic L1 defaults because the task's
central skill is *projection accuracy* — pyproj/PROJ is deterministic
for EPSG:3857 → EPSG:4326, so the correct projection produces
near-identical coordinates and per-feature lengths. Two CRS subchecks
at the end grade the agent's CRS pick:
- `crs_is_canonical` — declared CRS is EPSG:4326 (the spec'd output CRS).
- `crs_in_meaningful_set` — declared CRS is in {EPSG:4326}. Any other
  CRS is docked once for not being canonical and again for being
  outside the meaningful set.
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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "nyc_cycleways_wgs84.geoparquet"
OUTPUT_NAME = "nyc_cycleways_wgs84.geoparquet"

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}

# NYC envelope (Manhattan + inner Brooklyn / Queens). Generous: anything inside
# this box is plausibly NYC; anything outside means the SUT either skipped
# the reprojection or chose the wrong target CRS.
NYC_LON_MIN, NYC_LON_MAX = -74.10, -73.85
NYC_LAT_MIN, NYC_LAT_MAX = 40.65, 40.85


def _read_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_parquet(path)
    except Exception:
        return None


def _ensure_id_column(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # The instruction says "use `id` as the key" — some agents read that
    # as `set_index("id")`, which leaves no `id` column for the grader's
    # comparators. Lift it back out so column-based lookups work.
    if "id" not in df.columns and df.index.name == "id":
        df = df.reset_index()
    return df


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="crs-l1-nyc-webmercator-cycleways")
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
            Gate(
                "format_schema_valid",
                False,
                "could not read GeoParquet (missing geo metadata or unreadable bytes)",
            )
        )
        return report

    crs_res = grade_crs_soft(sub, MEANINGFUL_EPSGS, CANONICAL_EPSG)
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

    sub = _ensure_id_column(crs_res.normalized)
    report.gates.append(Gate("format_schema_valid", True))

    ref = _ensure_id_column(gpd.read_parquet(REFERENCE_OUT))
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

    # 1. Geometry type is exactly LineString (task contract — declared
    #    geometry_type is LineString; MultiLineString is allowed at the
    #    structural gate but only LineString-only earns the subcheck).
    linestring_only = geom_types == {"LineString"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_is_linestring",
            bool(linestring_only),
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

    # 3. Coordinates fall inside the NYC lon/lat envelope. This is the
    #    canonical catch for "stamped CRS as 4326 without actually
    #    reprojecting" — Web Mercator metres for NYC sit at ~ -8.2e6 / 4.97e6,
    #    nowhere near a -74 / 40 lon/lat box.
    xmin, ymin, xmax, ymax = sub.total_bounds
    in_nyc_envelope = (
        NYC_LON_MIN <= xmin <= NYC_LON_MAX
        and NYC_LON_MIN <= xmax <= NYC_LON_MAX
        and NYC_LAT_MIN <= ymin <= NYC_LAT_MAX
        and NYC_LAT_MIN <= ymax <= NYC_LAT_MAX
    )
    report.subchecks.append(
        Subcheck(
            "coordinates_within_nyc_lonlat_envelope",
            bool(in_nyc_envelope),
            detail=(
                f"bbox=({xmin:.4f}, {ymin:.4f}, {xmax:.4f}, {ymax:.4f}); "
                f"expected lon∈[{NYC_LON_MIN}, {NYC_LON_MAX}], "
                f"lat∈[{NYC_LAT_MIN}, {NYC_LAT_MAX}]"
            ),
            weight=4.0,
        )
    )

    # 4. Geometric IoU on the dissolved (line-buffered) network. Lines have
    #    zero IoU naturally, so we buffer both sides by ~1e-5° (≈ 1 m at this
    #    latitude) before comparing — that converts the network into a thin
    #    polygonal corridor and makes IoU meaningful. A correct reprojection
    #    drops the SUT's bounds within microns of the reference, well above
    #    the 0.9 floor.
    iou = iou_with_tolerance(sub, ref, eps=1e-5)
    report.subchecks.append(
        Subcheck(
            "geometry_iou_high",
            bool(iou >= 0.9),
            detail=f"IoU {iou:.6f} (eps=1e-5°)",
            weight=4.0,
        )
    )

    # 5. Per-feature length match. Computes geodesic-equivalent length on a
    #    spherical-Mercator-corrected projection (EPSG:3857 metres divided by
    #    cos(lat) is approximately right at this latitude — but we sidestep
    #    that by computing length in the *reference's projected metres*,
    #    after reprojecting both sub and ref into 3857). A correct SUT
    #    produces lengths that round-trip back to the input lengths to ppm.
    sub_3857 = sub.to_crs("EPSG:3857")
    ref_3857 = ref.to_crs("EPSG:3857")
    sub_lengths = (
        sub_3857.assign(_len_m=sub_3857.geometry.length)
        .loc[:, ["id", "_len_m"]]
    )
    ref_lengths = (
        ref_3857.assign(_len_m=ref_3857.geometry.length)
        .loc[:, ["id", "_len_m"]]
    )
    length_match = attribute_match(
        sub_lengths,
        ref_lengths,
        fields=["_len_m"],
        key="id",
        tolerance=0.01,
    )
    length_match_rate = length_match["_len_m"]
    report.subchecks.append(
        Subcheck(
            "per_feature_length_matches",
            bool(length_match_rate >= 0.95),
            detail=f"per-id length match rate {length_match_rate:.4f}",
            weight=3.0,
        )
    )

    # 6. Total network length within 1 % of reference. Catches systematic
    #    scale errors (e.g., the SUT lost a factor in the projection).
    sub_total_m = float(sub_3857.geometry.length.sum())
    ref_total_m = float(ref_3857.geometry.length.sum())
    total_pct_diff = abs(sub_total_m - ref_total_m) / max(ref_total_m, 1e-9)
    report.subchecks.append(
        Subcheck(
            "total_network_length_within_1_percent",
            bool(total_pct_diff <= 0.01),
            detail=(
                f"sub total {sub_total_m:.1f} m; "
                f"ref total {ref_total_m:.1f} m; rel diff {total_pct_diff:.4%}"
            ),
            weight=3.0,
        )
    )

    # 7. Identifying attributes preserved (class + name). Reprojection
    #    must not touch attributes; this catches accidental drop / rename /
    #    blanking and also the "I forgot to carry the metadata" failure mode.
    attr_match = attribute_match(
        sub.drop(columns="geometry"),
        ref.drop(columns="geometry"),
        fields=["class", "name"],
        key="id",
    )
    attrs_preserved = (
        attr_match["class"] >= 0.95 and attr_match["name"] >= 0.95
    )
    report.subchecks.append(
        Subcheck(
            "identifying_attributes_preserved",
            bool(attrs_preserved),
            detail=(
                f"class match {attr_match['class']:.4f}; "
                f"name match {attr_match['name']:.4f}"
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
            weight=0.5,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
