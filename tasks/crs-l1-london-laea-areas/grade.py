"""Grader for crs-l1-london-laea-areas.

One hard gate (``format_schema_valid`` — CSV present, parseable, with the
required columns) plus a checklist of binary subchecks. The task asks for a
CSV with area in km² — no output CRS is specified, so the model must
independently choose an appropriate projected CRS for area computation.
Tolerances are wider (2 %) than the original GeoJSON variant to accept any
reasonable equal-area or conformal projection (LAEA, UTM, OSGB, geodesic
area) for the London region.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "borough_areas.csv"
OUTPUT_NAME = "borough_areas.csv"


def _read_csv_or_none(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="crs-l1-london-laea-areas")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format/schema validity --------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    sub = _read_csv_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not parse as CSV")
        )
        return report

    required_cols = {"id", "name", "area_km2"}
    missing = required_cols - set(sub.columns)
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing columns: {sorted(missing)}",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    ref = pd.read_csv(REFERENCE_OUT)

    # ---- Subchecks ------------------------------------------------------
    # 0. Row count within 5 % of reference. A miscount usually means a
    #    silent filter — borough rows dropped or duplicated.
    count_rel_diff = abs(len(sub) - len(ref)) / max(len(ref), 1)
    report.subchecks.append(
        Subcheck(
            "row_count_within_5_percent",
            bool(count_rel_diff <= 0.05),
            detail=f"sub rows {len(sub)}; ref rows {len(ref)}; rel diff {count_rel_diff:.4%}",
            weight=1.0,
        )
    )

    # 1. Feature-id set Jaccard >= 0.95
    sub_ids = set(sub["id"].dropna().astype(str))
    ref_ids = set(ref["id"].dropna().astype(str))
    intersection = len(sub_ids & ref_ids)
    union = len(sub_ids | ref_ids)
    id_jaccard = intersection / max(union, 1)
    report.subchecks.append(
        Subcheck(
            "feature_id_set_preserved",
            bool(id_jaccard >= 0.95),
            detail=f"Jaccard {id_jaccard:.4f}",
            weight=2.0,
        )
    )

    # 2. Per-feature area match (2% relative tolerance over common ids).
    #    The wider tolerance accepts any reasonable projected CRS for the
    #    London region (LAEA, UTM 30N/31N, OSGB, geodesic).
    merged = pd.merge(
        sub[["id", "area_km2"]],
        ref[["id", "area_km2"]],
        on="id",
        suffixes=("_sub", "_ref"),
        how="inner",
    )
    if len(merged) > 0:
        rel_diff = (
            (merged["area_km2_sub"] - merged["area_km2_ref"]).abs()
            / merged["area_km2_ref"].clip(lower=1e-9)
        )
        match_rate = float((rel_diff <= 0.02).mean())
    else:
        match_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "area_km2_per_feature_matches",
            bool(match_rate >= 0.95),
            detail=f"per-id area match rate {match_rate:.4f} (2% tolerance)",
            weight=5.0,
        )
    )

    # 3. Total-area sanity: sum of all per-feature areas within 2%.
    sub_total = float(sub["area_km2"].sum())
    ref_total = float(ref["area_km2"].sum())
    total_pct_diff = abs(sub_total - ref_total) / max(ref_total, 1e-9)
    report.subchecks.append(
        Subcheck(
            "total_area_within_2_percent",
            bool(total_pct_diff <= 0.02),
            detail=(
                f"sub total {sub_total:.2f} km²; "
                f"ref total {ref_total:.2f} km²; rel diff {total_pct_diff:.4%}"
            ),
            weight=3.0,
        )
    )

    # 4. Area column is numeric.
    is_numeric = sub["area_km2"].dtype.kind in ("i", "u", "f")
    report.subchecks.append(
        Subcheck(
            "area_column_is_numeric",
            bool(is_numeric),
            detail=f"dtype={sub['area_km2'].dtype}",
            weight=0.5,
        )
    )

    # 5. Name attribute preserved.
    if len(merged) > 0:
        name_merged = pd.merge(
            sub[["id", "name"]].rename(columns={"name": "name_sub"}),
            ref[["id", "name"]].rename(columns={"name": "name_ref"}),
            on="id",
            how="inner",
        )
        name_match_rate = float(
            (name_merged["name_sub"] == name_merged["name_ref"]).mean()
        )
    else:
        name_match_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "name_attribute_preserved",
            bool(name_match_rate >= 0.95),
            detail=f"name match rate {name_match_rate:.4f}",
            weight=1.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
