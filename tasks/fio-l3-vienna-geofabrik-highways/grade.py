"""Grader — fio-l3-vienna-geofabrik-highways

Compares a submission's vienna_network.gpkg against the reference output.
L3 task: tolerances are wider to absorb OSM upstream drift.

Single hard gate (`format_schema_valid`): the GPKG exists, exposes the
`highways` and `pt_routes` layers, those layers read, each declares
some usable CRS, and each carries its required columns. Anything
recoverable (geometry-type uniformity, minimum feature counts,
canonical-vs-meaningful CRS) is graded as a subcheck so partial work
keeps partial credit. Each layer is reprojected to canonical
EPSG:31287 before the spatial subchecks run.
"""

from pathlib import Path

import geopandas as gpd
import pyogrio

from geo_grading import Gate, ScoreReport, Subcheck, grade_crs_soft
from geo_grading.comparisons import count_within_tolerance

TASK_DIR = Path(__file__).resolve().parent
REF_DIR = TASK_DIR / "reference" / "solution" / "outputs"

REQUIRED_HW_COLS = {"name", "highway", "maxspeed", "lanes", "surface", "oneway"}
REQUIRED_PT_COLS = {"ref", "name", "operator", "route"}

# L3 tolerances — OSM data drifts between runs
COUNT_TOL = 0.15  # ±15 % feature count
ATTR_PRESENT_THRESHOLD = 0.70  # ≥70 % of rows have non-empty values

CANONICAL_EPSG = 31287
MEANINGFUL_EPSGS = {31287}

# Expected coordinate envelope for EPSG:31287 around the Gürtel area
# (MGI / Austria Lambert — easting ~610 k – 640 k, northing ~470 k – 500 k)
EASTING_RANGE = (600_000, 660_000)
NORTHING_RANGE = (460_000, 510_000)


def _read_layer(path: Path, layer: str) -> gpd.GeoDataFrame | None:
    """Safely read a layer; return None on any error."""
    try:
        return gpd.read_file(path, layer=layer)
    except Exception:
        return None


def _coords_in_range(gdf: gpd.GeoDataFrame) -> bool:
    """Check the coordinate envelope falls in the expected EPSG:31287 range."""
    bounds = gdf.total_bounds  # minx miny maxx maxy
    return bool(
        EASTING_RANGE[0] <= bounds[0] <= EASTING_RANGE[1]
        and EASTING_RANGE[0] <= bounds[2] <= EASTING_RANGE[1]
        and NORTHING_RANGE[0] <= bounds[1] <= NORTHING_RANGE[1]
        and NORTHING_RANGE[0] <= bounds[3] <= NORTHING_RANGE[1]
    )


def _attr_fill_rate(gdf: gpd.GeoDataFrame, col: str) -> float:
    """Fraction of rows where `col` is non-empty and non-null."""
    if col not in gdf.columns:
        return 0.0
    series = gdf[col].fillna("")
    return float((series.astype(str).str.strip() != "").mean())


def _has_diacritics(gdf: gpd.GeoDataFrame, col: str, pattern: str = "ürtel") -> bool:
    """Check that at least one value in `col` contains the pattern (German umlaut test)."""
    if col not in gdf.columns:
        return False
    return bool(gdf[col].fillna("").str.contains(pattern, na=False).any())


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="fio-l3-vienna-geofabrik-highways")
    sub_path = submission_dir / "vienna_network.gpkg"

    # ── Gate: Format / schema validity ─────────────────────────────────

    if not sub_path.exists():
        report.gates.append(Gate("format_schema_valid", False, "vienna_network.gpkg not found"))
        return report

    try:
        layers = {row[0] for row in pyogrio.list_layers(sub_path)}
    except Exception as exc:
        report.gates.append(Gate("format_schema_valid", False, f"cannot read GPKG: {exc}"))
        return report

    missing_layers = {"highways", "pt_routes"} - layers
    if missing_layers:
        report.gates.append(
            Gate("format_schema_valid", False, f"missing layers: {missing_layers}")
        )
        return report

    hw_sub = _read_layer(sub_path, "highways")
    pt_sub = _read_layer(sub_path, "pt_routes")

    if hw_sub is None or pt_sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "failed to read one or both layers")
        )
        return report

    # Check required columns
    hw_missing = REQUIRED_HW_COLS - set(hw_sub.columns)
    pt_missing = REQUIRED_PT_COLS - set(pt_sub.columns)
    if hw_missing or pt_missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing columns — highways: {hw_missing or 'ok'}, pt_routes: {pt_missing or 'ok'}",
            )
        )
        return report

    # CRS soft-grade. The gate fails only if either layer has no
    # usable CRS at all (the grader cannot reproject; geometric
    # subchecks become undefined). Otherwise both layers are
    # reprojected to canonical EPSG:31287 so downstream coordinate-range
    # / geometry subchecks work regardless of the agent's pick. The
    # CRS pick itself is graded by the two appended subchecks at the
    # end of this method.
    hw_crs_res = grade_crs_soft(
        hw_sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=False
    )
    pt_crs_res = grade_crs_soft(
        pt_sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=False
    )
    if not (hw_crs_res.gate_ok and pt_crs_res.gate_ok):
        reasons = []
        if not hw_crs_res.gate_ok:
            reasons.append(f"highways: {hw_crs_res.gate_reason}")
        if not pt_crs_res.gate_ok:
            reasons.append(f"pt_routes: {pt_crs_res.gate_reason}")
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(reasons))
        )
        return report

    hw_sub = hw_crs_res.normalized
    pt_sub = pt_crs_res.normalized

    report.gates.append(Gate("format_schema_valid", True))

    # ── Load reference ─────────────────────────────────────────────────

    ref_path = REF_DIR / "vienna_network.gpkg"
    hw_ref = gpd.read_file(ref_path, layer="highways")
    pt_ref = gpd.read_file(ref_path, layer="pt_routes")

    # ── Subchecks ──────────────────────────────────────────────────────

    # Geometry-type uniformity for each layer.
    hw_geom_types = set(hw_sub.geom_type.unique())
    hw_geom_ok = hw_geom_types.issubset({"LineString", "MultiLineString"})
    report.subchecks.append(
        Subcheck(
            "hw_geometry_type",
            hw_geom_ok,
            f"highways geometry types: {sorted(hw_geom_types)}",
        )
    )
    pt_geom_types = set(pt_sub.geom_type.unique())
    pt_geom_ok = pt_geom_types.issubset({"MultiLineString", "LineString"})
    report.subchecks.append(
        Subcheck(
            "pt_geometry_type",
            pt_geom_ok,
            f"pt_routes geometry types: {sorted(pt_geom_types)}",
        )
    )

    # Minimum feature counts — guards against an empty-frame submission.
    feature_count_ok = bool(len(hw_sub) >= 100 and len(pt_sub) >= 5)
    report.subchecks.append(
        Subcheck(
            "minimum_feature_counts",
            feature_count_ok,
            f"highways: {len(hw_sub)} (≥100), pt_routes: {len(pt_sub)} (≥5)",
        )
    )

    # 1. Highway count within tolerance
    hw_count_ok = count_within_tolerance(len(hw_ref), len(hw_sub), pct=COUNT_TOL)
    report.subchecks.append(
        Subcheck(
            "highway_count",
            hw_count_ok,
            f"ref={len(hw_ref)}, sub={len(hw_sub)}, tol={COUNT_TOL}",
            weight=3.0,
        )
    )

    # 2. PT route count within tolerance
    pt_count_ok = count_within_tolerance(len(pt_ref), len(pt_sub), pct=COUNT_TOL)
    report.subchecks.append(
        Subcheck(
            "pt_route_count",
            pt_count_ok,
            f"ref={len(pt_ref)}, sub={len(pt_sub)}, tol={COUNT_TOL}",
            weight=3.0,
        )
    )

    # 3. Coordinate envelope in expected EPSG:31287 range.
    #    A wrong envelope is a central failure: it means the agent buffered
    #    in degrees / filtered against the wrong extent, or never reprojected.
    #    Weighted alongside the count checks as a primary spatial-extent detector.
    hw_coords_ok = _coords_in_range(hw_sub)
    report.subchecks.append(
        Subcheck(
            "highway_coords_range",
            hw_coords_ok,
            f"bounds={hw_sub.total_bounds}",
            weight=3.0,
        )
    )

    # 4. PT route coordinates are projected (not in degrees)
    #    PT routes span far beyond the Gürtel — whole bus lines cross Vienna
    #    and beyond.  Just confirm coordinates are not in geographic degrees.
    pt_bounds = pt_sub.total_bounds
    pt_not_degrees = bool(abs(pt_bounds[0]) > 360 or abs(pt_bounds[2]) > 360)
    report.subchecks.append(
        Subcheck(
            "pt_route_projected",
            pt_not_degrees,
            f"bounds={pt_bounds} (checking coords are not in degrees)",
            weight=2.0,
        )
    )

    # 5. Highway 'highway' attribute populated (≥70 % non-empty)
    hw_highway_fill = _attr_fill_rate(hw_sub, "highway")
    report.subchecks.append(
        Subcheck(
            "hw_highway_attr_populated",
            bool(hw_highway_fill >= ATTR_PRESENT_THRESHOLD),
            f"fill_rate={hw_highway_fill:.2f}",
        )
    )

    # 6. Highway 'name' attribute has diacritics preserved (German Gürtel names)
    diacritics_ok = _has_diacritics(hw_sub, "name")
    report.subchecks.append(
        Subcheck(
            "diacritics_preserved",
            diacritics_ok,
            "checked for 'ürtel' pattern in highway name column",
        )
    )

    # 7. PT route 'route' attribute populated
    pt_route_fill = _attr_fill_rate(pt_sub, "route")
    report.subchecks.append(
        Subcheck(
            "pt_route_attr_populated",
            bool(pt_route_fill >= ATTR_PRESENT_THRESHOLD),
            f"fill_rate={pt_route_fill:.2f}",
        )
    )

    # 8. PT route type distribution — should include bus and tram at minimum.
    #    A near-trivial diversity floor: any unfiltered or over-broad
    #    extraction passes it easily, so it does not detect the central
    #    spatial-extent failure. Kept at default weight (structural).
    pt_route_types = set(pt_sub["route"].dropna().unique())
    has_bus_tram = {"bus", "tram"}.issubset(pt_route_types)
    report.subchecks.append(
        Subcheck(
            "pt_route_type_diversity",
            has_bus_tram,
            f"route types present: {pt_route_types}",
        )
    )

    # 9. Highway type distribution — should include residential and primary/secondary.
    #    Like pt_route_type_diversity, this is a near-trivial floor that any
    #    over-broad extraction passes; it does not discriminate the central
    #    spatial-extent failure, so it stays at default weight (structural).
    hw_types = set(hw_sub["highway"].dropna().unique())
    has_major_types = bool(hw_types & {"primary", "secondary", "tertiary"}) and bool(
        hw_types & {"residential", "living_street"}
    )
    report.subchecks.append(
        Subcheck(
            "hw_type_diversity",
            has_major_types,
            f"highway types present: {hw_types}",
        )
    )

    # 10. PT routes are MultiLineString (one feature per relation, not split)
    pt_multi_frac = (pt_sub.geom_type == "MultiLineString").mean()
    report.subchecks.append(
        Subcheck(
            "pt_multilinestring",
            bool(pt_multi_frac >= 0.90),
            f"MultiLineString fraction={pt_multi_frac:.2f}",
        )
    )

    # 11 / 12. CRS pick across the two layers. Both layers must agree
    # with canonical / meaningful for the subcheck to pass.
    canonical_ok = bool(hw_crs_res.is_canonical and pt_crs_res.is_canonical)
    meaningful_ok = bool(
        hw_crs_res.in_meaningful_set and pt_crs_res.in_meaningful_set
    )
    layer_crs_summary = (
        f"highways=EPSG:{hw_crs_res.original_epsg}, "
        f"pt_routes=EPSG:{pt_crs_res.original_epsg}"
    )
    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            canonical_ok,
            f"layer CRS picks: {layer_crs_summary}; canonical EPSG:{CANONICAL_EPSG}",
        )
    )
    report.subchecks.append(
        Subcheck(
            "crs_in_meaningful_set",
            meaningful_ok,
            (
                f"layer CRS picks: {layer_crs_summary}; "
                f"meaningful set {sorted(MEANINGFUL_EPSGS)}"
            ),
        )
    )

    return report


if __name__ == "__main__":
    import json
    import sys

    import numpy as np

    class _Encoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, (np.bool_, np.integer)):
                return int(o)
            if isinstance(o, np.floating):
                return float(o)
            if isinstance(o, np.ndarray):
                return o.tolist()
            return super().default(o)

    sub_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REF_DIR
    result = grade(sub_dir)
    print(json.dumps(result.to_dict(), indent=2, cls=_Encoder))
