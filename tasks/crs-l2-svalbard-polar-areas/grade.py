"""Grader for crs-l2-svalbard-polar-areas.

One hard gate (``format_schema_valid``). The submission's declared
`crs_epsg` column must hold a single integer EPSG that pyproj can
resolve to a real CRS. A submission with no declarable / unparseable
EPSG is unrecoverable — the grader can't build a reference in that
frame and downstream area / bbox subchecks become undefined.
Membership in the polar accept-list is graded by the two soft CRS
subchecks below.

The reference glacier areas and bounding boxes are NOT pre-computed
against a single canonical CRS — they are recomputed from the source
`inputs/svalbard_glaciers_wgs84.gpkg` at grading time by reprojecting
to the submission's declared CRS. This way an LAEA-Europe pick and an
LAEA-Russia pick are both graded against geometrically-correct
reference values in their respective frames, and a Polar
Stereographic pick is graded against its own polar-stereographic
reference. The reference CSV at
`reference/solution/outputs/svalbard_glaciers_top20.csv` is the
canonical source of the top-20 NAME list only.

Two CRS subchecks grade the agent's pick:
- `equal_area_crs_used` — kept from the previous version; rewards LAEA
  picks over polar-stereographic ones (the textbook "true area"
  choice).
- `crs_in_meaningful_set` — declared EPSG is in MEANINGFUL_EPSGS
  (WGS-84-datum North-Pole-origin projected CRSes, both LAEA and
  Polar Stereographic variants).

  Note: an earlier `crs_is_canonical` subcheck rewarded EPSG:3575
  specifically over the four other LAEA variants. That contradicted
  the design intent — the five LAEA picks produce bit-identical
  areas, so the canonical-pick subcheck reduced to a coin-flip
  penalty against valid solutions and was removed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    attribute_match,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
SOURCE_GPKG = TASK_DIR / "inputs" / "svalbard_glaciers_wgs84.gpkg"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "svalbard_glaciers_top20.csv"
OUTPUT_NAME = "svalbard_glaciers_top20.csv"

REQUIRED_COLUMNS = [
    "name",
    "area_km2",
    "bbox_minx_polar",
    "bbox_miny_polar",
    "bbox_maxx_polar",
    "bbox_maxy_polar",
    "crs_epsg",
]

# The seven WGS-84-datum North-Pole-origin projected CRSes that
# constitute the meaningful set for this task. Five are Lambert
# Azimuthal Equal-Area (3573-3576 cover four sectoral central meridians
# plus 6931 the NSIDC EASE-Grid 2.0 generic), two are Polar
# Stereographic (3413 NSIDC sea-ice convention, 3995 EPSG/EuroGEO Arctic
# convention). At Svalbard latitudes the stereographic variants distort
# area by under 1 %, so they still match the area subchecks; the
# `equal_area_crs_used` subcheck below records the LAEA-vs-stereographic
# distinction. The reference output is produced in EPSG:3575 (LAEA Europe)
# but any of the five LAEA variants is equally valid (bit-identical areas).
MEANINGFUL_EPSGS = {3413, 3573, 3574, 3575, 3576, 3995, 6931}
EQUAL_AREA_EPSGS = {3573, 3574, 3575, 3576, 6931}


def _read_or_none(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _declared_epsg(sub: pd.DataFrame) -> tuple[int | None, str]:
    """Return the single declared EPSG, or (None, reason) if invalid."""
    col = sub["crs_epsg"].dropna()
    if col.empty:
        return None, "crs_epsg column is empty"
    uniq = set(col.astype(int).tolist()) if pd.api.types.is_numeric_dtype(col) else None
    if uniq is None:
        try:
            uniq = set(int(v) for v in col)
        except (TypeError, ValueError):
            return None, "crs_epsg values are not integers"
    if len(uniq) != 1:
        return None, f"crs_epsg is inconsistent across rows: {sorted(uniq)}"
    return next(iter(uniq)), ""


def _reference_in_crs(target_epsg: int) -> pd.DataFrame:
    """Reproject the source glaciers to *target_epsg* and build a
    per-glacier reference frame with the same column layout as the
    submission. Areas in km², bbox in the target CRS metres."""
    src = gpd.read_file(SOURCE_GPKG).to_crs(epsg=target_epsg)
    src["area_km2"] = src.geometry.area / 1_000_000.0
    bounds = src.geometry.bounds.rename(
        columns={
            "minx": "bbox_minx_polar",
            "miny": "bbox_miny_polar",
            "maxx": "bbox_maxx_polar",
            "maxy": "bbox_maxy_polar",
        }
    )
    return pd.concat([src.drop(columns="geometry"), bounds], axis=1)


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="crs-l2-svalbard-polar-areas")
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
            Gate("format_schema_valid", False, "could not read CSV")
        )
        return report

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in sub.columns]
    if missing_cols:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing columns: {missing_cols}",
            )
        )
        return report

    numeric_cols = [c for c in REQUIRED_COLUMNS if c != "name"]
    numeric_ok = all(pd.api.types.is_numeric_dtype(sub[c]) for c in numeric_cols)
    if not numeric_ok:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "area / bbox / crs_epsg columns are not numeric",
            )
        )
        return report

    sub_epsg, epsg_reason = _declared_epsg(sub)
    if sub_epsg is None:
        report.gates.append(Gate("format_schema_valid", False, epsg_reason))
        return report
    # Gate 1 only fails when the EPSG is unparseable; membership in the
    # polar accept-list is soft-graded by the two CRS subchecks below.
    # An unparseable EPSG is unrecoverable because we cannot build the
    # per-glacier reference frame.
    try:
        from pyproj import CRS as _PyprojCRS
        _PyprojCRS.from_epsg(sub_epsg)
    except Exception as exc:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"declared crs_epsg=EPSG:{sub_epsg} is not a parseable EPSG code: {exc}",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    ref_csv = pd.read_csv(REFERENCE_OUT)

    # ---- Build per-glacier reference in the submission's declared CRS --
    # The reference CSV is in EPSG:3575 (LAEA Europe — the canonical
    # equal-area pick for Svalbard) but a submission in any other
    # accepted polar CRS must be graded against reference values in
    # that frame, not against the LAEA values.
    ref_in_sub_crs = _reference_in_crs(sub_epsg)
    # Filter to the canonical top-20 names so per-name lookups don't
    # silently include outside-top-20 features.
    top20_names = set(ref_csv["name"].astype(str).tolist())
    ref_top20 = ref_in_sub_crs[
        ref_in_sub_crs["name"].astype(str).isin(top20_names)
    ].copy()

    # ---- Subchecks ------------------------------------------------------

    # 0. Equal-area CRS used — for "true area" rankings the textbook
    #    pick is a Lambert Azimuthal Equal-Area projection (no area
    #    distortion at any latitude). Polar Stereographic variants are
    #    accepted because their area distortion at Svalbard latitudes
    #    is well under 1 %, but they don't earn this subcheck.
    report.subchecks.append(
        Subcheck(
            "equal_area_crs_used",
            sub_epsg in EQUAL_AREA_EPSGS,
            detail=(
                f"declared CRS is EPSG:{sub_epsg}; equal-area accepted set is "
                f"{sorted(EQUAL_AREA_EPSGS)} (LAEA variants)"
            ),
        )
    )

    # 1. Exactly 20 rows (the persona asked for top 20).
    report.subchecks.append(
        Subcheck(
            "row_count_is_20",
            bool(len(sub) == 20),
            detail=f"observed {len(sub)} rows",
        )
    )

    # 2. Top-N membership (Jaccard >= 0.95) by name. Catches ranking by
    #    geographic-area (degrees^2) instead of projected area.
    sub_names = set(sub["name"].astype(str).tolist())
    ref_names = top20_names
    name_jaccard = jaccard_similarity_set(sub_names, ref_names)
    report.subchecks.append(
        Subcheck(
            "top20_name_set_matches",
            bool(name_jaccard >= 0.95),
            detail=f"Jaccard {name_jaccard:.4f}",
            weight=3.0,
        )
    )

    # 3. Per-glacier area within 1 % of reference (in the agent's frame)
    #    for names that overlap with the reference top-20.
    area_match = attribute_match(
        sub,
        ref_top20,
        fields=["area_km2"],
        key="name",
        tolerance=0.01,
    )
    area_match_rate = area_match["area_km2"]
    report.subchecks.append(
        Subcheck(
            "per_glacier_area_matches",
            bool(area_match_rate >= 0.95),
            detail=f"per-name area match rate {area_match_rate:.4f}",
            weight=3.0,
        )
    )

    # 4. Total top-20 area within 1 % of the reference (in the agent's
    #    frame). A systematic scale error (m^2 vs km^2, area in
    #    degrees^2) explodes here, and so does an off-by-N top-N pick
    #    that drops the biggest glaciers. Sums are over the full top-20
    #    on each side; the reference's areas are computed in the
    #    submission's declared CRS, so a conformal pick that's correct
    #    in its own frame still matches.
    sub_total = float(sub["area_km2"].sum())
    ref_total = float(ref_top20["area_km2"].sum())
    total_pct_diff = abs(sub_total - ref_total) / max(ref_total, 1e-9)
    report.subchecks.append(
        Subcheck(
            "total_top20_area_within_1_percent",
            bool(total_pct_diff <= 0.01),
            detail=(
                f"sub total {sub_total:.2f} km^2; "
                f"ref total {ref_total:.2f} km^2; "
                f"rel diff {total_pct_diff:.4%}"
            ),
            weight=3.0,
        )
    )

    # 5. Sorted descending by area_km2.
    sorted_desc = sub["area_km2"].is_monotonic_decreasing
    report.subchecks.append(
        Subcheck(
            "sorted_by_area_desc",
            bool(sorted_desc),
            detail=f"monotonic_decreasing={sorted_desc}",
        )
    )

    # 6. Per-glacier bbox values match reference within 1 % (relative),
    #    compared against the source reprojected to the submission's
    #    declared CRS. Catches "stamped crs_epsg as 3575 but coordinates
    #    are in WGS84 degrees" because degree-valued bbox columns are
    #    orders of magnitude smaller than LAEA-metre values.
    bbox_match = attribute_match(
        sub,
        ref_top20,
        fields=[
            "bbox_minx_polar",
            "bbox_miny_polar",
            "bbox_maxx_polar",
            "bbox_maxy_polar",
        ],
        key="name",
        tolerance=0.01,
    )
    bbox_ok = (
        bbox_match["bbox_minx_polar"] >= 0.95
        and bbox_match["bbox_miny_polar"] >= 0.95
        and bbox_match["bbox_maxx_polar"] >= 0.95
        and bbox_match["bbox_maxy_polar"] >= 0.95
    )
    report.subchecks.append(
        Subcheck(
            "per_glacier_bbox_matches",
            bool(bbox_ok),
            detail=(
                "match rates: "
                + ", ".join(
                    f"{k}={bbox_match[k]:.3f}"
                    for k in (
                        "bbox_minx_polar",
                        "bbox_miny_polar",
                        "bbox_maxx_polar",
                        "bbox_maxy_polar",
                    )
                )
            ),
            weight=3.0,
        )
    )

    # 7. bbox internal consistency: minx < maxx and miny < maxy on every
    #    row. A solution that swaps order or stores width/height instead
    #    of upper bounds is caught here.
    bbox_consistent = (
        (sub["bbox_minx_polar"] < sub["bbox_maxx_polar"]).all()
        and (sub["bbox_miny_polar"] < sub["bbox_maxy_polar"]).all()
    )
    report.subchecks.append(
        Subcheck(
            "bbox_min_less_than_max",
            bool(bbox_consistent),
            detail="all rows have minx<maxx and miny<maxy"
            if bbox_consistent
            else "at least one row violates min<max",
        )
    )

    # CRS soft-grading subcheck. `equal_area_crs_used` above already
    # rewards LAEA over polar-stereographic; this one grades membership
    # in the broader polar accept-list.
    report.subchecks.append(
        Subcheck(
            "crs_in_meaningful_set",
            sub_epsg in MEANINGFUL_EPSGS,
            detail=(
                f"original EPSG:{sub_epsg}; "
                f"meaningful set {sorted(MEANINGFUL_EPSGS)}"
            ),
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
