"""Grader for geo-l1-cairo-multipoint-hull.

The persona's question is "give me the convex hull of each station's
MultiPoint of entrances, with both Arabic and English names preserved".

Hard gate (`format_schema_valid`) — file exists, parses as GeoJSON,
has the two required attribute columns (`station_name_en`,
`station_name_ar`), and declares *some* usable CRS (or is RFC 7946
implicit WGS 84). A submission with no declarable CRS is unrecoverable
— the grader can't reproject to canonical and downstream geometric
subchecks become undefined.

Subchecks:
  1. `station_name_en` populated (non-empty) for every row.
  2. `station_name_ar` populated for every row.
  3. English-name set Jaccard vs reference ≥ 0.95.
  4. Per-station Arabic-name agreement (≥ 99 % match on common English
     names).
  5. Per-station hull contains its input MultiPoint vertices (≥ 99 %).
  6. Per-station mean IoU ≥ 0.95 against the reference hull.
  7. Geometry types are Polygon only.
  8. Row count within ±5 % of reference.
  9. `crs_is_canonical` — original declared CRS is EPSG:4326.
  10. `crs_in_meaningful_set` — original declared CRS is in {EPSG:4326}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    feature_set_equality_by_id,
    grade_crs_soft,
    iou_with_tolerance,
)

TASK_DIR = Path(__file__).resolve().parent
INPUT = TASK_DIR / "inputs" / "cairo_metro_stations.geojson"
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "cairo_metro_hulls.geojson"
OUTPUT_NAME = "cairo_metro_hulls.geojson"

REQUIRED_COLUMNS = {"station_name_en", "station_name_ar"}

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}


def _read_gdf_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="geo-l1-cairo-multipoint-hull")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate 1: format / schema validity ------------------------------
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

    missing = REQUIRED_COLUMNS - set(sub.columns)
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
    n_sub = len(sub)
    n_ref = len(ref_gdf)

    sub["station_name_en"] = sub["station_name_en"].fillna("").astype(str)
    sub["station_name_ar"] = sub["station_name_ar"].fillna("").astype(str)

    # 1. English name populated.
    en_pop = int((sub["station_name_en"].str.len() > 0).sum())
    report.subchecks.append(
        Subcheck(
            "station_name_en_populated",
            en_pop == len(sub),
            detail=f"{en_pop}/{len(sub)} rows have non-empty station_name_en",
        )
    )

    # 2. Arabic name populated.
    ar_pop = int((sub["station_name_ar"].str.len() > 0).sum())
    report.subchecks.append(
        Subcheck(
            "station_name_ar_populated",
            ar_pop == len(sub),
            detail=f"{ar_pop}/{len(sub)} rows have non-empty station_name_ar",
        )
    )

    # 3. English-name set Jaccard.
    en_jaccard = feature_set_equality_by_id(sub, ref_gdf, key="station_name_en")
    report.subchecks.append(
        Subcheck(
            "station_name_en_set_preserved",
            en_jaccard >= 0.95,
            detail=f"english-name Jaccard {en_jaccard:.4f}",
            weight=3.0,  # bilingual data: persona-required, but not the central hull skill
        )
    )

    # 4. Per-name Arabic-name agreement.
    common_en = sorted(set(sub["station_name_en"]) & set(ref_gdf["station_name_en"]))
    sub_by = sub.drop_duplicates("station_name_en", keep="first").set_index(
        "station_name_en"
    )
    ref_by = ref_gdf.drop_duplicates("station_name_en", keep="first").set_index(
        "station_name_en"
    )
    if common_en:
        ar_match = int(
            (
                sub_by.loc[common_en, "station_name_ar"].values
                == ref_by.loc[common_en, "station_name_ar"].values
            ).sum()
        )
        ar_rate = ar_match / len(common_en)
    else:
        ar_match, ar_rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "arabic_names_match",
            ar_rate >= 0.99,
            detail=f"{ar_match}/{len(common_en)} arabic names match",
            weight=3.0,  # bilingual data: persona-required, but not the central hull skill
        )
    )

    # 5. Hulls contain their input MultiPoint vertices.
    inp = gpd.read_file(INPUT)
    inp_by = inp.drop_duplicates("station_name_en", keep="first").set_index(
        "station_name_en"
    )
    if common_en:
        contained = 0
        for name in common_en:
            hull = sub_by.loc[name, "geometry"]
            mp = inp_by.loc[name, "geometry"] if name in inp_by.index else None
            if hull is None or mp is None:
                continue
            # A buffered hull catches sub-millimetre serialisation drift
            # without admitting truly-misplaced polygons.
            hull_b = hull.buffer(1e-7)
            if all(hull_b.covers(p) for p in mp.geoms):
                contained += 1
        contain_rate = contained / len(common_en)
    else:
        contained, contain_rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "hull_contains_input_points",
            contain_rate >= 0.99,
            detail=f"{contained}/{len(common_en)} hulls cover all input entrances",
            weight=4.0,  # central hull skill: wrong-station pairing / no-op hull
        )
    )

    # 6. Per-station IoU ≥ 0.95 mean against the reference hull.
    if common_en:
        ious = []
        for name in common_en:
            sg = sub_by.loc[name, "geometry"]
            rg = ref_by.loc[name, "geometry"]
            if sg is None or rg is None or sg.is_empty or rg.is_empty:
                ious.append(0.0)
                continue
            ious.append(iou_with_tolerance(sg, rg, eps=0))
        mean_iou = sum(ious) / len(ious)
    else:
        mean_iou = 0.0
    report.subchecks.append(
        Subcheck(
            "hull_iou_against_reference",
            mean_iou >= 0.95,
            detail=f"mean per-station IoU {mean_iou:.4f}",
            weight=5.0,  # central hull skill: wrong hull shape (bbox/buffer) is THE failure this task probes
        )
    )

    # Geometry types are Polygon only.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    report.subchecks.append(
        Subcheck(
            "geometry_types_polygon",
            geom_types == {"Polygon"},
            detail=f"geometry types: {sorted(geom_types)} (expected Polygon only)",
            weight=2.0,  # structural: non-Polygon output signals no-op (co-detected by IoU)
        )
    )

    # Row count within ±5 % of reference.
    count_ok = (
        abs(n_sub - n_ref) / max(n_sub, n_ref) <= 0.05 if max(n_sub, n_ref) else True
    )
    report.subchecks.append(
        Subcheck(
            "row_count_within_tolerance",
            count_ok,
            detail=f"submission {n_sub} vs reference {n_ref} (±5%)",
            weight=3.0,  # per-row vs global hull twist: a collapse co-fails the per-station checks
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
            weight=0.5,  # cosmetic: wrong CRS is recoverable (reprojected), all-WGS84 task
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
            weight=0.5,  # cosmetic: wrong CRS is recoverable (reprojected), all-WGS84 task
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
