"""Grader for geo-l1-capetown-building-centroids.

The persona's question is "give me a centroid Point per building
footprint, with the original building IDs preserved as `building_id`,
in WGS84 GeoJSON".

Hard gate (`format_schema_valid`) — file exists, parses as GeoJSON,
has the required `building_id` column, and declares *some* usable CRS
(or is RFC 7946 implicit WGS84). A submission with no declarable CRS
is unrecoverable.

Subchecks:
  1. `building_id` populated (non-empty) for every row.
  2. `building_id` set Jaccard vs reference ≥ 0.95.
  3. Per-building centroid distance ≤ 1.0 m for ≥ 99% of common IDs.
  4. Median per-building centroid distance ≤ 0.05 m.
  5. All centroids fall inside the input bbox.
  6. Geometry types are Point only.
  7. Row count within ±5% of reference.
  8. `crs_is_canonical` — original declared CRS is EPSG:4326.
  9. `crs_in_meaningful_set` — original declared CRS is in
     {EPSG:4326, EPSG:32734}.
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
    feature_set_equality_by_id,
    grade_crs_soft,
)

TASK_DIR = Path(__file__).resolve().parent
INPUT = TASK_DIR / "inputs" / "capetown_buildings.shp"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "building_centroids.geojson"
OUTPUT_NAME = "building_centroids.geojson"

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326, 32734}

def _read_gdf_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="geo-l1-capetown-building-centroids")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format / schema validity ------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    sub = _read_gdf_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GeoJSON")
        )
        return report

    if "building_id" not in sub.columns:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "missing required column: building_id",
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
    ref_gdf = gpd.read_file(REFERENCE_OUT)
    n_sub = len(sub)
    n_ref = len(ref_gdf)

    sub["building_id"] = sub["building_id"].fillna("").astype(str)

    # 1. building_id populated.
    bid_pop = int((sub["building_id"].str.len() > 0).sum())
    report.subchecks.append(
        Subcheck(
            "building_id_populated",
            bid_pop == len(sub),
            detail=f"{bid_pop}/{len(sub)} rows have non-empty building_id",
        )
    )

    # 2. building_id set Jaccard.
    id_jaccard = feature_set_equality_by_id(sub, ref_gdf, key="building_id")
    report.subchecks.append(
        Subcheck(
            "building_id_set_preserved",
            id_jaccard >= 0.95,
            detail=f"building_id Jaccard {id_jaccard:.4f}",
            weight=3.0,
        )
    )

    # 3 & 4. Per-building centroid distance vs reference, computed in a
    # local metric CRS (UTM 34S) for sub-metre precision. We re-project
    # both sides to EPSG:32734 so the Euclidean distance is in metres.
    sub_m = sub.to_crs("EPSG:32734")
    ref_m = ref_gdf.to_crs("EPSG:32734")
    sub_by = sub_m.drop_duplicates("building_id", keep="first").set_index(
        "building_id"
    )
    ref_by = ref_m.drop_duplicates("building_id", keep="first").set_index(
        "building_id"
    )
    common_ids = sorted(set(sub_by.index) & set(ref_by.index))
    if common_ids:
        distances = [
            sub_by.loc[bid, "geometry"].distance(ref_by.loc[bid, "geometry"])
            for bid in common_ids
        ]
        within_1m = sum(1 for d in distances if d <= 1.0)
        within_rate = within_1m / len(distances)
        sorted_d = sorted(distances)
        median_d = sorted_d[len(sorted_d) // 2]
    else:
        within_1m, within_rate, median_d = 0, 0.0, float("inf")
        distances = []

    report.subchecks.append(
        Subcheck(
            "centroid_within_1m",
            within_rate >= 0.99,
            detail=(
                f"{within_1m}/{len(common_ids)} centroids within 1.0 m of reference"
            ),
            weight=4.0,
        )
    )
    report.subchecks.append(
        Subcheck(
            "centroid_median_distance_tight",
            median_d <= 0.05,
            detail=f"median centroid distance {median_d:.4f} m (≤ 0.05 m required)",
            weight=4.0,
        )
    )

    # 5. Each centroid covered by its own building footprint's
    # axis-aligned bbox (envelope). Every planar centroid of a polygon
    # lies inside the polygon's bbox by definition; this catches an
    # agent that produced a Point per building but paired the wrong
    # geometry to the wrong id (or output projected metres mistakenly
    # tagged as EPSG:4326).
    inp = gpd.read_file(INPUT)
    if "building_i" in inp.columns and "building_id" not in inp.columns:
        inp = inp.rename(columns={"building_i": "building_id"})
    inp_4326 = inp.to_crs("EPSG:4326")
    inp_by = inp_4326.drop_duplicates("building_id", keep="first").set_index(
        "building_id"
    )
    contained = 0
    common_for_bbox = [bid for bid in sub["building_id"] if bid in inp_by.index]
    sub_by_id = sub.drop_duplicates("building_id", keep="first").set_index(
        "building_id"
    )
    for bid in common_for_bbox:
        pt = sub_by_id.loc[bid, "geometry"]
        poly = inp_by.loc[bid, "geometry"]
        if pt is None or poly is None:
            continue
        minx, miny, maxx, maxy = poly.bounds
        if minx <= pt.x <= maxx and miny <= pt.y <= maxy:
            contained += 1
    contain_rate = contained / len(common_for_bbox) if common_for_bbox else 0.0
    report.subchecks.append(
        Subcheck(
            "centroid_inside_own_footprint_bbox",
            contain_rate >= 0.99,
            detail=(
                f"{contained}/{len(common_for_bbox)} centroids fall inside "
                "their building's footprint bbox"
            ),
            weight=3.0,
        )
    )

    # Geometry types are Point only.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    report.subchecks.append(
        Subcheck(
            "geometry_types_point",
            geom_types == {"Point"},
            detail=f"geometry types: {sorted(geom_types)} (expected Point only)",
        )
    )

    # Row count within ±5 % of reference.
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
