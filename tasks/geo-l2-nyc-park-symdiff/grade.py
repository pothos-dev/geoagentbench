"""Grader for geo-l2-nyc-park-symdiff.

Skills under test:
  1. Read multi-layer GPKG, compute symmetric difference between two
     park layers in EPSG:6539.
  2. Cluster the symdiff into connected components (collect: single →
     multi).
  3. Classify each cluster with a `source` attribute (parks_official,
     parks_osm, both).
  4. Compute point-on-surface label anchors that lie *inside* their
     parent disagreement geometry.
  5. Write two GeoJSON files in WGS 84: MultiPolygon clusters and
     Point anchors.

Hard gate (`format_schema_valid`) — both files present, parse as
GeoJSON FeatureCollections, required column `source` present in both,
anchor file's geometry types are Point only, and each file declares
*some* usable CRS (or is RFC 7946 implicit WGS 84). A submission with
no declarable CRS is unrecoverable.

Subchecks (weights encode error severity for this geometric-ops task;
the central skill is a correct symmetric-difference overlay in a
projected CRS, so the subchecks that detect its failure carry the
highest weight, structural/cosmetic checks the lowest):
  1. all_multipolygon_disagreement (w=1) — every disagreement geometry
     is MultiPolygon. Structural: recoverable shape slip.
  2. count_within_tolerance (w=3) — disagreement count within ±10 % of
     ref. Core overlay result-structure (cluster cardinality).
  3. source_label_distribution (w=3) — Jaccard ≥ 0.9 of (source) value
     sets; per-source count within ±20 %. Core overlay
     result-structure (per-side attribution).
  4. total_area_within_tolerance (w=4) — total disagreement area within
     ±5 %. CENTRAL: symdiff geometric footprint; catches dropped-side /
     unit / missing-reproject errors cleanly.
  5. unioned_geometry_iou (w=4) — IoU of unioned disagreement vs
     reference ≥ 0.85. CENTRAL: symdiff geometric footprint overlap.
  6. anchors_inside_disagreements (w=2) — every anchor point lies inside
     some disagreement geometry. Secondary label-anchor sub-skill
     (point-on-surface vs centroid); not the core overlay.
  7. anchor_count_matches_disagreements (w=1) — anchor count ==
     disagreement count. Structural cardinality check.
  8. crs_is_canonical (w=1) — both files' original declared CRS is
     EPSG:4326. Cosmetic when recoverable (reprojected internally).
  9. crs_in_meaningful_set (w=1) — both files' original declared CRS is
     in {EPSG:4326}. Cosmetic when recoverable.

Total weight 20. Weights set 2026-06-14 (replacing the blunt
repo-wide weight=3.0-on-all-data-content scheme): area + IoU (the true
symdiff-overlay footprint) are 4; count + source-distribution (overlay
result-structure) are 3; anchors-inside (a distinct secondary skill) is
2; structural/CRS checks are 1.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import geopandas as gpd
from shapely.ops import unary_union

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    count_within_tolerance,
    grade_crs_soft,
    iou_with_tolerance,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REF_DISAGREEMENT = TASK_DIR / "reference" / "solution" / "outputs" / "parks_disagreement.geojson"
REF_ANCHORS = TASK_DIR / "reference" / "solution" / "outputs" / "park_label_anchors.geojson"
OUT_DISAGREEMENT = "parks_disagreement.geojson"
OUT_ANCHORS = "park_label_anchors.geojson"

AREA_CRS = "EPSG:6539"  # metric CRS; applied to BOTH sides for area math
COUNT_TOL = 0.10
PER_SOURCE_TOL = 0.20
AREA_TOL = 0.05
JACCARD_THRESHOLD = 0.9
IOU_THRESHOLD = 0.85

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}


def _is_geojson(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as f:
            head = json.load(f)
    except Exception:
        return False
    return isinstance(head, dict) and head.get("type") == "FeatureCollection"


def _safe_read(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="geo-l2-nyc-park-symdiff")
    sub_d_path = submission_dir / OUT_DISAGREEMENT
    sub_a_path = submission_dir / OUT_ANCHORS

    # ---- Gate: format / schema valid ----------------------------------
    for label, p in (("disagreement", sub_d_path), ("anchors", sub_a_path)):
        if not p.exists():
            report.gates.append(
                Gate("format_schema_valid", False, f"missing output file: {p.name}")
            )
            return report
        if not _is_geojson(p):
            report.gates.append(
                Gate(
                    "format_schema_valid",
                    False,
                    f"{label} output is not a GeoJSON FeatureCollection",
                )
            )
            return report

    sub_d = _safe_read(sub_d_path)
    sub_a = _safe_read(sub_a_path)
    if sub_d is None or sub_a is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not read one of the GeoJSONs")
        )
        return report

    for label, gdf in (("disagreement", sub_d), ("anchors", sub_a)):
        if "source" not in gdf.columns:
            report.gates.append(
                Gate(
                    "format_schema_valid",
                    False,
                    f"{label} missing required column `source`",
                )
            )
            return report

    anchor_geom_types = set(sub_a.geometry.geom_type.dropna().unique())
    if not anchor_geom_types.issubset({"Point"}):
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"anchors file has non-Point geometries: {sorted(anchor_geom_types)}",
            )
        )
        return report

    crs_res_d = grade_crs_soft(
        sub_d, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True
    )
    if not crs_res_d.gate_ok:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"disagreement: {crs_res_d.gate_reason}",
            )
        )
        return report
    crs_res_a = grade_crs_soft(
        sub_a, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True
    )
    if not crs_res_a.gate_ok:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"anchors: {crs_res_a.gate_reason}",
            )
        )
        return report

    sub_d = crs_res_d.normalized
    sub_a = crs_res_a.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks -----------------------------------------------------
    ref_d = gpd.read_file(REF_DISAGREEMENT)
    n_d = len(sub_d)
    n_a = len(sub_a)
    n_ref = len(ref_d)

    # 1. All disagreement geometries are MultiPolygon.
    d_geom_types = set(sub_d.geometry.geom_type.dropna().unique())
    multipoly_only = d_geom_types.issubset({"MultiPolygon"})
    report.subchecks.append(
        Subcheck(
            "all_multipolygon_disagreement",
            multipoly_only,
            detail=f"disagreement geom types: {sorted(d_geom_types)} "
            "(expected only MultiPolygon)",
        )
    )

    # 2. Count within ±10 %.
    count_ok = count_within_tolerance(n_d, n_ref, pct=COUNT_TOL)
    report.subchecks.append(
        Subcheck(
            "count_within_tolerance",
            count_ok,
            detail=f"submission {n_d} vs reference {n_ref} "
            f"(±{int(COUNT_TOL * 100)} %)",
            weight=3.0,  # core overlay result-structure (cluster cardinality)
        )
    )

    # 3. Source-label distribution.
    sub_sources = Counter(sub_d["source"].astype(str).tolist())
    ref_sources = Counter(ref_d["source"].astype(str).tolist())
    set_jacc = jaccard_similarity_set(sub_sources.keys(), ref_sources.keys())
    per_source_ok = True
    deltas = {}
    for src, ref_n in ref_sources.items():
        sub_n = sub_sources.get(src, 0)
        denom = max(ref_n, sub_n, 1)
        rel = abs(ref_n - sub_n) / denom
        deltas[src] = (sub_n, ref_n, rel)
        if rel > PER_SOURCE_TOL:
            per_source_ok = False
    distribution_ok = bool(set_jacc >= JACCARD_THRESHOLD and per_source_ok)
    report.subchecks.append(
        Subcheck(
            "source_label_distribution",
            distribution_ok,
            detail=f"set Jaccard {set_jacc:.3f} (threshold {JACCARD_THRESHOLD}); "
            f"per-source counts (sub, ref, rel): {deltas} "
            f"(per-source threshold {PER_SOURCE_TOL})",
            weight=3.0,  # core overlay result-structure (per-side attribution)
        )
    )

    # 4. Total area within ±5 %. Both sides reprojected the same way to a
    #    metric CRS so the comparison is in real metres² (not WGS84 deg²).
    total_sub = float(sub_d.to_crs(AREA_CRS).geometry.area.sum())
    total_ref = float(ref_d.to_crs(AREA_CRS).geometry.area.sum())
    denom = max(abs(total_sub), abs(total_ref))
    if denom == 0:
        area_ok = total_sub == total_ref
        rel = 0.0
    else:
        rel = abs(total_sub - total_ref) / denom
        area_ok = rel <= AREA_TOL
    report.subchecks.append(
        Subcheck(
            "total_area_within_tolerance",
            bool(area_ok),
            detail=f"submission total {total_sub:.0f} m² vs reference {total_ref:.0f} m² "
            f"(rel diff {rel:.4f}, threshold {AREA_TOL})",
            weight=4.0,  # central skill: symdiff geometric footprint (catches dropped-side / unit / missing-reproject errors)
        )
    )

    # 5. Unioned-geometry IoU.
    sub_union = unary_union(sub_d.geometry.tolist())
    ref_union = unary_union(ref_d.geometry.tolist())
    iou = iou_with_tolerance(sub_union, ref_union, eps=0.0)
    report.subchecks.append(
        Subcheck(
            "unioned_geometry_iou",
            iou >= IOU_THRESHOLD,
            detail=f"unioned IoU {iou:.4f} (threshold {IOU_THRESHOLD})",
            weight=4.0,  # central skill: symdiff geometric footprint overlap
        )
    )

    # 6. Every anchor lies inside the unioned disagreement geometry.
    sub_disagreement_union = sub_union  # reuse
    inside_count = sum(
        1 for p in sub_a.geometry if p is not None and p.within(sub_disagreement_union)
    )
    inside_rate = inside_count / max(len(sub_a), 1)
    anchors_inside_ok = inside_rate >= 0.99
    report.subchecks.append(
        Subcheck(
            "anchors_inside_disagreements",
            anchors_inside_ok,
            detail=f"{inside_count}/{len(sub_a)} anchors lie inside the unioned "
            f"disagreement geometry ({inside_rate:.3f}; threshold 0.99)",
            weight=2.0,  # secondary label-anchor sub-skill (point-on-surface vs centroid); not the core overlay
        )
    )

    # 7. Anchor count matches disagreement count.
    report.subchecks.append(
        Subcheck(
            "anchor_count_matches_disagreements",
            n_a == n_d,
            detail=f"anchors {n_a} vs disagreements {n_d}",
        )
    )

    both_canonical = crs_res_d.is_canonical and crs_res_a.is_canonical
    both_meaningful = crs_res_d.in_meaningful_set and crs_res_a.in_meaningful_set
    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            both_canonical,
            detail=(
                f"disagreement EPSG:{crs_res_d.original_epsg}, "
                f"anchors EPSG:{crs_res_a.original_epsg}; "
                f"canonical EPSG:{CANONICAL_EPSG}"
            ),
        )
    )
    report.subchecks.append(
        Subcheck(
            "crs_in_meaningful_set",
            both_meaningful,
            detail=(
                f"disagreement EPSG:{crs_res_d.original_epsg}, "
                f"anchors EPSG:{crs_res_a.original_epsg}; "
                f"meaningful set {sorted(MEANINGFUL_EPSGS)}"
            ),
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
