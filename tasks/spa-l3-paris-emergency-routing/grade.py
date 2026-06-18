"""Grader for spa-l3-paris-emergency-routing.

Grades a submission GPKG with four layers:
  - incidents (Point)
  - closest_hospital (LineString)
  - distance_matrix (tabular)
  - isochrones_15min (MultiPolygon)

against the committed reference outputs.

Gate — file exists, parses as a GPKG with the four required layers,
       each layer carries the required columns, and every spatial
       layer declares *some* usable CRS. A layer with no declarable
       CRS or missing the columns the subchecks index by is
       unrecoverable. When the gate passes, every spatial layer is
       reprojected to EPSG:2154 (Lambert-93) so the comparisons below
       run regardless of which CRS the agent picked.

Subchecks cover incident/hospital counts, network distances, distance-
matrix rank ordering, isochrone count + IoU + area plausibility,
geometry types, coordinate-range sanity, and the
`crs_is_canonical` / `crs_in_meaningful_set` pair across all three
spatial layers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    count_within_tolerance,
    grade_crs_soft,
    iou_with_tolerance,
)

TASK_DIR = Path(__file__).resolve().parent
REF_DIR = TASK_DIR / "reference" / "solution" / "outputs"
GPKG_NAME = "emergency_routing.gpkg"

REQUIRED_LAYERS = ["incidents", "closest_hospital", "distance_matrix", "isochrones_15min"]
# Lambert-93 is the official IGN-mandated CRS for metropolitan France.
# UTM 31N is meaningful (an agent that picks it is reasoning generically
# rather than regionally) and is reprojected into Lambert-93 before any
# spatial subcheck runs.
CANONICAL_EPSG = 2154
MEANINGFUL_EPSGS = {2154, 32631}
CRS_EXPECTED = f"EPSG:{CANONICAL_EPSG}"

# Tolerances (L3 drift-tolerant)
COUNT_PCT = 0.15          # ±15% on feature counts (hospitals may drift)
DISTANCE_REL_TOL = 0.15   # ±15% on network distances
ISO_IOU_MIN = 0.50         # Minimum IoU for isochrone overlap (convex hull approximation varies)
HOSPITAL_JACCARD_MIN = 0.60  # Minimum Jaccard for hospital name overlap


def _read_layer(gpkg_path: Path, layer: str) -> gpd.GeoDataFrame | None:
    """Safely read a layer from a GPKG, return None on failure."""
    try:
        return gpd.read_file(gpkg_path, layer=layer)
    except Exception:
        return None


def _layer_exists(gpkg_path: Path, layer: str) -> bool:
    """Check if a layer exists in a GPKG."""
    try:
        layers = [row[0] for row in pyogrio.list_layers(gpkg_path)]
        return layer in layers
    except Exception:
        return False


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="spa-l3-paris-emergency-routing")

    sub_gpkg = submission_dir / GPKG_NAME
    ref_gpkg = REF_DIR / GPKG_NAME

    # ── Gate 1: format / schema validity ──
    gate1_ok = True
    gate1_reasons = []
    # Per-spatial-layer CrsGradeResult — populated when Gate 1 reaches the
    # CRS-soft step. Used by the crs_is_canonical / crs_in_meaningful_set
    # subchecks at the end.
    crs_results: dict[str, object] = {}
    sub_incidents = sub_closest = sub_matrix = sub_iso = None

    if not sub_gpkg.exists():
        gate1_ok = False
        gate1_reasons.append(f"{GPKG_NAME} not found")
    else:
        try:
            sub_layers = [row[0] for row in pyogrio.list_layers(sub_gpkg)]
        except Exception as e:
            gate1_ok = False
            gate1_reasons.append(f"Cannot read GPKG: {e}")
            sub_layers = []

        if gate1_ok:
            for layer in REQUIRED_LAYERS:
                if layer not in sub_layers:
                    gate1_ok = False
                    gate1_reasons.append(f"Missing layer: {layer}")

        if gate1_ok:
            # Read every layer, soft-grade CRS + reproject the spatial
            # ones. distance_matrix is tabular — distances are already
            # metres, so CRS doesn't matter and we skip the check for
            # that layer.
            sub_matrix = _read_layer(sub_gpkg, "distance_matrix")
            spatial_layer_map: dict[str, gpd.GeoDataFrame] = {}
            for layer in ["incidents", "closest_hospital", "isochrones_15min"]:
                gdf = _read_layer(sub_gpkg, layer)
                res = grade_crs_soft(gdf, MEANINGFUL_EPSGS, CANONICAL_EPSG)
                crs_results[layer] = res
                if not res.gate_ok:
                    gate1_ok = False
                    gate1_reasons.append(f"Layer {layer}: {res.gate_reason}")
                else:
                    spatial_layer_map[layer] = res.normalized
            sub_incidents = spatial_layer_map.get("incidents")
            sub_closest = spatial_layer_map.get("closest_hospital")
            sub_iso = spatial_layer_map.get("isochrones_15min")

        # Required columns: the subchecks index layers by these columns,
        # so absence is unrecoverable for grading and gates the run.
        if gate1_ok:
            required_cols = {
                "incidents": ["incident_id"],
                "closest_hospital": ["incident_id", "hospital_name", "network_distance_m"],
                "distance_matrix": ["incident_id", "hospital_name", "rank", "network_distance_m"],
                "isochrones_15min": ["hospital_name", "travel_time_min"],
            }
            layer_map = {
                "incidents": sub_incidents,
                "closest_hospital": sub_closest,
                "distance_matrix": sub_matrix,
                "isochrones_15min": sub_iso,
            }
            for layer, cols in required_cols.items():
                gdf = layer_map[layer]
                for col in cols:
                    if col not in gdf.columns:
                        gate1_ok = False
                        gate1_reasons.append(f"Layer {layer} missing column: {col}")

    report.gates.append(Gate("format_schema_valid", gate1_ok, "; ".join(gate1_reasons)))
    if not gate1_ok:
        return report

    ref_incidents = gpd.read_file(ref_gpkg, layer="incidents")
    ref_closest = gpd.read_file(ref_gpkg, layer="closest_hospital")
    ref_matrix = gpd.read_file(ref_gpkg, layer="distance_matrix")
    ref_iso = gpd.read_file(ref_gpkg, layer="isochrones_15min")

    # ── Subchecks ──

    # Geometry types per spatial layer.
    inc_types = set(sub_incidents.geometry.geom_type.unique())
    inc_geom_ok = inc_types.issubset({"Point", "MultiPoint"})
    cl_types = set(sub_closest.geometry.geom_type.unique())
    cl_geom_ok = cl_types.issubset({"LineString", "MultiLineString"})
    iso_types = set(sub_iso.geometry.geom_type.unique())
    iso_geom_ok = iso_types.issubset({"Polygon", "MultiPolygon"})
    report.subchecks.append(Subcheck(
        "geometry_types_per_layer",
        inc_geom_ok and cl_geom_ok and iso_geom_ok,
        (
            f"incidents={sorted(inc_types)}, closest_hospital={sorted(cl_types)}, "
            f"isochrones_15min={sorted(iso_types)}"
        ),
    ))

    # Minimum feature counts: incidents and isochrones each >= 3 rows.
    min_counts_ok = len(sub_incidents) >= 3 and len(sub_iso) >= 3
    report.subchecks.append(Subcheck(
        "min_feature_counts",
        min_counts_ok,
        f"incidents={len(sub_incidents)} (>=3), isochrones_15min={len(sub_iso)} (>=3)",
    ))

    # Coordinate range sanity: after reprojection to Lambert-93 the
    # incidents bbox should be in metres (≥10 000). Catches an agent who
    # mislabeled degree coords as a projected CRS.
    if len(sub_incidents) > 0:
        bounds = sub_incidents.total_bounds  # minx, miny, maxx, maxy
        coord_range_ok = bounds[0] >= 10_000 and bounds[2] >= 10_000
        coord_detail = f"incidents x-range {bounds[0]:.1f}-{bounds[2]:.1f} (expect ≥10 000 in Lambert-93 metres)"
    else:
        coord_range_ok = False
        coord_detail = "incidents layer empty"
    report.subchecks.append(Subcheck(
        "incident_coords_in_metres",
        coord_range_ok,
        coord_detail,
    ))

    # 1. Incident count
    inc_count_ok = count_within_tolerance(len(sub_incidents), len(ref_incidents), pct=COUNT_PCT)
    report.subchecks.append(Subcheck(
        "incident_count",
        inc_count_ok,
        f"sub={len(sub_incidents)}, ref={len(ref_incidents)}, tol={COUNT_PCT}",
        weight=2.0,
    ))

    # 2. Closest hospital count matches incidents
    closest_count_ok = count_within_tolerance(len(sub_closest), len(ref_closest), pct=COUNT_PCT)
    report.subchecks.append(Subcheck(
        "closest_hospital_count",
        closest_count_ok,
        f"sub={len(sub_closest)}, ref={len(ref_closest)}",
        weight=2.0,
    ))

    # 3. Hospital name overlap in closest_hospital layer
    if "hospital_name" in sub_closest.columns and "hospital_name" in ref_closest.columns:
        sub_names = set(sub_closest["hospital_name"].dropna().str.strip().str.lower())
        ref_names = set(ref_closest["hospital_name"].dropna().str.strip().str.lower())
        if ref_names:
            name_jaccard = len(sub_names & ref_names) / len(sub_names | ref_names) if (sub_names | ref_names) else 1.0
        else:
            name_jaccard = 1.0
        hosp_name_ok = name_jaccard >= HOSPITAL_JACCARD_MIN
    else:
        hosp_name_ok = False
        name_jaccard = 0.0
    report.subchecks.append(Subcheck(
        "closest_hospital_names",
        hosp_name_ok,
        f"Jaccard={name_jaccard:.2f}, min={HOSPITAL_JACCARD_MIN}",
        weight=3.0,
    ))

    # 4. Network distances in closest_hospital — compare matched incidents
    if "incident_id" in sub_closest.columns and "network_distance_m" in sub_closest.columns:
        ref_side = ref_closest[["incident_id", "network_distance_m"]].rename(columns={"network_distance_m": "ref_dist"})
        sub_side = sub_closest[["incident_id", "network_distance_m"]].rename(columns={"network_distance_m": "sub_dist"})
        ref_side["incident_id"] = ref_side["incident_id"].astype(str)
        sub_side["incident_id"] = sub_side["incident_id"].astype(str)
        merged = pd.merge(ref_side, sub_side, on="incident_id", how="inner")
        if len(merged) > 0:
            rel_err = ((merged["sub_dist"] - merged["ref_dist"]).abs() / merged["ref_dist"].clip(lower=1.0))
            dist_match_rate = (rel_err <= DISTANCE_REL_TOL).mean()
            dist_ok = dist_match_rate >= 0.5  # at least half within tolerance
        else:
            dist_ok = False
            dist_match_rate = 0.0
    else:
        dist_ok = False
        dist_match_rate = 0.0
    report.subchecks.append(Subcheck(
        "closest_hospital_distances",
        dist_ok,
        f"match_rate={dist_match_rate:.2f} (tol={DISTANCE_REL_TOL})",
        weight=4.0,
    ))

    # 5. Distance matrix row count
    expected_matrix_rows = len(ref_matrix)
    matrix_count_ok = count_within_tolerance(len(sub_matrix), expected_matrix_rows, pct=0.20)
    report.subchecks.append(Subcheck(
        "distance_matrix_count",
        matrix_count_ok,
        f"sub={len(sub_matrix)}, ref={expected_matrix_rows}",
        weight=2.0,
    ))

    # 6. Distance matrix rank correctness — for matched incidents, check rank ordering
    if "incident_id" in sub_matrix.columns and "rank" in sub_matrix.columns and "network_distance_m" in sub_matrix.columns:
        # Check that within each incident, distances are monotonically non-decreasing by rank
        rank_ok_count = 0
        total_incidents = 0
        for inc_id in sub_matrix["incident_id"].unique():
            inc_rows = sub_matrix[sub_matrix["incident_id"] == inc_id].sort_values("rank")
            if len(inc_rows) >= 2 and "network_distance_m" in inc_rows.columns:
                dists = inc_rows["network_distance_m"].values
                if all(dists[i] <= dists[i + 1] + 1.0 for i in range(len(dists) - 1)):
                    rank_ok_count += 1
            total_incidents += 1
        rank_ok = rank_ok_count >= total_incidents * 0.5 if total_incidents > 0 else False
    else:
        rank_ok = False
        rank_ok_count = 0
        total_incidents = 0
    report.subchecks.append(Subcheck(
        "distance_matrix_rank_order",
        rank_ok,
        f"{rank_ok_count}/{total_incidents} incidents have correct rank ordering",
        weight=3.0,
    ))

    # 7. Isochrone count
    iso_count_ok = count_within_tolerance(len(sub_iso), len(ref_iso), pct=COUNT_PCT)
    report.subchecks.append(Subcheck(
        "isochrone_count",
        iso_count_ok,
        f"sub={len(sub_iso)}, ref={len(ref_iso)}",
        weight=2.0,
    ))

    # 8. Isochrone hospital name overlap
    if "hospital_name" in sub_iso.columns and "hospital_name" in ref_iso.columns:
        sub_iso_names = set(sub_iso["hospital_name"].dropna().str.strip().str.lower())
        ref_iso_names = set(ref_iso["hospital_name"].dropna().str.strip().str.lower())
        iso_name_jaccard = (
            len(sub_iso_names & ref_iso_names) / len(sub_iso_names | ref_iso_names)
            if (sub_iso_names | ref_iso_names)
            else 1.0
        )
        iso_name_ok = iso_name_jaccard >= HOSPITAL_JACCARD_MIN
    else:
        iso_name_ok = False
        iso_name_jaccard = 0.0
    report.subchecks.append(Subcheck(
        "isochrone_hospital_names",
        iso_name_ok,
        f"Jaccard={iso_name_jaccard:.2f}, min={HOSPITAL_JACCARD_MIN}",
        weight=3.0,
    ))

    # 9. Isochrone spatial coverage IoU (union of all isochrones).
    # sub_iso was normalised to OFFICIAL_CRS_EPSG above; ref is committed in
    # the same CRS, so both sides are already in metres-from-Lambert-93.
    try:
        iou_val = iou_with_tolerance(sub_iso, ref_iso, eps=10.0)
        iou_ok = iou_val >= ISO_IOU_MIN
    except Exception:
        iou_val = 0.0
        iou_ok = False
    report.subchecks.append(Subcheck(
        "isochrone_coverage_iou",
        iou_ok,
        f"IoU={iou_val:.2f}, min={ISO_IOU_MIN}",
        weight=3.0,
    ))

    # 10. Isochrone areas plausible (each should be > 1 km² and < 100 km²)
    if len(sub_iso) > 0:
        areas_m2 = sub_iso.geometry.area
        areas_km2 = areas_m2 / 1e6
        plausible = ((areas_km2 > 1.0) & (areas_km2 < 100.0)).mean()
        area_ok = plausible >= 0.7
    else:
        area_ok = False
        plausible = 0.0
    report.subchecks.append(Subcheck(
        "isochrone_area_plausible",
        area_ok,
        f"{plausible:.0%} of isochrones have area between 1-100 km²",
    ))

    # 11/12. CRS subchecks — Lambert-93 is the IGN-mandated CRS for
    # metropolitan France; UTM 31N is defensible (and meaningful, with
    # the submission already reprojected into Lambert-93 for subchecks
    # 1-10) but does not reflect the regional convention a SAMU stack
    # would use. Both flags aggregate across the three spatial layers.
    spatial_layers = ["incidents", "closest_hospital", "isochrones_15min"]
    layer_epsgs = {
        layer: crs_results[layer].original_epsg for layer in spatial_layers
    }
    all_canonical = all(
        crs_results[layer].is_canonical for layer in spatial_layers
    )
    all_meaningful = all(
        crs_results[layer].in_meaningful_set for layer in spatial_layers
    )
    report.subchecks.append(Subcheck(
        "crs_is_canonical",
        all_canonical,
        f"per-layer original EPSGs {layer_epsgs}; canonical EPSG:{CANONICAL_EPSG}",
    ))
    report.subchecks.append(Subcheck(
        "crs_in_meaningful_set",
        all_meaningful,
        f"per-layer original EPSGs {layer_epsgs}; meaningful set {sorted(MEANINGFUL_EPSGS)}",
    ))

    return report


if __name__ == "__main__":
    submission = Path(sys.argv[1]) if len(sys.argv) > 1 else REF_DIR
    report = grade(submission)

    def _default(obj):
        if isinstance(obj, (np.bool_, np.integer)):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    print(json.dumps(report.to_dict(), indent=2, default=_default))
