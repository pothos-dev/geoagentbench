"""Grader for fio-l2-cairo-mixedgeom-split.

The persona's three skills under test:

  1. Stratify a mixed-geometry FeatureCollection into per-type layers.
  2. Explode multi-part polygons into singletons.
  3. Reproject to a metric CRS for Cairo and write a multi-layer GPKG
     that preserves the originating `site_id` on every feature.

The instruction asks for "Egypt's national grid" as a category-level
hint without naming an EPSG. Egypt Red Belt (EPSG:22992) is the
canonical national grid and the only CRS rewarded by the
`crs_is_canonical` subcheck. UTM 36N (EPSG:32636) is in the meaningful
set as a defensible generic alternative for Cairo (an agent picking
32636 is reasoning generically rather than regionally); a 32636
submission is reprojected into EPSG:22992 before any spatial subcheck
runs.

Single hard gate (`format_schema_valid`): file present, parses as
GPKG, exposes the three required layers (`points`, `lines`,
`polygons`), each declares *some* usable CRS, each carries a `site_id`
column. A layer with no declarable CRS is unrecoverable — the grader
can't reproject and downstream geometric subchecks become undefined.
Layers are reprojected into the canonical EPSG:22992 before subchecks
regardless of which CRS the agent picked.

Subchecks:
  - polygons layer contains no MultiPolygon (the agent exploded).
  - per-layer geometry-type matches the layer name (no Lines or
    Polygons in the points layer, etc.).
  - per-layer feature count within ±5 %.
  - summed feature count across all three layers within ±10 % of the
    reference.
  - site_id populated on every feature of every layer.
  - site_id Jaccard ≥ 0.9 across the union of all three layers.
  - polygons-layer geometry IoU ≥ 0.9 (unioned per layer).
  - points-layer per-site geometry agreement (≥ 95 % within 1 m).
  - lines-layer per-site Hausdorff agreement (≥ 95 % within 1 m).
  - `crs_is_canonical` — every layer's declared CRS is EPSG:22992.
  - `crs_in_meaningful_set` — every layer's declared CRS is in
    {EPSG:22992, EPSG:32636}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pyogrio
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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "heritage.gpkg"
OUTPUT_NAME = "heritage.gpkg"

EXPECTED_LAYERS = ("points", "lines", "polygons")
LAYER_GEOM_TYPES = {
    "points": {"Point", "MultiPoint"},
    "lines": {"LineString", "MultiLineString"},
    "polygons": {"Polygon", "MultiPolygon"},
}

# Egypt Red Belt (EPSG:22992) is the canonical national projected
# metric CRS for Cairo (cf. author-context's region table) and the
# only one rewarded by the crs_is_canonical subcheck. UTM 36N
# (EPSG:32636) is in the meaningful set as a defensible generic
# alternative — an agent picking 32636 is reasoning generically rather
# than regionally — and the submission is reprojected into Egypt Red
# Belt before any spatial subcheck runs.
CANONICAL_EPSG = 22992
MEANINGFUL_EPSGS = {22992, 32636}
COUNT_TOL = 0.05
TOTAL_COUNT_TOL = 0.10
GEOM_EPS_M = 1.0  # 1 metre — tight enough to catch a swapped CRS or axis swap.
IOU_THRESHOLD = 0.9
JACCARD_THRESHOLD = 0.9


def _safe_read(path: Path, layer: str) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path, layer=layer)
    except Exception:
        return None


def _list_layer_names(path: Path) -> list[str]:
    try:
        info = pyogrio.list_layers(path)
        return [str(row[0]) for row in info]
    except Exception:
        return []


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="fio-l2-cairo-mixedgeom-split")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format / schema validity --------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    layer_names = _list_layer_names(submission_path)
    missing_layers = [name for name in EXPECTED_LAYERS if name not in layer_names]
    if missing_layers:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"GPKG is missing expected layers: {missing_layers} (found {layer_names})",
            )
        )
        return report

    sub_layers: dict[str, gpd.GeoDataFrame] = {}
    for name in EXPECTED_LAYERS:
        gdf = _safe_read(submission_path, name)
        if gdf is None:
            report.gates.append(
                Gate(
                    "format_schema_valid",
                    False,
                    f"could not read GPKG layer '{name}'",
                )
            )
            return report
        sub_layers[name] = gdf

    # CRS soft-grade — every layer must declare some usable CRS. Layers
    # are reprojected into the canonical EPSG:22992 for downstream
    # spatial subchecks regardless of the agent's pick; the original
    # EPSG of each layer is captured so the `crs_is_canonical` and
    # `crs_in_meaningful_set` subchecks below can grade the
    # regional-vs-generic pick.
    sub_layer_epsgs: dict[str, int | None] = {}
    sub_layer_canonical: dict[str, bool] = {}
    sub_layer_meaningful: dict[str, bool] = {}
    for name in EXPECTED_LAYERS:
        crs_res = grade_crs_soft(
            sub_layers[name],
            MEANINGFUL_EPSGS,
            CANONICAL_EPSG,
            treat_none_as_wgs84=False,
        )
        sub_layer_epsgs[name] = crs_res.original_epsg
        sub_layer_canonical[name] = crs_res.is_canonical
        sub_layer_meaningful[name] = crs_res.in_meaningful_set
        if not crs_res.gate_ok:
            report.gates.append(
                Gate(
                    "format_schema_valid",
                    False,
                    f"layer '{name}': {crs_res.gate_reason}",
                )
            )
            return report
        sub_layers[name] = crs_res.normalized

    # site_id column present on every layer.
    for name, gdf in sub_layers.items():
        if "site_id" not in gdf.columns:
            report.gates.append(
                Gate(
                    "format_schema_valid",
                    False,
                    f"layer '{name}' is missing the required 'site_id' column",
                )
            )
            return report

    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref_layers = {name: gpd.read_file(REFERENCE_OUT, layer=name) for name in EXPECTED_LAYERS}

    # Per-layer geometry-type matches the layer name.
    for name, gdf in sub_layers.items():
        types = set(gdf.geometry.geom_type.dropna().unique())
        type_ok = bool(types) and types.issubset(LAYER_GEOM_TYPES[name])
        report.subchecks.append(
            Subcheck(
                f"{name}_geometry_type",
                type_ok,
                detail=(
                    f"layer '{name}' geometry types {sorted(types)} "
                    f"(expected subset of {sorted(LAYER_GEOM_TYPES[name])})"
                ),
            )
        )

    # Summed feature count across all three layers within ±10 %.
    n_sub_total = sum(len(g) for g in sub_layers.values())
    n_ref_total = sum(len(g) for g in ref_layers.values())
    total_count_ok = (
        abs(n_sub_total - n_ref_total) / max(n_sub_total, n_ref_total)
        <= TOTAL_COUNT_TOL
        if max(n_sub_total, n_ref_total)
        else True
    )
    report.subchecks.append(
        Subcheck(
            "total_count_within_tolerance",
            total_count_ok,
            detail=(
                f"summed feature count {n_sub_total} vs reference "
                f"{n_ref_total} (±{int(TOTAL_COUNT_TOL * 100)} %)"
            ),
            weight=1.0,
        )
    )

    # 1. polygons layer: no MultiPolygon.
    poly_types = set(sub_layers["polygons"].geometry.geom_type.dropna().unique())
    n_multi = int(
        (sub_layers["polygons"].geometry.geom_type == "MultiPolygon").sum()
    )
    singletons_ok = "MultiPolygon" not in poly_types
    report.subchecks.append(
        Subcheck(
            "polygons_singletons_only",
            singletons_ok,
            detail=(
                f"{n_multi} MultiPolygon features in polygons layer "
                f"(expected 0 — multi-parts must be exploded)"
            ),
            weight=4.0,
        )
    )

    # 2 / 3 / 4. Per-layer feature count within tolerance. The polygons
    # count is the co-detector of the central explode skill (15 exploded
    # vs 10 unexploded is 33 % off) and carries the highest weight; the
    # points/lines counts are routine stratification sanity and stay at 1.
    count_weights = {"points": 1.0, "lines": 1.0, "polygons": 4.0}
    for name in EXPECTED_LAYERS:
        n_sub = len(sub_layers[name])
        n_ref = len(ref_layers[name])
        ok = count_within_tolerance(n_sub, n_ref, pct=COUNT_TOL)
        report.subchecks.append(
            Subcheck(
                f"{name}_count_within_tolerance",
                ok,
                detail=f"submission {n_sub} features vs reference {n_ref} (±{int(COUNT_TOL * 100)}%)",
                weight=count_weights[name],
            )
        )

    # 5. site_id populated everywhere.
    populated_problems: list[str] = []
    for name in EXPECTED_LAYERS:
        col = sub_layers[name]["site_id"]
        n_total = len(col)
        n_pop = int(col.notna().sum())
        if hasattr(col, "astype"):
            n_pop_str = int((col.fillna("").astype(str).str.strip().str.len() > 0).sum())
        else:
            n_pop_str = n_pop
        if n_pop_str != n_total:
            populated_problems.append(
                f"{name}: {n_pop_str}/{n_total} populated"
            )
    pop_ok = not populated_problems
    report.subchecks.append(
        Subcheck(
            "site_id_populated",
            pop_ok,
            detail=(
                "all features carry a non-empty site_id"
                if pop_ok
                else "; ".join(populated_problems)
            ),
        )
    )

    # 6. site_id Jaccard across union of all three layers.
    def _ids(layers: dict[str, gpd.GeoDataFrame]) -> set[str]:
        out: set[str] = set()
        for g in layers.values():
            out |= set(g["site_id"].dropna().astype(str).tolist())
        return out

    sub_ids = _ids(sub_layers)
    ref_ids = _ids(ref_layers)
    jacc = jaccard_similarity_set(sub_ids, ref_ids)
    report.subchecks.append(
        Subcheck(
            "site_id_jaccard_union",
            jacc >= JACCARD_THRESHOLD,
            detail=f"site_id Jaccard {jacc:.4f} (threshold {JACCARD_THRESHOLD})",
            weight=3.0,
        )
    )

    # 7. polygons-layer geometry IoU.
    sub_polys_geom = unary_union(sub_layers["polygons"].geometry.tolist())
    ref_polys_geom = unary_union(ref_layers["polygons"].geometry.tolist())
    poly_iou = iou_with_tolerance(sub_polys_geom, ref_polys_geom, eps=0.0)
    report.subchecks.append(
        Subcheck(
            "polygons_geometry_iou",
            poly_iou >= IOU_THRESHOLD,
            detail=f"polygons layer IoU {poly_iou:.4f} (threshold {IOU_THRESHOLD})",
            weight=3.0,
        )
    )

    # 8. points-layer per-site geometry agreement.
    sub_pts = sub_layers["points"]
    ref_pts = ref_layers["points"]
    if "feature_kind" in sub_pts.columns and "feature_kind" in ref_pts.columns:
        sub_key = list(zip(sub_pts["site_id"].astype(str), sub_pts["feature_kind"].astype(str)))
        ref_key = list(zip(ref_pts["site_id"].astype(str), ref_pts["feature_kind"].astype(str)))
        sub_map = {k: g for k, g in zip(sub_key, sub_pts.geometry)}
        ref_map = {k: g for k, g in zip(ref_key, ref_pts.geometry)}
        common = sorted(set(sub_map.keys()) & set(ref_map.keys()))
    else:
        # Fall back to site_id alone — keeps the subcheck running, but
        # less discriminating. The agent should preserve feature_kind.
        sub_map = {sid: g for sid, g in zip(sub_pts["site_id"].astype(str), sub_pts.geometry)}
        ref_map = {sid: g for sid, g in zip(ref_pts["site_id"].astype(str), ref_pts.geometry)}
        common = sorted(set(sub_map.keys()) & set(ref_map.keys()))

    if common:
        match = 0
        for k in common:
            sg, rg = sub_map[k], ref_map[k]
            if sg is None or rg is None:
                continue
            if abs(sg.x - rg.x) <= GEOM_EPS_M and abs(sg.y - rg.y) <= GEOM_EPS_M:
                match += 1
        rate = match / len(common)
    else:
        match, rate = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "points_geometry_per_site",
            rate >= 0.95,
            detail=f"{match}/{len(common)} points within {GEOM_EPS_M:.0f} m of reference",
            weight=3.0,
        )
    )

    # 9. lines per-site Hausdorff agreement.
    sub_ln = sub_layers["lines"]
    ref_ln = ref_layers["lines"]
    if "feature_kind" in sub_ln.columns and "feature_kind" in ref_ln.columns:
        sub_lk = list(zip(sub_ln["site_id"].astype(str), sub_ln["feature_kind"].astype(str)))
        ref_lk = list(zip(ref_ln["site_id"].astype(str), ref_ln["feature_kind"].astype(str)))
    else:
        sub_lk = list(sub_ln["site_id"].astype(str))
        ref_lk = list(ref_ln["site_id"].astype(str))
    sub_lmap = {k: g for k, g in zip(sub_lk, sub_ln.geometry)}
    ref_lmap = {k: g for k, g in zip(ref_lk, ref_ln.geometry)}
    common_lines = sorted(set(sub_lmap.keys()) & set(ref_lmap.keys()))
    if common_lines:
        match_l = 0
        for k in common_lines:
            sg, rg = sub_lmap[k], ref_lmap[k]
            if sg is None or rg is None or sg.is_empty or rg.is_empty:
                continue
            if sg.hausdorff_distance(rg) <= GEOM_EPS_M:
                match_l += 1
        rate_l = match_l / len(common_lines)
    else:
        match_l, rate_l = 0, 0.0
    report.subchecks.append(
        Subcheck(
            "lines_geometry_per_site",
            rate_l >= 0.95,
            detail=(
                f"{match_l}/{len(common_lines)} lines with Hausdorff distance "
                f"≤ {GEOM_EPS_M:.0f} m"
            ),
            weight=3.0,
        )
    )

    # Consolidated per-task CRS subchecks across all layers — gate
    # already enforced "some usable CRS"; here we grade canonical vs
    # meaningful regional alternative.
    canonical_ok = all(sub_layer_canonical.values())
    meaningful_ok = all(sub_layer_meaningful.values())
    layer_crs_summary = ", ".join(
        f"{name}=EPSG:{sub_layer_epsgs[name]}" for name in EXPECTED_LAYERS
    )
    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            canonical_ok,
            detail=(
                f"layer CRS picks: {layer_crs_summary}; "
                f"canonical EPSG:{CANONICAL_EPSG}"
            ),
            weight=4.0,
        )
    )
    report.subchecks.append(
        Subcheck(
            "crs_in_meaningful_set",
            meaningful_ok,
            detail=(
                f"layer CRS picks: {layer_crs_summary}; "
                f"meaningful set {sorted(MEANINGFUL_EPSGS)}"
            ),
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
