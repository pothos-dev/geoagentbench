"""Grader for spa-l2-lagos-hotspot-overlaps.

The persona's question: rank Lagos hex cells by area-weighted population
density across overlapping land-use polygons, after filtering slivers
(< 100 m²). Emit the top 10% as both a GeoParquet of hex polygons and
a plain Parquet ranking table.

Gate — both required files exist, readable, have the required columns
       + dtypes, GeoParquet declares *some* usable CRS with Polygon
       geometries. A submission with no declarable CRS is
       unrecoverable — the grader can't reproject to canonical and
       downstream geometric subchecks become undefined. Whenever the
       gate passes, the submission is reprojected to EPSG:26331
       (Minna / UTM zone 31N) before any spatial subcheck runs — that
       is the reference's CRS. The agent's original CRS pick is graded
       by the soft subchecks.

Subchecks:
  1. hex_id_set_jaccard_vs_reference: top-N hex_id Jaccard ≥ 0.85 (the
     persona's actual answer is "which cells are the hotspots?").
     This is the load-bearing check for the sliver-filter step:
     skipping the filter pulls the top-N toward sliver-dominated
     cells and trips this subcheck.
  2. cross_file_hex_id_set_matches: GeoParquet hex_id set equals the
     Parquet hex_id set (the two outputs must agree on which cells
     are the hot-spots).
  3. density_values_match_reference: for hex_ids in both submission
     and reference top-N, the area_weighted_density agrees with the
     reference within ±5% relative tolerance for ≥ 90% of the
     overlap.
  4. rank_consistent_with_density: within the submission, sorting by
     `rank` ascending must agree with sorting by
     `area_weighted_density` descending (allowing tie-breaks).
  5. overlap_count_matches_reference: per overlapping hex,
     n_overlap_polygons matches the reference exactly for ≥ 90% of
     the overlap.
  6. sliver_count_matches_reference: per overlapping hex,
     n_slivers_filtered matches the reference exactly for ≥ 90% of
     the overlap. Catches an agent who didn't account for slivers
     at all (always 0).
  7. hex_geometries_match: the GeoParquet polygons for shared hex_ids
     are within IoU ≥ 0.95 of the reference's polygons (after the
     submission was reprojected into EPSG:26331 by the gate). Catches
     agents who emitted off-grid hex coordinates.
  8. crs_is_canonical: submission's original CRS is in the canonical
     set {EPSG:26331, EPSG:26391}. EPSG:26331 is "Minna / UTM zone 31N"
     and EPSG:26391 is "Minna / Nigeria West Belt"; both share the
     Minna datum, both are equally defensible readings of "Nigeria's
     national grid" applied to Lagos (26391 wins on registry-faithful
     name match; 26331 is the practical convention used by the
     reference and sibling Lagos tasks).
  9. crs_in_meaningful_set: submission's original CRS is in
     {EPSG:26331, EPSG:26391, EPSG:32631}. EPSG:32631 (WGS84 /
     UTM zone 31N) is a generic defensible fallback. Any other CRS is
     docked an additional point.

Weighting (severity-tiered; total weight 19):
  - Tier 1 (the persona's answer) weight 4.0:
      hex_id_set_jaccard_vs_reference (which cells are the hotspots),
      density_values_match_reference (the ranked metric value).
  - Tier 2 (supporting analytical correctness) weight 2.0:
      cross_file_hex_id_set_matches, overlap_count_matches_reference,
      sliver_count_matches_reference, hex_geometries_match.
  - Tier 3 (structural / cosmetic) weight 1.0:
      rank_consistent_with_density, crs_is_canonical,
      crs_in_meaningful_set.
A wrong-answer failure (Tier 1) costs 4/19 ≈ 0.21; a cosmetic
CRS-label slip (a valid but non-canonical UTM pick) costs only
1/19 ≈ 0.05, so the score gradient tracks error severity.
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
    grade_crs_soft,
    iou_with_tolerance,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REF_DIR = TASK_DIR / "reference" / "solution" / "outputs"
HOTSPOTS_NAME = "hotspots.geoparquet"
RANKING_NAME = "hotspot_ranking.parquet"

# "Nigeria's national grid" applied to Lagos has two equally defensible
# canonical EPSG picks that share the Minna datum:
#   - EPSG:26331 — Minna / UTM zone 31N. Practical convention; what the
#     reference and sibling Lagos tasks use. Officially area-of-use is
#     "Nigeria offshore beyond continental shelf west of 6°E", but it
#     is widely used onshore as a metric CRS for southwest Nigeria.
#   - EPSG:26391 — Minna / Nigeria West Belt. The literal registry name
#     match for "Nigeria's national grid" (the 26391/26392/26393 family
#     is *the* national grid for onshore Nigeria). Lagos sits in the
#     West Belt geographically.
# Both are accepted as canonical. EPSG:32631 (WGS84 / UTM zone 31N) is
# a meaningful-but-not-canonical fallback (same projection family,
# WGS84 datum — generic rather than Nigeria-specific). The submission
# is always reprojected to min(canonical) = EPSG:26331 (the reference's
# CRS) before any spatial subcheck runs; the agent's original CRS pick
# is graded by the soft subchecks at the end.
CANONICAL_EPSGS = {26331, 26391}
MEANINGFUL_EPSGS = {26331, 26391, 32631}

EXPECTED_GEO_COLS = {"hex_id", "rank", "area_weighted_density"}
EXPECTED_TABLE_COLS = {
    "hex_id",
    "rank",
    "area_weighted_density",
    "n_overlap_polygons",
    "n_slivers_filtered",
}

DENSITY_REL_TOL = 0.05
COUNT_MATCH_FRACTION = 0.90
ID_JACCARD_MIN = 0.85
DENSITY_MATCH_FRACTION = 0.90
GEOM_IOU_MIN = 0.95


def _safe_read_geoparquet(path: Path):
    try:
        return gpd.read_parquet(path)
    except Exception as exc:
        return exc


def _safe_read_parquet(path: Path):
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        return exc


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="spa-l2-lagos-hotspot-overlaps")

    geo_path = submission_dir / HOTSPOTS_NAME
    tab_path = submission_dir / RANKING_NAME

    # ---- Gate: schema validity ----------------------------------------
    g1_problems: list[str] = []
    if not geo_path.exists():
        g1_problems.append(f"missing {HOTSPOTS_NAME}")
    if not tab_path.exists():
        g1_problems.append(f"missing {RANKING_NAME}")
    if g1_problems:
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(g1_problems))
        )
        return report

    geo = _safe_read_geoparquet(geo_path)
    tab = _safe_read_parquet(tab_path)
    if isinstance(geo, Exception):
        g1_problems.append(f"could not read {HOTSPOTS_NAME}: {geo}")
    if isinstance(tab, Exception):
        g1_problems.append(f"could not read {RANKING_NAME}: {tab}")
    if g1_problems:
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(g1_problems))
        )
        return report

    if not EXPECTED_GEO_COLS.issubset(geo.columns):
        g1_problems.append(
            f"{HOTSPOTS_NAME} missing columns: "
            f"{sorted(EXPECTED_GEO_COLS - set(geo.columns))}"
        )
    if not EXPECTED_TABLE_COLS.issubset(tab.columns):
        g1_problems.append(
            f"{RANKING_NAME} missing columns: "
            f"{sorted(EXPECTED_TABLE_COLS - set(tab.columns))}"
        )
    if "geometry" not in getattr(geo, "columns", []) or geo.geometry is None:
        g1_problems.append(f"{HOTSPOTS_NAME} has no geometry column")
    # Soft-grade the CRS: hard-fail only if the submission has no usable
    # CRS at all (otherwise reproject to min(CANONICAL_EPSGS) = 26331 for
    # downstream spatial subchecks, and grade the original pick via the
    # crs_is_canonical / crs_in_meaningful_set subchecks at the end).
    crs_res = grade_crs_soft(geo, MEANINGFUL_EPSGS, CANONICAL_EPSGS)
    if not crs_res.gate_ok:
        g1_problems.append(f"{HOTSPOTS_NAME}: {crs_res.gate_reason}")
    else:
        geo = crs_res.normalized
    geom_types = set(geo.geometry.geom_type.dropna().unique()) if len(geo) else {"Polygon"}
    if not geom_types.issubset({"Polygon", "MultiPolygon"}):
        g1_problems.append(
            f"{HOTSPOTS_NAME} unexpected geometry types: {sorted(geom_types)}"
        )

    if g1_problems:
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(g1_problems))
        )
        return report
    report.gates.append(Gate("format_schema_valid", True))

    ref_geo = gpd.read_parquet(REF_DIR / HOTSPOTS_NAME)
    ref_tab = pd.read_parquet(REF_DIR / RANKING_NAME)

    # Submission was already reprojected to min(CANONICAL_EPSGS) = 26331
    # by the gate via grade_crs_soft; the reference is in the same CRS,
    # so no further reprojection is needed before the spatial subchecks.

    geo_ids = set(geo["hex_id"].astype(str))
    tab_ids = set(tab["hex_id"].astype(str))

    # ---- Subchecks ----------------------------------------------------

    sub_ids = geo_ids
    ref_ids = set(ref_geo["hex_id"].astype(str))
    common_ids = sorted(sub_ids & ref_ids)

    # Subcheck 1: hex_id set Jaccard vs reference top-N.
    id_jaccard = jaccard_similarity_set(sub_ids, ref_ids)
    report.subchecks.append(
        Subcheck(
            "hex_id_set_jaccard_vs_reference",
            id_jaccard >= ID_JACCARD_MIN,
            detail=(
                f"Jaccard(submission top-N hex_ids, reference top-N hex_ids) = "
                f"{id_jaccard:.4f}; threshold {ID_JACCARD_MIN}"
            ),
            # Tier 1 (central skill): this is the persona's actual answer —
            # "which cells are the hotspots?". Highest weight.
            weight=4.0,
        )
    )

    # Subcheck: GeoParquet and Parquet must agree on which cells are top-N.
    cross_set_ok = geo_ids == tab_ids and len(geo) == len(tab)
    only_geo = sorted(geo_ids - tab_ids)[:3]
    only_tab = sorted(tab_ids - geo_ids)[:3]
    report.subchecks.append(
        Subcheck(
            "cross_file_hex_id_set_matches",
            cross_set_ok,
            detail=(
                f"{HOTSPOTS_NAME} rows={len(geo)}, {RANKING_NAME} rows={len(tab)}; "
                f"only-geo: {only_geo}, only-tab: {only_tab}"
            ),
            # Tier 2 (supporting correctness): cross-file consistency / output
            # hygiene, not the analytical answer itself.
            weight=2.0,
        )
    )

    # Index reference and submission tabular by hex_id for lookups.
    sub_tab = tab.set_index(tab["hex_id"].astype(str))
    r_tab = ref_tab.set_index(ref_tab["hex_id"].astype(str))

    # Subcheck 2: density values within ±5% for overlapping ids.
    n_density_ok = 0
    for hid in common_ids:
        sub_d = float(sub_tab.loc[hid, "area_weighted_density"])
        ref_d = float(r_tab.loc[hid, "area_weighted_density"])
        denom = max(abs(ref_d), 1e-9)
        if abs(sub_d - ref_d) / denom <= DENSITY_REL_TOL:
            n_density_ok += 1
    density_rate = n_density_ok / max(len(common_ids), 1)
    report.subchecks.append(
        Subcheck(
            "density_values_match_reference",
            density_rate >= DENSITY_MATCH_FRACTION,
            detail=(
                f"{n_density_ok}/{len(common_ids)} shared hex_ids have "
                f"|Δ|/|ref| ≤ {DENSITY_REL_TOL:.0%} on area_weighted_density"
            ),
            # Tier 1 (central skill): the ranked metric value is the other half
            # of the persona's answer (overlap-aware area-weighted mean).
            weight=4.0,
        )
    )

    # Subcheck 3: rank ↑ ≡ density ↓ (within the submission).
    sub_sorted = tab.sort_values("rank", kind="stable").reset_index(drop=True)
    densities = sub_sorted["area_weighted_density"].astype(float).tolist()
    is_monotone = all(
        densities[i] >= densities[i + 1] - 1e-9
        for i in range(len(densities) - 1)
    )
    ranks = sub_sorted["rank"].astype(int).tolist()
    rank_unique = len(set(ranks)) == len(ranks)
    rank_starts_at_1 = (min(ranks) == 1) if ranks else True
    report.subchecks.append(
        Subcheck(
            "rank_consistent_with_density",
            is_monotone and rank_unique and rank_starts_at_1,
            detail=(
                f"density-monotone-by-rank={is_monotone}, "
                f"unique_rank={rank_unique}, starts_at_1={rank_starts_at_1}"
            ),
        )
    )

    # Subcheck 4: n_overlap_polygons match for shared ids (exact).
    n_overlap_ok = 0
    for hid in common_ids:
        if int(sub_tab.loc[hid, "n_overlap_polygons"]) == int(
            r_tab.loc[hid, "n_overlap_polygons"]
        ):
            n_overlap_ok += 1
    overlap_rate = n_overlap_ok / max(len(common_ids), 1)
    report.subchecks.append(
        Subcheck(
            "overlap_count_matches_reference",
            overlap_rate >= COUNT_MATCH_FRACTION,
            detail=(
                f"{n_overlap_ok}/{len(common_ids)} shared hex_ids have "
                f"matching n_overlap_polygons"
            ),
            # Tier 2 (supporting correctness): per-cell overlap count verifies
            # the overlay step but is a diagnostic alongside the answer.
            weight=2.0,
        )
    )

    # Subcheck 5: n_slivers_filtered match for shared ids (exact).
    n_sliv_ok = 0
    for hid in common_ids:
        if int(sub_tab.loc[hid, "n_slivers_filtered"]) == int(
            r_tab.loc[hid, "n_slivers_filtered"]
        ):
            n_sliv_ok += 1
    sliv_rate = n_sliv_ok / max(len(common_ids), 1)
    report.subchecks.append(
        Subcheck(
            "sliver_count_matches_reference",
            sliv_rate >= COUNT_MATCH_FRACTION,
            detail=(
                f"{n_sliv_ok}/{len(common_ids)} shared hex_ids have "
                f"matching n_slivers_filtered"
            ),
            # Tier 2 (supporting correctness): the per-cell sliver-filter
            # traceability count; central enough to flag "didn't filter at
            # all" but a diagnostic rather than the answer.
            weight=2.0,
        )
    )

    # Subcheck 6: hex polygon geometries match reference for shared ids.
    sub_geo_idx = geo.set_index(geo["hex_id"].astype(str))
    ref_geo_idx = ref_geo.set_index(ref_geo["hex_id"].astype(str))
    geom_ok = 0
    for hid in common_ids:
        s_geom = sub_geo_idx.loc[hid, "geometry"]
        r_geom = ref_geo_idx.loc[hid, "geometry"]
        if iou_with_tolerance(s_geom, r_geom, eps=0.0) >= GEOM_IOU_MIN:
            geom_ok += 1
    geom_rate = geom_ok / max(len(common_ids), 1)
    report.subchecks.append(
        Subcheck(
            "hex_geometries_match",
            geom_rate >= COUNT_MATCH_FRACTION,
            detail=(
                f"{geom_ok}/{len(common_ids)} shared hex polygons have "
                f"IoU ≥ {GEOM_IOU_MIN} with the reference polygon"
            ),
            # Tier 2 (supporting correctness): emitted hex geometry must match,
            # but the cells/metric are the answer; geometry is the carrier.
            weight=2.0,
        )
    )

    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            crs_res.is_canonical,
            detail=(
                f"original EPSG:{crs_res.original_epsg}; "
                f"canonical set {sorted(CANONICAL_EPSGS)} "
                f"(26331 = Minna / UTM zone 31N; 26391 = Minna / Nigeria West Belt)"
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
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
