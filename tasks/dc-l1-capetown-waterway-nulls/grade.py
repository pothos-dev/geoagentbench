"""Grader for dc-l1-capetown-waterway-nulls.

Single hard gate (`format_schema_valid`) when the file is missing,
unreadable, lacks a usable CRS, or is missing required columns.
Everything else is a one-point subcheck.

The task's central skill is *null / empty handling on a
contractor-style export*: the agent must recognise three independent
defect classes (null geometries, empty LineString geometries, null
`waterway_type`) and drop them while preserving everything else —
including rows whose only oddity is a null `name`. The grader splits
the cleanup contract into independent subchecks (output has no
null/empty geometry, no null waterway_type, correct dropped_count
foreign member, kept the null-name rows, geometry type uniformity)
so an agent that only catches one of the three defect classes is
partially credited.

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
import pandas as pd
from shapely.geometry.base import BaseGeometry

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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "waterways_clean.geojson"
OUTPUT_NAME = "waterways_clean.geojson"

REQUIRED_COLUMNS = {"feature_id", "name", "waterway_type"}
ATTR_COLUMNS = ["name", "waterway_type"]
# Inputs 21..25 carry a null `name` but a valid geometry and waterway_type;
# the persona's drop predicate is on geometry + waterway_type only, so
# these rows must survive the cleanup. Hard-coded here because the rule
# is part of the task spec, not a property of the reference fixture.
NULL_NAME_FEATURE_IDS = {21, 22, 23, 24, 25}
EXPECTED_DROPPED_COUNT = 20
GEOM_EPS_DEG = 1e-7

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}


def _read_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def _read_json_or_none(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _hausdorff_le(a: BaseGeometry, b: BaseGeometry, eps: float) -> bool:
    if a is None or b is None:
        return False
    if a.is_empty or b.is_empty:
        return False
    return a.hausdorff_distance(b) <= eps


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dc-l1-capetown-waterway-nulls")
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

    # Geometry-type uniformity (LineString) — salvageable subcheck so a
    # submission with one stray non-LineString row is docked one point
    # rather than collapsed to zero. We measure on the non-null subset,
    # because the dedicated null/empty subcheck below already flags those.
    nonempty = sub.loc[~(sub.geometry.isna() | sub.geometry.is_empty)]
    geom_types = set(nonempty.geometry.geom_type.unique())
    geom_type_ok = geom_types.issubset({"LineString"})
    report.subchecks.append(
        Subcheck(
            "geometry_type_linestring_only",
            bool(geom_type_ok),
            detail=(
                f"got geometry types {sorted(geom_types)} on non-null subset, "
                "expected LineString"
            ),
        )
    )

    # 1. No null or empty geometries in the output. The persona's primary
    #    drop predicate; an agent that missed either of the two
    #    geometry-defect classes (null vs. empty) fails here.
    n_null = int(sub.geometry.isna().sum())
    n_empty = int((~sub.geometry.isna() & sub.geometry.is_empty).sum())
    no_bad_geom = (n_null == 0) and (n_empty == 0)
    report.subchecks.append(
        Subcheck(
            "no_null_or_empty_geometry_in_output",
            bool(no_bad_geom),
            detail=f"null={n_null}, empty={n_empty}",
            weight=4.0,
        )
    )

    # 2. No null waterway_type values in the output. The persona's
    #    secondary drop predicate; an attribute-typed defect that an
    #    agent who only filters on geometry would miss.
    n_null_wt = int(sub["waterway_type"].isna().sum())
    report.subchecks.append(
        Subcheck(
            "no_null_waterway_type_in_output",
            n_null_wt == 0,
            detail=f"null waterway_type rows: {n_null_wt}",
            weight=4.0,
        )
    )

    # 3-4. The `dropped_count` foreign member on the FeatureCollection.
    #     The persona explicitly asked for this so they can flag the
    #     contractor. Two subchecks: presence (agent remembered) and
    #     correctness (matches the reference exactly — the cleaning
    #     rule is deterministic so the count is too).
    fc = _read_json_or_none(submission_path)
    dropped_value = fc.get("dropped_count") if isinstance(fc, dict) else None
    dropped_present = dropped_value is not None
    report.subchecks.append(
        Subcheck(
            "dropped_count_present",
            dropped_present,
            detail=f"top-level dropped_count = {dropped_value!r}",
        )
    )
    try:
        dropped_int = int(dropped_value) if dropped_present else None
    except (TypeError, ValueError):
        dropped_int = None
    report.subchecks.append(
        Subcheck(
            "dropped_count_correct",
            dropped_int == EXPECTED_DROPPED_COUNT,
            detail=(
                f"reported {dropped_int!r}, expected {EXPECTED_DROPPED_COUNT}"
            ),
            weight=2.0,
        )
    )

    # 5. Feature count within ±5% of the reference. Catches gross
    #    over-dropping (agent dropped null-name rows too) or
    #    under-dropping (agent missed an entire defect class) without
    #    being so tight it flips on a single row.
    count_ok = count_within_tolerance(sub, ref, pct=0.05)
    report.subchecks.append(
        Subcheck(
            "feature_count_within_tolerance",
            bool(count_ok),
            detail=f"submission {len(sub)} vs reference {len(ref)} (±5%)",
            weight=2.0,
        )
    )

    # 6. Feature-id set Jaccard ≥ 0.95. Catches *which* rows the agent
    #    kept, not just how many. An agent that swapped its drop
    #    predicate (kept the bad rows, dropped good ones) would still
    #    pass the count check above but fail this one.
    sub_ids_ok = "feature_id" in sub.columns and "feature_id" in ref.columns
    if sub_ids_ok:
        id_jaccard = feature_set_equality_by_id(sub, ref, key="feature_id")
    else:
        id_jaccard = 0.0
    report.subchecks.append(
        Subcheck(
            "feature_id_set_preserved",
            id_jaccard >= 0.95,
            detail=f"Jaccard {id_jaccard:.4f}",
            weight=4.0,
        )
    )

    # 7. Null-name rows preserved. The persona's spec is explicit that
    #    the drop predicate is geometry + waterway_type only; rows whose
    #    only oddity is a null `name` must survive. Catches the
    #    common LLM failure of "drop any row with any null".
    sub_ids = (
        set(pd.to_numeric(sub["feature_id"], errors="coerce").dropna().astype(int))
        if "feature_id" in sub.columns
        else set()
    )
    null_name_preserved = NULL_NAME_FEATURE_IDS.issubset(sub_ids)
    missing_null_name = sorted(NULL_NAME_FEATURE_IDS - sub_ids)
    report.subchecks.append(
        Subcheck(
            "null_name_rows_preserved",
            null_name_preserved,
            detail=(
                f"missing feature_ids: {missing_null_name}"
                if missing_null_name
                else "all 5 null-name rows present"
            ),
            weight=4.0,
        )
    )

    # 8. Geometry preserved per feature_id. For each id common to both
    #    sides, the LineString must agree within 1e-7° (~ 1 cm at the
    #    equator) under Hausdorff distance. Catches stray reprojection
    #    round-trips and accidental coordinate edits.
    if sub_ids_ok:
        sub_g = sub[["feature_id", "geometry"]].copy()
        ref_g = ref[["feature_id", "geometry"]].copy()
        sub_g["feature_id"] = sub_g["feature_id"].astype("Int64")
        ref_g["feature_id"] = ref_g["feature_id"].astype("Int64")
        sub_g = sub_g.dropna(subset=["feature_id"]).set_index("feature_id")
        ref_g = ref_g.set_index("feature_id")
        common = sorted(set(sub_g.index) & set(ref_g.index))
        if not common:
            geom_match_rate = 0.0
        else:
            matches = sum(
                1
                for fid in common
                if _hausdorff_le(sub_g.loc[fid, "geometry"], ref_g.loc[fid, "geometry"], GEOM_EPS_DEG)
            )
            geom_match_rate = matches / len(common)
    else:
        common = []
        geom_match_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "geometry_preserved_per_id",
            geom_match_rate >= 0.95,
            detail=(
                f"per-id geometry match rate {geom_match_rate:.4f} "
                f"(common ids: {len(common)})"
            ),
            weight=2.5,
        )
    )

    # 9. name + waterway_type preserved per feature_id. The cleanup is
    #    not supposed to mutate attribute values; this catches accidental
    #    rewrites (e.g., the agent re-cased everything, or filled nulls
    #    with a sentinel like "unknown" instead of dropping).
    sub_a = sub[["feature_id"] + ATTR_COLUMNS].copy()
    ref_a = ref[["feature_id"] + ATTR_COLUMNS].copy()
    sub_a["feature_id"] = sub_a["feature_id"].astype(str)
    ref_a["feature_id"] = ref_a["feature_id"].astype(str)
    attr = attribute_match(sub_a, ref_a, fields=ATTR_COLUMNS, key="feature_id")
    attrs_ok = attr["name"] >= 0.95 and attr["waterway_type"] >= 0.95
    report.subchecks.append(
        Subcheck(
            "attributes_preserved_per_id",
            bool(attrs_ok),
            detail=(
                f"name match {attr['name']:.4f}; "
                f"waterway_type match {attr['waterway_type']:.4f}"
            ),
            weight=2.5,
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
