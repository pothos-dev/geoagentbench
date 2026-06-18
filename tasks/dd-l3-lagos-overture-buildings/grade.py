"""Grader for dd-l3-lagos-overture-buildings.

One hard gate (``format_schema_valid``) plus a checklist of subchecks.

The hard gate covers cases where the output is unrecoverable for
grading: either parquet file missing, neither file readable, required
columns absent, or the building file has no usable CRS at all
(geopandas can't reproject to the canonical CRS without one).

Everything else — including zero-row submissions, unexpected geometry
types, and coordinates outside the Lagos WGS84 window — is scored as
subchecks so an agent that botches one dimension still earns credit
on the others.

Subchecks:
    building_count_tolerance    — feature count within ±10 % of ref.
    feature_set_jaccard         — Jaccard ≥ 0.80 on building ids.
    area_filter_applied         — ≥ 95 % of submitted buildings have
                                   footprint_area_m2 > 900 m² (allows
                                   minor float drift from reprojection
                                   differences).
    crs_wgs84_coords            — submitted building coords fall inside
                                   the Lagos State degree-window.
    summary_columns_types       — summary has correct columns and types.
    summary_lga_overlap         — ≥ 70 % of reference LGA names appear
                                   in the submission (tolerates minor
                                   name drift from Overture releases).
    summary_total_consistent    — sum(n_buildings) matches the building
                                   file count (±5 %).
    summary_area_reasonable     — total_footprint_m2 across all LGAs is
                                   within ±20 % of reference total.
    height_stats_present        — n_with_height and p50_height_m columns
                                   exist and have plausible values.
    crs_is_canonical            — buildings CRS is EPSG:4326.
    crs_in_meaningful_set       — buildings CRS is in {EPSG:4326}.
    buildings_non_empty         — buildings file has at least one row.
    geometry_types_valid        — every geometry is Polygon/MultiPolygon.
    bounds_in_lagos_window      — total bounds inside generous Lagos
                                   WGS84 window.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from geo_grading import Gate, ScoreReport, Subcheck
from geo_grading.comparisons import (
    count_within_tolerance,
    grade_crs_soft,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REF_BUILDINGS = TASK_DIR / "reference" / "solution" / "outputs" / "lagos_buildings.geoparquet"
REF_SUMMARY = TASK_DIR / "reference" / "solution" / "outputs" / "lagos_building_summary.parquet"

BUILDINGS_NAME = "lagos_buildings.geoparquet"
SUMMARY_NAME = "lagos_building_summary.parquet"

REQUIRED_BLDG_COLS = {"id", "height", "footprint_area_m2", "lga", "geometry"}
REQUIRED_SUMM_COLS = {
    "lga",
    "n_buildings",
    "total_footprint_m2",
    "n_with_height",
    "p50_height_m",
}

# Lagos WGS84 coordinate window (generous)
LAGOS_X = (2.5, 4.5)
LAGOS_Y = (6.0, 7.0)

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}


def _read_geoparquet_safe(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_parquet(path)
    except Exception:
        return None


def _read_parquet_safe(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_parquet(path)
    except Exception:
        return None




def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dd-l3-lagos-overture-buildings")

    bldg_path = submission_dir / BUILDINGS_NAME
    summ_path = submission_dir / SUMMARY_NAME

    # ------------------------------------------------------------------ #
    # Hard gate: format / schema valid                                    #
    # ------------------------------------------------------------------ #
    if not bldg_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing {BUILDINGS_NAME}")
        )
        return report

    if not summ_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing {SUMMARY_NAME}")
        )
        return report

    bldg = _read_geoparquet_safe(bldg_path)
    if bldg is None:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"{BUILDINGS_NAME} not readable as GeoParquet",
            )
        )
        return report

    summ = _read_parquet_safe(summ_path)
    if summ is None:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"{SUMMARY_NAME} not readable as Parquet",
            )
        )
        return report

    # Check building columns
    missing_bldg = REQUIRED_BLDG_COLS - set(bldg.columns)
    if missing_bldg:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"{BUILDINGS_NAME} missing columns: {missing_bldg}",
            )
        )
        return report

    # Check summary columns
    missing_summ = REQUIRED_SUMM_COLS - set(summ.columns)
    if missing_summ:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"{SUMMARY_NAME} missing columns: {missing_summ}",
            )
        )
        return report

    # Soft-grade building CRS — only hard-fail when the submission has
    # no usable CRS at all; the agent's actual choice is graded as two
    # subchecks below. GeoParquet always carries a CRS explicitly, so we
    # don't honour RFC 7946 implicit WGS84 here.
    crs_res = grade_crs_soft(bldg, MEANINGFUL_EPSGS, CANONICAL_EPSG)
    if not crs_res.gate_ok:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"{BUILDINGS_NAME}: {crs_res.gate_reason}",
            )
        )
        return report

    bldg = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ------------------------------------------------------------------ #
    # Subchecks                                                           #
    # ------------------------------------------------------------------ #
    ref_bldg = gpd.read_parquet(REF_BUILDINGS)
    ref_summ = pd.read_parquet(REF_SUMMARY)

    # 1. Building count tolerance (±10 % for L3)
    count_ok = count_within_tolerance(len(bldg), len(ref_bldg), pct=0.10)
    report.subchecks.append(
        Subcheck(
            "building_count_tolerance",
            count_ok,
            f"submitted {len(bldg)} vs reference {len(ref_bldg)} (±10 %)",
            weight=5.0,
        )
    )

    # 2. Feature-set Jaccard on building IDs
    sub_ids = set(bldg["id"].dropna())
    ref_ids = set(ref_bldg["id"].dropna())
    jac = jaccard_similarity_set(sub_ids, ref_ids)
    report.subchecks.append(
        Subcheck(
            "feature_set_jaccard",
            bool(jac >= 0.80),
            f"Jaccard over building ids = {jac:.4f} (need ≥ 0.80)",
            weight=5.0,
        )
    )

    # 3. Area filter applied: ≥ 95 % of buildings have area > 900 m²
    if "footprint_area_m2" in bldg.columns:
        area_vals = pd.to_numeric(bldg["footprint_area_m2"], errors="coerce")
        above_threshold = (area_vals > 900).sum()
        frac = above_threshold / max(len(bldg), 1)
        area_ok = bool(frac >= 0.95)
    else:
        frac = 0.0
        area_ok = False
    report.subchecks.append(
        Subcheck(
            "area_filter_applied",
            area_ok,
            f"{frac:.2%} of buildings have footprint > 900 m²",
            weight=5.0,
        )
    )

    # 4. CRS / coordinate sanity — verify against Lagos State's WGS84
    #    extent (roughly lon 2.71–4.35, lat 6.37–6.70) with a small
    #    margin.
    lagos_state_window = (2.5, 6.3, 4.5, 6.8)
    if len(bldg) > 0:
        tb = bldg.total_bounds
        coord_ok = bool(
            tb[0] >= lagos_state_window[0]
            and tb[1] >= lagos_state_window[1]
            and tb[2] <= lagos_state_window[2]
            and tb[3] <= lagos_state_window[3]
        )
        coord_detail = (
            f"bounds [{tb[0]:.2f},{tb[1]:.2f},{tb[2]:.2f},{tb[3]:.2f}] "
            f"vs Lagos State window {lagos_state_window}"
        )
    else:
        coord_ok = False
        coord_detail = "buildings file has zero features"
    report.subchecks.append(
        Subcheck("crs_wgs84_coords", coord_ok, coord_detail)
    )

    # 5. Summary columns and types
    summ_ok = True
    detail_parts = []
    for col in REQUIRED_SUMM_COLS:
        if col not in summ.columns:
            summ_ok = False
            detail_parts.append(f"missing {col}")
    if "n_buildings" in summ.columns and not pd.api.types.is_numeric_dtype(
        summ["n_buildings"]
    ):
        summ_ok = False
        detail_parts.append("n_buildings not numeric")
    report.subchecks.append(
        Subcheck(
            "summary_columns_types",
            summ_ok,
            "; ".join(detail_parts) if detail_parts else "all columns present and typed",
        )
    )

    # 6. Summary LGA name overlap (≥ 70 % of reference LGA names)
    ref_lgas = set(ref_summ["lga"].dropna().str.lower())
    sub_lgas = set(summ["lga"].dropna().str.lower()) if "lga" in summ.columns else set()
    if ref_lgas:
        lga_overlap = len(ref_lgas & sub_lgas) / len(ref_lgas)
    else:
        lga_overlap = 0.0
    report.subchecks.append(
        Subcheck(
            "summary_lga_overlap",
            bool(lga_overlap >= 0.70),
            f"{lga_overlap:.2%} of reference LGA names found in submission "
            f"(need ≥ 70 %)",
            weight=4.0,
        )
    )

    # 7. Summary total buildings consistent with building file (±5 %)
    if "n_buildings" in summ.columns:
        total_in_summary = int(summ["n_buildings"].sum())
        consist_ok = count_within_tolerance(total_in_summary, len(bldg), pct=0.05)
    else:
        total_in_summary = 0
        consist_ok = False
    report.subchecks.append(
        Subcheck(
            "summary_total_consistent",
            consist_ok,
            f"sum(n_buildings) = {total_in_summary} vs building file count "
            f"{len(bldg)} (±5 %)",
            weight=2.0,
        )
    )

    # 8. Summary total footprint area reasonable (±20 % of reference)
    if "total_footprint_m2" in summ.columns:
        sub_total_area = summ["total_footprint_m2"].sum()
        ref_total_area = ref_summ["total_footprint_m2"].sum()
        area_ratio = sub_total_area / max(ref_total_area, 1)
        area_reasonable = bool(0.80 <= area_ratio <= 1.20)
    else:
        sub_total_area = 0
        ref_total_area = 0
        area_ratio = 0
        area_reasonable = False
    report.subchecks.append(
        Subcheck(
            "summary_area_reasonable",
            area_reasonable,
            f"total footprint {sub_total_area:.0f} m² vs reference "
            f"{ref_total_area:.0f} m² (ratio {area_ratio:.2f}, need 0.80–1.20)",
            weight=4.0,
        )
    )

    # 9. Height stats present and plausible
    height_ok = True
    height_detail = []
    if "n_with_height" in summ.columns:
        total_h = summ["n_with_height"].sum()
        ref_total_h = ref_summ["n_with_height"].sum()
        if ref_total_h > 0 and total_h == 0:
            height_ok = False
            height_detail.append("n_with_height is all zeros but reference has non-zero")
    else:
        height_ok = False
        height_detail.append("n_with_height column missing")
    if "p50_height_m" not in summ.columns:
        height_ok = False
        height_detail.append("p50_height_m column missing")
    report.subchecks.append(
        Subcheck(
            "height_stats_present",
            height_ok,
            "; ".join(height_detail) if height_detail else "height stats present and plausible",
            weight=1.0,
        )
    )

    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            crs_res.is_canonical,
            f"original EPSG:{crs_res.original_epsg}; "
            f"canonical EPSG:{CANONICAL_EPSG}",
        )
    )
    report.subchecks.append(
        Subcheck(
            "crs_in_meaningful_set",
            crs_res.in_meaningful_set,
            f"original EPSG:{crs_res.original_epsg}; "
            f"meaningful set {sorted(MEANINGFUL_EPSGS)}",
        )
    )

    # 10. Buildings file non-empty (migrated from old Gate 2).
    report.subchecks.append(
        Subcheck(
            "buildings_non_empty",
            len(bldg) > 0,
            f"buildings file has {len(bldg)} rows",
        )
    )

    # 11. Geometry types valid (migrated from old Gate 2).
    valid_types = {"Polygon", "MultiPolygon"}
    if len(bldg) > 0:
        geom_types = set(bldg.geometry.geom_type.unique())
        bad_types = geom_types - valid_types
        geom_ok = not bad_types
        geom_detail = (
            f"present types {sorted(geom_types)}; "
            f"unexpected {sorted(bad_types)}"
        )
    else:
        geom_ok = False
        geom_detail = "no geometries to check (zero features)"
    report.subchecks.append(
        Subcheck("geometry_types_valid", geom_ok, geom_detail)
    )

    # 12. Total bounds within generous Lagos WGS84 window (migrated
    #     from old Gate 2). Distinct from `crs_wgs84_coords` which uses
    #     the tighter Lagos State window.
    if len(bldg) > 0:
        tb2 = bldg.total_bounds
        bounds_ok = bool(
            LAGOS_X[0] <= tb2[0]
            and tb2[2] <= LAGOS_X[1]
            and LAGOS_Y[0] <= tb2[1]
            and tb2[3] <= LAGOS_Y[1]
        )
        bounds_detail = (
            f"bounds [{tb2[0]:.2f},{tb2[1]:.2f},{tb2[2]:.2f},{tb2[3]:.2f}] "
            f"vs Lagos window x={LAGOS_X}, y={LAGOS_Y}"
        )
    else:
        bounds_ok = False
        bounds_detail = "no features to bound"
    report.subchecks.append(
        Subcheck("bounds_in_lagos_window", bounds_ok, bounds_detail)
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
