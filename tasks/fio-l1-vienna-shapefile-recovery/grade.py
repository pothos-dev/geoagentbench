"""Grader for fio-l1-vienna-shapefile-recovery.

The persona's three skills under test:

  1. Read a CP1252-encoded shapefile correctly (.cpg sidecar respected).
  2. Restore truncated dBase column names from `column_map.csv`.
  3. Reproject from EPSG:31287 (MGI / Austria Lambert) to EPSG:4326.

Single hard gate (`format_schema_valid`): file present, parses as
GeoJSON, and declares *some* usable CRS (or is RFC 7946 implicit
WGS84). A submission with no declarable CRS is unrecoverable — the
grader can't reproject to canonical and downstream geometric subchecks
become undefined.

Subchecks:
  - One subcheck per truncated → original column rename
    (KATASTRALGEMEINDE_NAME, GRUNDSTUECKSNUMMER, EIGENTUEMER_NAME,
    WIDMUNG_BEZEICHNUNG, STRASSE_NAME). Each checks the full name is
    present *and* the truncated alias is absent.
  - Diacritics decoded — at least one ä, ö, ü, ß each appears across
    any string column.
  - Per-id KATASTRALGEMEINDE_NAME values match (uses the truncated
    alias as a fallback key).
  - Per-id EIGENTUEMER_NAME values match.
  - Per-id FLAECHE_M2 numeric values within 1e-6 relative.
  - Per-id geometry centroid within 1e-5° (~1.1 m).
  - Geometry-type uniformity (Polygon/MultiPolygon only).
  - Row count exact against the reference.
  - `crs_is_canonical` — original declared CRS is EPSG:4326.
  - `crs_in_meaningful_set` — original declared CRS is in {EPSG:4326,
    EPSG:31287}. 31287 is the source CRS (agent forgot reprojection
    step); any other CRS is docked an additional point.

The fallback-aliasing in the per-id value subchecks keeps the
*value-preservation* skills graded independently from the
*column-renaming* skill — a "kept truncated names but otherwise
correct" submission scores well on values and only loses the rename
subchecks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    grade_crs_soft,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "parcels.geojson"
OUTPUT_NAME = "parcels.geojson"

# (truncated_alias, full_name) — the recovery the agent must perform.
COLUMN_PAIRS = (
    ("KATASTRALG", "KATASTRALGEMEINDE_NAME"),
    ("GRUNDSTUEC", "GRUNDSTUECKSNUMMER"),
    ("EIGENTUEME", "EIGENTUEMER_NAME"),
    ("WIDMUNG_BE", "WIDMUNG_BEZEICHNUNG"),
    ("STRASSE_NA", "STRASSE_NAME"),
)
DIACRITIC_CHARS = ("ä", "ö", "ü", "ß")
GEOM_EPS_DEG = 1e-5
NUMERIC_REL_TOL = 1e-6

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326, 31287}


def _read_gdf_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def _resolve_col(columns: set[str], full: str, alias: str) -> str | None:
    """Return whichever name the column is exposed under, preferring full."""
    if full in columns:
        return full
    if alias in columns:
        return alias
    return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="fio-l1-vienna-shapefile-recovery")
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
    columns = set(sub.columns)

    # Geometry-type uniformity — Polygon / MultiPolygon only.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    geom_type_ok = bool(geom_types) and geom_types.issubset({"Polygon", "MultiPolygon"})
    report.subchecks.append(
        Subcheck(
            "geometry_type_polygonal",
            geom_type_ok,
            detail=f"geometry types: {sorted(geom_types)} (expected Polygon/MultiPolygon)",
        )
    )

    # Row count exact against the reference.
    n_sub = len(sub)
    n_ref = len(ref_gdf)
    count_ok = n_sub == n_ref
    report.subchecks.append(
        Subcheck(
            "row_count_exact",
            count_ok,
            detail=f"submission {n_sub} rows vs reference {n_ref}",
            weight=3.0,
        )
    )

    # 1–5. Per-column rename: full name present *and* truncated alias absent.
    for alias, full in COLUMN_PAIRS:
        ok = (full in columns) and (alias not in columns)
        report.subchecks.append(
            Subcheck(
                f"column_renamed_{full.lower()}",
                ok,
                detail=(
                    f"{full} present={full in columns}, "
                    f"truncated alias {alias} present={alias in columns}"
                ),
            )
        )

    # 6. Diacritics decoded — scan every string-typed column for ä/ö/ü/ß.
    string_cols = [
        c for c in sub.columns
        if c != sub.geometry.name and sub[c].dtype == object
    ]
    if string_cols:
        haystack = "".join(
            sub[c].fillna("").astype(str).str.cat(sep=" ") for c in string_cols
        )
    else:
        haystack = ""
    found = [ch for ch in DIACRITIC_CHARS if ch in haystack]
    diacritics_ok = len(found) == len(DIACRITIC_CHARS)
    report.subchecks.append(
        Subcheck(
            "diacritics_decoded",
            diacritics_ok,
            detail=f"diacritics found in string columns: {found}",
            weight=3.0,
        )
    )

    # 7–10. Per-id checks — resolve each column under whichever name the
    #       submission exposes it as. The reference uses the full names.
    key_col_sub = _resolve_col(columns, "GRUNDSTUECKSNUMMER", "GRUNDSTUEC")

    common_ids: list[str] = []
    sub_by = ref_by = None
    if key_col_sub is not None and "GRUNDSTUECKSNUMMER" in ref_gdf.columns:
        sub_keys = sub[key_col_sub].astype(str)
        ref_keys = ref_gdf["GRUNDSTUECKSNUMMER"].astype(str)
        common_ids = sorted(set(sub_keys) & set(ref_keys))
        sub_by = sub.assign(_k=sub_keys).drop_duplicates("_k", keep="first").set_index("_k")
        ref_by = ref_gdf.assign(_k=ref_keys).drop_duplicates("_k", keep="first").set_index("_k")

    def _per_id_string_match(full_name: str, alias: str) -> tuple[int, int, bool]:
        if not common_ids or sub_by is None or ref_by is None:
            return 0, 0, False
        sub_col = _resolve_col(set(sub_by.columns), full_name, alias)
        if sub_col is None or full_name not in ref_by.columns:
            return 0, len(common_ids), False
        sa = sub_by.loc[common_ids, sub_col].astype(str).values
        rb = ref_by.loc[common_ids, full_name].astype(str).values
        match = int((sa == rb).sum())
        return match, len(common_ids), match / max(len(common_ids), 1) >= 0.99

    for full_name, alias, label in (
        ("KATASTRALGEMEINDE_NAME", "KATASTRALG", "katastralgemeinde_values_match"),
        ("EIGENTUEMER_NAME", "EIGENTUEME", "eigentuemer_values_match"),
    ):
        match, total, ok = _per_id_string_match(full_name, alias)
        report.subchecks.append(
            Subcheck(label, ok, detail=f"{match}/{total} per-id {full_name} values match", weight=3.0)
        )

    # FLAECHE_M2 numeric.
    if (
        common_ids
        and sub_by is not None
        and ref_by is not None
        and "FLAECHE_M2" in sub_by.columns
        and "FLAECHE_M2" in ref_by.columns
    ):
        sa = sub_by.loc[common_ids, "FLAECHE_M2"].astype(float).values
        rb = ref_by.loc[common_ids, "FLAECHE_M2"].astype(float).values
        denom = np.where(np.abs(rb) < 1e-12, 1e-12, np.abs(rb))
        rel = np.abs(sa - rb) / denom
        flaeche_match = int((rel <= NUMERIC_REL_TOL).sum())
        flaeche_ok = flaeche_match / len(common_ids) >= 0.99
    else:
        flaeche_match = 0
        flaeche_ok = False
    report.subchecks.append(
        Subcheck(
            "flaeche_values_match",
            flaeche_ok,
            detail=(
                f"{flaeche_match}/{len(common_ids)} per-id FLAECHE_M2 "
                f"match within {NUMERIC_REL_TOL:.0e}"
            ),
            weight=3.0,
        )
    )

    # Geometry centroid per id.
    if common_ids and sub_by is not None and ref_by is not None:
        sub_g = sub_by.loc[common_ids, "geometry"]
        ref_g = ref_by.loc[common_ids, "geometry"]
        match = 0
        for sg, rg in zip(sub_g.values, ref_g.values):
            if sg is None or rg is None:
                continue
            sc = sg.centroid
            rc = rg.centroid
            if abs(sc.x - rc.x) <= GEOM_EPS_DEG and abs(sc.y - rc.y) <= GEOM_EPS_DEG:
                match += 1
        geom_ok = match / len(common_ids) >= 0.99
    else:
        match = 0
        geom_ok = False
    report.subchecks.append(
        Subcheck(
            "geometry_reprojected_per_id",
            geom_ok,
            detail=f"{match}/{len(common_ids)} centroids within {GEOM_EPS_DEG:.0e}°",
            weight=3.0,
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
