"""Grader for fio-l1-paris-kml-pois.

The persona's question is "convert this KML to a flat GeoJSON with the
Folder name carried through as a `category` attribute and the
'Dernière vérification' date extracted into a `verified_date` column".

Single hard gate (`format_schema_valid`): file exists, parses as
GeoJSON, has the three required attribute columns (`name`, `category`,
`verified_date`) plus geometry, and declares *some* usable CRS (or is
RFC 7946 implicit WGS84). A submission with no declarable CRS is
unrecoverable — the grader can't reproject and downstream geometric
subchecks become undefined.

Subchecks:
  1. The set of `name` values matches the reference (Jaccard ≥ 0.95).
  2. `category` is populated with one of the three Folder labels for
     every row.
  3. Per-name `category` agreement (≥ 99 % match on common names) —
     catches an agent that merged folders into one bucket.
  4. Per-name geometry agreement within ~1 m (≈ 1e-5°) — catches an
     agent that swapped axes (lat,lon) → (lon,lat).
  5. `verified_date` is populated for every row and every value parses
     as an ISO date (YYYY-MM-DD).
  6. Per-name `verified_date` matches the reference (≥ 99 % of common
     names) — catches an agent that failed to extract the date or
     extracted the wrong one.
  7. Geometry-type uniformity — every feature is a Point.
  8. Row count within ±5 % of the reference.
  9. `crs_is_canonical` — original declared CRS is EPSG:4326.
  10. `crs_in_meaningful_set` — original declared CRS is in {EPSG:4326}.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "paris_pois.geojson"
OUTPUT_NAME = "paris_pois.geojson"

REQUIRED_COLUMNS = {"name", "category", "verified_date"}
EXPECTED_CATEGORIES = {
    "Cafés ouverts tard",
    "Bibliothèques de nuit",
    "Tours et infos touristiques",
}
GEOM_EPS_DEG = 1e-5  # ~1.1 m at this latitude — catches axis swaps & reprojections.

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ANY_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _read_gdf_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def _extract_any_date(value: object) -> date | None:
    """Lenient: pulls a YYYY-MM-DD out of a longer string if present.

    Used only for per-name agreement so that an agent who extracted the
    correct date but left it embedded in noise still receives credit
    for getting the *value* right (the format failure is signalled by
    the dedicated iso-format subcheck)."""
    if value is None:
        return None
    match = _ANY_DATE_RE.search(str(value))
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="fio-l1-paris-kml-pois")
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
            Gate("format_schema_valid", False, "could not read GeoJSON")
        )
        return report

    column_names = set(sub.columns)
    missing = REQUIRED_COLUMNS - column_names
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing columns: {sorted(missing)}",
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
    sub["name"] = sub["name"].fillna("").astype(str)
    sub["category"] = sub["category"].fillna("").astype(str)

    # Geometry-type uniformity — every feature should be a Point.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    geom_type_ok = geom_types == {"Point"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_point_only",
            geom_type_ok,
            detail=f"geometry types: {sorted(geom_types)} (expected only Point)",
        )
    )

    # Row count within ±5 % of the reference.
    n_sub = len(sub)
    n_ref = len(ref_gdf)
    count_ok = (
        abs(n_sub - n_ref) / max(n_sub, n_ref) <= 0.05
        if max(n_sub, n_ref)
        else True
    )
    report.subchecks.append(
        Subcheck(
            "row_count_within_tolerance",
            count_ok,
            detail=f"submission {n_sub} rows vs reference {n_ref} (±5 %)",
            weight=3.0,
        )
    )

    # 1. Name set Jaccard.
    name_jaccard = feature_set_equality_by_id(sub, ref_gdf, key="name")
    report.subchecks.append(
        Subcheck(
            "name_set_preserved",
            name_jaccard >= 0.95,
            detail=f"name Jaccard {name_jaccard:.4f}",
            weight=3.5,
        )
    )

    # 2. category populated with one of the expected folder labels.
    cat_pop = int((sub["category"].str.len() > 0).sum())
    cat_known = int(sub["category"].isin(EXPECTED_CATEGORIES).sum())
    cat_ok = cat_pop == len(sub) and cat_known == len(sub)
    report.subchecks.append(
        Subcheck(
            "category_populated_and_recognised",
            cat_ok,
            detail=(
                f"{cat_pop}/{len(sub)} rows populated, "
                f"{cat_known}/{len(sub)} match an expected folder label"
            ),
            weight=2.0,
        )
    )

    # 3. Per-name category agreement.
    common_names = sorted(set(sub["name"]) & set(ref_gdf["name"]))
    sub_by = sub.drop_duplicates("name", keep="first").set_index("name")
    ref_by = ref_gdf.drop_duplicates("name", keep="first").set_index("name")

    if common_names:
        sub_cat = sub_by.loc[common_names, "category"]
        ref_cat = ref_by.loc[common_names, "category"]
        cat_match = int((sub_cat.values == ref_cat.values).sum())
        cat_rate = cat_match / len(common_names)
    else:
        cat_match, cat_rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "category_values_match",
            cat_rate >= 0.99,
            detail=f"{cat_match}/{len(common_names)} per-name categories match",
            weight=3.0,
        )
    )

    # 4. Per-name geometry agreement.
    if common_names:
        sub_g = sub_by.loc[common_names, "geometry"]
        ref_g = ref_by.loc[common_names, "geometry"]
        match = 0
        for sg, rg in zip(sub_g.values, ref_g.values):
            if sg is None or rg is None:
                continue
            if abs(sg.x - rg.x) <= GEOM_EPS_DEG and abs(sg.y - rg.y) <= GEOM_EPS_DEG:
                match += 1
        geom_rate = match / len(common_names)
    else:
        match, geom_rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "geometry_preserved_per_name",
            geom_rate >= 0.99,
            detail=f"{match}/{len(common_names)} points within {GEOM_EPS_DEG:.0e}°",
            weight=3.0,
        )
    )

    # 5. verified_date populated and ISO-formatted on every row.
    # Read the raw JSON because pyogrio auto-types YYYY-MM-DD columns as
    # datetime64[ms], hiding the original string form. The format check
    # must verify what the agent literally wrote on disk.
    with open(submission_path) as fp:
        raw = json.load(fp)
    raw_dates = [
        f.get("properties", {}).get("verified_date") for f in raw.get("features", [])
    ]
    n_iso = sum(
        1
        for v in raw_dates
        if isinstance(v, str) and _ISO_DATE_RE.match(v) is not None
    )
    iso_ok = n_iso == len(sub)
    report.subchecks.append(
        Subcheck(
            "verified_date_iso_format",
            iso_ok,
            detail=f"{n_iso}/{len(sub)} rows have a YYYY-MM-DD verified_date",
            weight=2.0,
        )
    )

    # 6. Per-name verified_date matches the reference (lenient parse on
    # both sides so an agent who got the value right but kept it in a
    # longer string still scores here — the format failure already
    # showed up in subcheck 5).
    if common_names:
        date_match = 0
        for n in common_names:
            sub_d = _extract_any_date(sub_by.loc[n, "verified_date"])
            ref_d = _extract_any_date(ref_by.loc[n, "verified_date"])
            if sub_d is not None and sub_d == ref_d:
                date_match += 1
        date_rate = date_match / len(common_names)
    else:
        date_match, date_rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "verified_date_values_match",
            date_rate >= 0.99,
            detail=f"{date_match}/{len(common_names)} per-name verified_dates match",
            weight=4.0,
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
