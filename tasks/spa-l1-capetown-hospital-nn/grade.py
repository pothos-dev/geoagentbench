"""Grader for spa-l1-capetown-hospital-nn.

The task gives WGS84 address and hospital points and asks for nearest-neighbour
assignment with distance in metres.  No output CRS is specified — the model
must independently choose a projected CRS for metric distance computation.

Gate — file exists, parses as GPKG, has required columns.  No CRS check.

Subchecks (weights chosen by error severity, total 13):
  1. Geometry types are Point only.                       (weight 1, structural)
  2. nearest_hospital_name populated (non-empty).          (weight 1, structural)
  3. distance_m is finite, non-negative, numeric.          (weight 1, structural)
  4. distance_m per address agrees with reference within 50 m for >= 95%
     of common addresses — catches degree-vs-metre and wrong-CRS errors.
     Tolerance is wider (50 m) than the original (1 m) to accept any
     reasonable projected CRS for the Cape Town region.    (weight 4, CENTRAL)
  5. nearest_hospital_name matches reference for >= 95%.   (weight 4, CENTRAL)
  6. Address-set Jaccard vs reference >= 0.95.             (weight 2, data-loss)

Weighting rationale: the central skill is correct nearest-neighbour
assignment computed in a projected CRS (subchecks 4 + 5). A model that
computes in WGS84 degrees, picks the wrong CRS, reports the wrong unit,
or assigns the wrong hospital fails one or both of those and takes the
largest hit. Subcheck 6 (dropped/duplicated addresses) is data loss —
worse than a cosmetic format slip but not the analysis itself — so it
sits between the structural checks (1) and the central ones (4).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    feature_set_equality_by_id,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "nearest_hospital.gpkg"
OUTPUT_NAME = "nearest_hospital.gpkg"


def _read_gdf_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def _coord_key(geom) -> str:
    return f"{geom.x:.3f},{geom.y:.3f}"


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="spa-l1-capetown-hospital-nn")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format / schema validity --------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    sub = _read_gdf_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read GPKG")
        )
        return report

    missing = [c for c in ("nearest_hospital_name", "distance_m") if c not in sub.columns]
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing required columns: {missing}",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    ref_gdf = gpd.read_file(REFERENCE_OUT)

    # ---- Subchecks ------------------------------------------------------
    sub["nearest_hospital_name"] = (
        sub["nearest_hospital_name"].fillna("").astype(str)
    )

    # 1. Geometry types are Point only.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    geom_type_ok = geom_types == {"Point"}
    report.subchecks.append(
        Subcheck(
            "geometry_types_point_only",
            geom_type_ok,
            detail=f"geometry types: {sorted(geom_types)} (expected Point only)",
        )
    )

    # 2. nearest_hospital_name populated.
    name_pop = int((sub["nearest_hospital_name"].str.len() > 0).sum())
    report.subchecks.append(
        Subcheck(
            "nearest_hospital_name_populated",
            name_pop == len(sub),
            detail=f"{name_pop}/{len(sub)} rows have non-empty nearest_hospital_name",
        )
    )

    # 2. distance_m numeric, finite, non-negative.
    try:
        dist_numeric = sub["distance_m"].astype(float)
        dist_clean = dist_numeric.apply(
            lambda v: isinstance(v, float) and math.isfinite(v) and v >= 0
        )
        dist_ok_n = int(dist_clean.sum())
    except Exception:
        dist_ok_n = 0
    report.subchecks.append(
        Subcheck(
            "distance_m_numeric_finite",
            dist_ok_n == len(sub),
            detail=f"{dist_ok_n}/{len(sub)} rows have a finite non-negative distance_m",
        )
    )

    # Build a join key. Prefer address_id; fall back to rounded coordinates.
    if "address_id" in sub.columns and "address_id" in ref_gdf.columns:
        sub_key = sub["address_id"].astype(str)
        ref_key = ref_gdf["address_id"].astype(str)
        key_label = "address_id"
    else:
        sub_key = sub.geometry.apply(_coord_key)
        ref_key = ref_gdf.geometry.apply(_coord_key)
        key_label = "coord_key"

    sub_idx = sub.assign(_k=sub_key.values).drop_duplicates("_k").set_index("_k")
    ref_idx = (
        ref_gdf.assign(_k=ref_key.values).drop_duplicates("_k").set_index("_k")
    )
    common = sorted(set(sub_idx.index) & set(ref_idx.index))

    # 3. distance_m within 50 m of reference for >= 95% of common keys.
    #    The wider tolerance (50 m vs original 1 m) accommodates different
    #    projected CRS choices (e.g. UTM 34S vs UTM 35S) for Cape Town.
    #    A model computing in WGS84 degrees will be off by orders of
    #    magnitude (e.g. 0.05 vs 5000).
    if common:
        diffs = [
            abs(float(sub_idx.loc[k, "distance_m"]) - float(ref_idx.loc[k, "distance_m"]))
            for k in common
        ]
        within_tol = sum(1 for d in diffs if d <= 50.0)
        within_rate = within_tol / len(diffs)
    else:
        within_tol, within_rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "distance_m_matches_reference",
            within_rate >= 0.95,
            detail=(
                f"{within_tol}/{len(common)} rows have |Δdistance| <= 50.0 m vs reference"
                f" (key: {key_label})"
            ),
            weight=4.0,
        )
    )

    # 4. nearest_hospital_name matches reference for >= 95%.
    if common:
        name_matches = sum(
            1
            for k in common
            if str(sub_idx.loc[k, "nearest_hospital_name"]).strip()
            == str(ref_idx.loc[k, "nearest_hospital_name"]).strip()
        )
        name_match_rate = name_matches / len(common)
    else:
        name_matches, name_match_rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "nearest_hospital_name_matches_reference",
            name_match_rate >= 0.95,
            detail=(
                f"{name_matches}/{len(common)} rows match reference's"
                " nearest_hospital_name"
            ),
            weight=4.0,
        )
    )

    # 5. Address-set Jaccard >= 0.95.
    if "address_id" in sub.columns and "address_id" in ref_gdf.columns:
        addr_jaccard = feature_set_equality_by_id(sub, ref_gdf, key="address_id")
    else:
        addr_jaccard = 0.0
    report.subchecks.append(
        Subcheck(
            "address_set_preserved",
            addr_jaccard >= 0.95,
            detail=f"address_id Jaccard {addr_jaccard:.4f}",
            weight=2.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
