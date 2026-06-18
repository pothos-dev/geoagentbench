"""Grader for crs-l3-tokyo-jgd-crossings.

Live-data L3 task. The reference fetches Tokyo's 23 special wards and
the drivable highway network from Overpass and runs the full
reproject -> crossings -> buffer -> intersect -> density -> reproject
pipeline. Two consecutive reference runs may differ by a few features
because OSM updates minute-by-minute, so tolerances are intentionally
wide on counts and ranking-based on density. Geometric checks
(reprojection sanity, buffer planar area) are *principled* -- they
catch the failure mode regardless of upstream drift.

One hard gate (``format_schema_valid``): the multi-layer GPKG exists
and has the five expected layer names readable.

Subchecks span:
  - ward count is exactly 23 (the persona's whole framing assumes the
    23 special wards),
  - per-layer CRS metadata correctness,
  - principled-bound coordinate-envelope checks (catches "stamped CRS
    metadata but did not actually reproject"),
  - count tolerances against the reference (+-15%),
  - the buffer mean planar area approximates pi*50^2 m^2 (catches
    "buffered in degrees" / "buffered before reprojecting"),
  - per-ward density rank correlation against the reference (catches
    coarse ordering errors regardless of drift),
  - top-N densest wards membership.
"""
from __future__ import annotations

import json
import sys
import math
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import CRS

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    count_within_tolerance,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "tokyo_crossings.gpkg"
OUTPUT_NAME = "tokyo_crossings.gpkg"

LAYERS = {
    "wards_jgd": ("Polygon", "EPSG:6677"),
    "crossing_points": ("Point", "EPSG:6677"),
    "crossing_buffers_50m": ("Polygon", "EPSG:6677"),
    "buffer_ward_intersection": ("Polygon", "EPSG:6677"),
    "ward_crossing_density_wgs84": ("Polygon", "EPSG:4326"),
}

# JGD2011 Plane IX envelope for Tokyo's 23 special wards. Coordinates
# from the reference run: x in [-24500, +7800], y in [-57600, -20200].
# We add slack to absorb drift and slightly different ward boundary
# stitching across OSM versions.
JGD_X_MIN, JGD_X_MAX = -40_000, 20_000
JGD_Y_MIN, JGD_Y_MAX = -70_000, -10_000

# WGS84 envelope for the same 23 wards.
WGS_LON_MIN, WGS_LON_MAX = 139.4, 140.0
WGS_LAT_MIN, WGS_LAT_MAX = 35.4, 35.9

# 50 m planar buffer mean area: pi * 50^2 = 7853.98 m^2. Shapely's
# default 16-segment quad approximation undersells the true circle by
# ~0.4%. Allow a generous +-25% band so tasks with slightly different
# resolution settings still pass; failures here mean "buffered in
# degrees", "buffered without reprojecting", or "wrong radius".
BUFFER_AREA_TARGET = math.pi * 50.0 * 50.0  # ~7854 m^2
BUFFER_AREA_MIN = 0.7 * BUFFER_AREA_TARGET
BUFFER_AREA_MAX = 1.3 * BUFFER_AREA_TARGET

# Drift-tolerant count windows.
COUNT_TOLERANCE = 0.15

# Density rank-correlation floor.
DENSITY_RANK_CORR_MIN = 0.80


def _crs_matches(crs_obj, target_epsg: str) -> bool:
    if crs_obj is None:
        return False
    try:
        target = CRS.from_user_input(target_epsg)
        actual = CRS.from_user_input(crs_obj)
        # Compare authority codes when possible.
        if actual.to_epsg() is not None and target.to_epsg() is not None:
            return actual.to_epsg() == target.to_epsg()
        return actual.equals(target)
    except Exception:
        return False


def _spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation, returning 0.0 on degenerate inputs."""
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(a.rank().corr(b.rank()))


def _read_layer(path: Path, layer: str) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path, layer=layer)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="crs-l3-tokyo-jgd-crossings")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format / schema validity ------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output: {OUTPUT_NAME}")
        )
        return report

    try:
        from pyogrio import list_layers
        present_layers_arr = list_layers(submission_path)
        present_layers = {row[0] for row in present_layers_arr}
    except Exception as e:
        report.gates.append(
            Gate("format_schema_valid", False, f"could not open GPKG: {e}")
        )
        return report

    missing_layers = [name for name in LAYERS if name not in present_layers]
    if missing_layers:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing layer(s): {missing_layers}",
            )
        )
        return report

    # Read every layer; if any fails to read, gate 1 fails.
    submission_layers: dict[str, gpd.GeoDataFrame] = {}
    for name in LAYERS:
        gdf = _read_layer(submission_path, name)
        if gdf is None:
            report.gates.append(
                Gate("format_schema_valid", False, f"could not read layer {name}")
            )
            return report
        submission_layers[name] = gdf

    report.gates.append(Gate("format_schema_valid", True))

    wards = submission_layers["wards_jgd"]

    # ---- Reference layers ----------------------------------------------
    ref_layers = {name: _read_layer(REFERENCE_OUT, name) for name in LAYERS}

    # ---- Subcheck: ward count is exactly 23 ----------------------------
    report.subchecks.append(
        Subcheck(
            "wards_jgd_row_count_is_23",
            bool(len(wards) == 23),
            detail=f"wards_jgd has {len(wards)} rows; expected exactly 23",
        )
    )

    # ---- Subchecks: per-layer CRS metadata -----------------------------
    # These only verify the *declared* CRS label, not that coordinates
    # were actually transformed. A file can stamp EPSG:6677 metadata and
    # still hold lon/lat values. They are therefore weighted low (0.25
    # each): a metadata declaration must never out-leverage the
    # coordinate-envelope / planar-area checks that prove the
    # reprojection truly happened.
    for name, (_geom_type, target_epsg) in LAYERS.items():
        sub = submission_layers[name]
        ok = _crs_matches(sub.crs, target_epsg)
        report.subchecks.append(
            Subcheck(
                f"crs_match_{name}",
                bool(ok),
                detail=f"layer {name} crs={sub.crs}; expected {target_epsg}",
                weight=0.25,
            )
        )

    # ---- Subcheck: wards layer in JGD coordinate envelope --------------
    bx = wards.total_bounds  # minx, miny, maxx, maxy
    wards_in_envelope = (
        JGD_X_MIN <= bx[0] <= JGD_X_MAX
        and JGD_X_MIN <= bx[2] <= JGD_X_MAX
        and JGD_Y_MIN <= bx[1] <= JGD_Y_MAX
        and JGD_Y_MIN <= bx[3] <= JGD_Y_MAX
    )
    report.subchecks.append(
        Subcheck(
            "wards_jgd_in_plane_ix_envelope",
            bool(wards_in_envelope),
            detail=f"bounds={bx.tolist()}; expected x in [{JGD_X_MIN},{JGD_X_MAX}], y in [{JGD_Y_MIN},{JGD_Y_MAX}]",
            weight=3.0,
        )
    )

    # ---- Subcheck: density layer in WGS84 envelope ---------------------
    density = submission_layers["ward_crossing_density_wgs84"]
    db = density.total_bounds
    density_in_envelope = (
        WGS_LON_MIN <= db[0] <= WGS_LON_MAX
        and WGS_LON_MIN <= db[2] <= WGS_LON_MAX
        and WGS_LAT_MIN <= db[1] <= WGS_LAT_MAX
        and WGS_LAT_MIN <= db[3] <= WGS_LAT_MAX
    )
    report.subchecks.append(
        Subcheck(
            "density_layer_in_wgs84_envelope",
            bool(density_in_envelope),
            detail=f"bounds={db.tolist()}; expected lon in [{WGS_LON_MIN},{WGS_LON_MAX}], lat in [{WGS_LAT_MIN},{WGS_LAT_MAX}]",
            weight=2.0,
        )
    )

    # ---- Subcheck: crossing count within +-15% of reference ------------
    crossings = submission_layers["crossing_points"]
    ref_crossings = ref_layers["crossing_points"]
    crossings_count_ok = count_within_tolerance(
        crossings, ref_crossings, pct=COUNT_TOLERANCE
    )
    report.subchecks.append(
        Subcheck(
            "crossing_count_within_tolerance",
            bool(crossings_count_ok),
            detail=f"sub={len(crossings)} ref={len(ref_crossings)} tol={COUNT_TOLERANCE:.0%}",
            weight=3.0,
        )
    )

    # ---- Subcheck: buffer mean planar area ~ pi*50^2 -------------------
    buffers = submission_layers["crossing_buffers_50m"]
    if len(buffers) > 0 and _crs_matches(buffers.crs, "EPSG:6677"):
        # Compute area in the layer's own (projected) CRS.
        mean_area = float(buffers.geometry.area.mean())
    elif len(buffers) > 0:
        # Reproject to JGD plane IX before measuring -- catches "stamped
        # the wrong CRS metadata but the geometry is in lon/lat". If we
        # still get a degree-scale area the reprojection won't fix it.
        try:
            mean_area = float(buffers.to_crs("EPSG:6677").geometry.area.mean())
        except Exception:
            mean_area = -1.0
    else:
        mean_area = -1.0
    buffer_area_ok = BUFFER_AREA_MIN <= mean_area <= BUFFER_AREA_MAX
    report.subchecks.append(
        Subcheck(
            "buffer_mean_area_is_planar_50m",
            bool(buffer_area_ok),
            detail=(
                f"observed mean buffer area={mean_area:.2f} m^2; "
                f"expected ~{BUFFER_AREA_TARGET:.2f} (+-30%)"
            ),
            weight=3.0,
        )
    )

    # ---- Subcheck: buffer-ward-intersection mean area <= buffer area ---
    inter = submission_layers["buffer_ward_intersection"]
    if len(inter) > 0 and len(buffers) > 0:
        try:
            inter_area_crs = inter if _crs_matches(inter.crs, "EPSG:6677") else inter.to_crs("EPSG:6677")
            inter_mean = float(inter_area_crs.geometry.area.mean())
        except Exception:
            inter_mean = -1.0
        # The intersection should be at most the unclipped buffer area
        # and strictly smaller for any crossing not deep inside a ward
        # (most boundary crossings clip the disc into a half-disc).
        # We accept anything in (0, BUFFER_AREA_TARGET * 1.05].
        inter_area_ok = 0 < inter_mean <= BUFFER_AREA_TARGET * 1.05
    else:
        inter_area_ok = False
        inter_mean = 0.0
    report.subchecks.append(
        Subcheck(
            "intersection_mean_area_below_buffer",
            bool(inter_area_ok),
            detail=f"observed mean={inter_mean:.2f} m^2; ceiling={BUFFER_AREA_TARGET:.2f}",
            weight=2.0,
        )
    )

    # ---- Subcheck: density attributes present and positive -------------
    has_density_col = "crossings_per_km2" in density.columns
    has_count_col = "crossing_count" in density.columns
    if has_density_col:
        positive = (density["crossings_per_km2"] >= 0).all() and (
            density["crossings_per_km2"] > 0
        ).any()
    else:
        positive = False
    report.subchecks.append(
        Subcheck(
            "density_layer_has_crossings_per_km2",
            bool(has_density_col and has_count_col and positive),
            detail=(
                f"crossings_per_km2 column present={has_density_col}; "
                f"crossing_count column present={has_count_col}; "
                f"positive={positive}"
            ),
        )
    )

    # ---- Subcheck: per-ward density rank correlation -------------------
    ref_density = ref_layers["ward_crossing_density_wgs84"]
    rank_ok = False
    rank_detail = ""
    if has_density_col and "ward_id" in density.columns and "ward_id" in ref_density.columns:
        sub_d = density[["ward_id", "crossings_per_km2"]].copy()
        ref_d = ref_density[["ward_id", "crossings_per_km2"]].copy()
        sub_d["ward_id"] = sub_d["ward_id"].astype(str)
        ref_d["ward_id"] = ref_d["ward_id"].astype(str)
        merged = sub_d.merge(
            ref_d, on="ward_id", how="inner", suffixes=("_sub", "_ref")
        )
        corr = _spearman(merged["crossings_per_km2_sub"], merged["crossings_per_km2_ref"])
        rank_ok = corr >= DENSITY_RANK_CORR_MIN and len(merged) >= 20
        rank_detail = f"spearman={corr:.4f} on {len(merged)} matched wards (min {DENSITY_RANK_CORR_MIN})"
    else:
        rank_detail = "ward_id or crossings_per_km2 column missing; cannot compute rank"
    report.subchecks.append(
        Subcheck(
            "density_rank_correlation_with_reference",
            bool(rank_ok),
            detail=rank_detail,
            weight=3.0,
        )
    )

    # ---- Subcheck: top-5 densest wards Jaccard match -------------------
    if has_density_col and "ward_id" in density.columns:
        sub_top = (
            density.sort_values("crossings_per_km2", ascending=False)
            .head(5)["ward_id"].astype(str).tolist()
        )
        ref_top = (
            ref_density.sort_values("crossings_per_km2", ascending=False)
            .head(5)["ward_id"].astype(str).tolist()
        )
        top5_jaccard = jaccard_similarity_set(sub_top, ref_top)
        top5_ok = top5_jaccard >= 0.5  # 3-of-5 overlap is fine under drift
    else:
        top5_jaccard = 0.0
        top5_ok = False
    report.subchecks.append(
        Subcheck(
            "top5_densest_wards_match",
            bool(top5_ok),
            detail=f"top-5 Jaccard={top5_jaccard:.4f} (min 0.5)",
            weight=1.5,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
