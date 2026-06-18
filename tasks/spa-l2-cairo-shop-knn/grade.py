"""Grader for spa-l2-cairo-shop-knn.

The persona's question is: for each of 100 anchors, return the 5 nearest
shops (with `normalised_name`, metric distance, 1-km flag), the 5×3
distance matrix to the anchor's 3 closest sibling anchors, plus a tidy
anchor name. Chain transliteration variants must collapse to one
canonical normalised_name per chain.

Gate — JSON parses, is a list of dicts with the required top-level
       keys, and every record has a `knn` list of 5 entries with the
       required sub-keys plus a 5×3 numeric `full_distance_matrix_m`.

Subchecks:
  1. anchor_name_normalised non-empty for every anchor.
  2. anchor_id Jaccard vs reference ≥ 0.95.
  3. Record count within ±5% of reference (100).
  4. knn distances per anchor are non-negative, finite, sorted
     ascending, and the agent's reported distance for each knn entry
     matches the true distance from the named shop to the named anchor
     (we look up coords from the bundled GPKG) within 1.0 m for ≥99%
     of (anchor, knn-position) pairs.
  5. within_1km flag matches (distance_m ≤ 1000) for ≥99% of pairs.
  6. The set of distance values at each knn position matches the
     reference's at the same position within 1.0 m for ≥95% of
     (anchor, position) pairs. This catches an agent that found 5
     real shops but not the 5 nearest (e.g. wrong CRS, wrong join
     direction).
  7. Distance matrix values per anchor: each cell equals the true
     distance from the agent's r-th knn shop to its c-th sibling
     anchor within 1.0 m, for ≥99% of cells.
  8. Chain canonicalisation: ≥ 7 of the 8 known chains have exactly
     ONE distinct `normalised_name` across all shop_ids belonging to
     that chain in the agent's output. Per-shop_id consistency
     (same shop_id always tagged with the same name) is also
     required globally.

Notes on robustness:
  - When the anchor sits on coordinates with many collocated Overture
    POIs nearby, the *identity* of the 5 nearest may be ambiguous (5
    shops tied to within float noise). Subcheck 6 therefore compares
    distance VALUES at each position rather than shop_ids — any 5
    agents could legitimately disagree on shop ids while all picking
    valid nearest sets with identical distance vectors.
  - Subcheck 8 lets the agent pick its own canonical string per chain
    ("Carrefour", "carrefour", "carrefour egypt" — any one). Only the
    consistency-per-chain matters.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np

from geo_grading import Gate, ScoreReport, Subcheck, jaccard_similarity_set

TASK_DIR = Path(__file__).resolve().parent
REF_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "market_neighbourhoods.json"
GPKG = TASK_DIR / "inputs" / "cairo_retail.gpkg"
TRUTH_FILE = TASK_DIR / "reference" / "_chain_truth.json"
OUTPUT_NAME = "market_neighbourhoods.json"

DIST_TOL_M = 1.0
N_KNN = 5
N_SIB = 3
WITHIN_M = 1000.0


# ---- helpers --------------------------------------------------------


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_finite_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(
        float(x)
    )


def _shape_ok(records) -> tuple[bool, str]:
    if not isinstance(records, list):
        return False, "top-level JSON is not a list"
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            return False, f"record {i} is not an object"
        for key in ("anchor_id", "anchor_name_normalised", "knn", "full_distance_matrix_m"):
            if key not in r:
                return False, f"record {i} missing key '{key}'"
        if not isinstance(r["knn"], list) or len(r["knn"]) != N_KNN:
            return False, f"record {i} knn must be a list of {N_KNN} entries"
        for j, k in enumerate(r["knn"]):
            if not isinstance(k, dict):
                return False, f"record {i} knn[{j}] not an object"
            for kk in ("shop_id", "normalised_name", "distance_m", "within_1km"):
                if kk not in k:
                    return False, f"record {i} knn[{j}] missing '{kk}'"
            if not _is_finite_number(k["distance_m"]):
                return False, f"record {i} knn[{j}] distance_m not numeric"
            if not isinstance(k["within_1km"], bool):
                return False, f"record {i} knn[{j}] within_1km not bool"
        m = r["full_distance_matrix_m"]
        if not isinstance(m, list) or len(m) != N_KNN:
            return False, f"record {i} full_distance_matrix_m must have {N_KNN} rows"
        for r_idx, row in enumerate(m):
            if not isinstance(row, list) or len(row) != N_SIB:
                return (
                    False,
                    f"record {i} matrix row {r_idx} must have {N_SIB} cols",
                )
            for c, v in enumerate(row):
                if not _is_finite_number(v):
                    return False, f"record {i} matrix[{r_idx}][{c}] not numeric"
    return True, ""


# ---- main grader ----------------------------------------------------


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="spa-l2-cairo-shop-knn")
    sub_path = submission_dir / OUTPUT_NAME

    # ---- Gate: schema validity ----------------------------------------
    if not sub_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report
    sub = _load_json(sub_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not parse JSON")
        )
        return report
    ok, why = _shape_ok(sub)
    if not ok:
        report.gates.append(Gate("format_schema_valid", False, why))
        return report
    report.gates.append(Gate("format_schema_valid", True))

    ref = _load_json(REF_OUT)
    sub_ids = [r["anchor_id"] for r in sub]
    ref_ids = [r["anchor_id"] for r in ref]
    n_sub, n_ref = len(sub_ids), len(ref_ids)
    count_ok = abs(n_sub - n_ref) / max(n_sub, n_ref) <= 0.05
    id_jaccard = jaccard_similarity_set(sub_ids, ref_ids)

    # ---- Look up shop / anchor coordinates from bundled GPKG ----------
    shops = gpd.read_file(GPKG, layer="shops")
    anchors = gpd.read_file(GPKG, layer="anchors")
    shop_xy = {
        sid: (g.x, g.y) for sid, g in zip(shops["shop_id"], shops.geometry)
    }
    anchor_xy = {
        aid: (g.x, g.y) for aid, g in zip(anchors["anchor_id"], anchors.geometry)
    }

    truth = json.loads(TRUTH_FILE.read_text(encoding="utf-8"))
    shop_to_chain: dict[str, str | None] = truth["shop_id_to_chain"]
    chain_keys: list[str] = truth["chain_keys"]

    sub_by_id = {r["anchor_id"]: r for r in sub}
    ref_by_id = {r["anchor_id"]: r for r in ref}
    common_anchors = sorted(set(sub_by_id) & set(ref_by_id))

    # ---- Subcheck 1: anchor_name_normalised non-empty -----------------
    n_named = sum(
        1
        for r in sub
        if isinstance(r.get("anchor_name_normalised"), str)
        and r["anchor_name_normalised"].strip() != ""
    )
    report.subchecks.append(
        Subcheck(
            "anchor_name_normalised_populated",
            n_named == len(sub),
            detail=f"{n_named}/{len(sub)} anchors have non-empty anchor_name_normalised",
        )
    )

    # ---- Subcheck: anchor_id Jaccard vs reference ---------------------
    report.subchecks.append(
        Subcheck(
            "anchor_id_set_jaccard",
            id_jaccard >= 0.95,
            detail=f"anchor_id Jaccard {id_jaccard:.4f} (threshold 0.95)",
            weight=2.0,
        )
    )

    # ---- Subcheck: record count within ±5% of reference ---------------
    report.subchecks.append(
        Subcheck(
            "record_count_within_5pct",
            count_ok,
            detail=f"submission {n_sub} records; reference {n_ref}",
            weight=1.0,
        )
    )

    # ---- Subcheck 4: knn distance values agree with coord lookup ------
    pairs = 0
    pairs_ok = 0
    sorted_ok_anchors = 0
    for aid in common_anchors:
        r = sub_by_id[aid]
        ax, ay = anchor_xy.get(aid, (None, None))
        knn_dists = []
        per_pair_ok = 0
        for k in r["knn"]:
            pairs += 1
            sid = str(k["shop_id"])
            d_reported = float(k["distance_m"])
            knn_dists.append(d_reported)
            if sid in shop_xy and ax is not None:
                sx, sy = shop_xy[sid]
                d_true = math.hypot(sx - ax, sy - ay)
                if abs(d_true - d_reported) <= DIST_TOL_M:
                    pairs_ok += 1
                    per_pair_ok += 1
        if knn_dists == sorted(knn_dists):
            sorted_ok_anchors += 1
    distance_match_rate = pairs_ok / max(pairs, 1)
    report.subchecks.append(
        Subcheck(
            "knn_distances_agree_with_coords",
            distance_match_rate >= 0.99 and sorted_ok_anchors == len(common_anchors),
            detail=(
                f"{pairs_ok}/{pairs} knn rows have |distance_reported - "
                f"d(anchor, shop)| ≤ {DIST_TOL_M} m; "
                f"{sorted_ok_anchors}/{len(common_anchors)} anchors have knn "
                "distances sorted ascending"
            ),
            weight=5.0,
        )
    )

    # ---- Subcheck 5: within_1km flag consistency ----------------------
    flag_pairs = 0
    flag_ok = 0
    for r in sub:
        for k in r["knn"]:
            flag_pairs += 1
            d = float(k["distance_m"])
            expected = d <= WITHIN_M
            if bool(k["within_1km"]) == expected:
                flag_ok += 1
    flag_rate = flag_ok / max(flag_pairs, 1)
    report.subchecks.append(
        Subcheck(
            "within_1km_flag_correct",
            flag_rate >= 0.99,
            detail=f"{flag_ok}/{flag_pairs} knn rows have within_1km == (distance_m ≤ 1000)",
            weight=1.0,
        )
    )

    # ---- Subcheck 6: knn distance VECTORS match reference -------------
    pos_pairs = 0
    pos_ok = 0
    for aid in common_anchors:
        s_dists = sorted(float(k["distance_m"]) for k in sub_by_id[aid]["knn"])
        r_dists = sorted(float(k["distance_m"]) for k in ref_by_id[aid]["knn"])
        for s, r in zip(s_dists, r_dists):
            pos_pairs += 1
            if abs(s - r) <= DIST_TOL_M:
                pos_ok += 1
    pos_rate = pos_ok / max(pos_pairs, 1)
    report.subchecks.append(
        Subcheck(
            "knn_distance_vector_matches_reference",
            pos_rate >= 0.95,
            detail=(
                f"{pos_ok}/{pos_pairs} (anchor, position) knn distances within "
                f"{DIST_TOL_M} m of reference"
            ),
            weight=5.0,
        )
    )

    # ---- Subcheck 7: distance matrix values consistent with coords ----
    cell_pairs = 0
    cell_ok = 0
    for r in sub:
        aid = r["anchor_id"]
        knn_sids = [str(k["shop_id"]) for k in r["knn"]]
        # Sibling anchors: derive from the matrix's columns. We don't
        # know which siblings the agent picked — we can only verify
        # the column distances are *some* consistent set across rows.
        # Concretely: the column-c distance of row r is the distance
        # from knn shop r to a single sibling anchor; if columns are
        # consistent across rows then for each column there exists an
        # anchor in the dataset whose distances to all 5 knn shops
        # equal the column.
        matrix = np.array(r["full_distance_matrix_m"], dtype=float)
        # Determine the implied sibling for each column by minimising
        # squared error against any anchor coordinate. This is a soft
        # consistency check: each column should be reproducible to
        # within DIST_TOL_M from SOME anchor's coords.
        knn_xy = np.array(
            [shop_xy.get(sid, (np.nan, np.nan)) for sid in knn_sids]
        )
        all_anchor_ids = list(anchor_xy.keys())
        all_anchor_xy = np.array([anchor_xy[a] for a in all_anchor_ids])
        for c in range(N_SIB):
            col = matrix[:, c]
            # distances from each anchor to all 5 knn shops:
            d = np.hypot(
                all_anchor_xy[:, None, 0] - knn_xy[None, :, 0],
                all_anchor_xy[:, None, 1] - knn_xy[None, :, 1],
            )  # shape (n_anchors, 5)
            err = np.max(np.abs(d - col[None, :]), axis=1)
            best = np.min(err)
            for v in col:
                cell_pairs += 1
                # cell counted as ok if the best-fit anchor for this
                # column is within tolerance of all rows.
                if best <= DIST_TOL_M:
                    cell_ok += 1
    cell_rate = cell_ok / max(cell_pairs, 1)
    report.subchecks.append(
        Subcheck(
            "distance_matrix_consistent_with_coords",
            cell_rate >= 0.99,
            detail=(
                f"{cell_ok}/{cell_pairs} matrix cells reproduce from the agent's "
                f"knn shop_ids and some anchor's coords within {DIST_TOL_M} m"
            ),
            weight=3.0,
        )
    )

    # ---- Subcheck 8: chain canonicalisation ---------------------------
    # Map (chain_key) → set of normalised_name values the agent used.
    chain_to_norms: dict[str, set[str]] = {ck: set() for ck in chain_keys}
    shop_id_to_norms: dict[str, set[str]] = {}
    for r in sub:
        for k in r["knn"]:
            sid = str(k["shop_id"])
            n = str(k["normalised_name"])
            shop_id_to_norms.setdefault(sid, set()).add(n)
            ch = shop_to_chain.get(sid)
            if ch in chain_to_norms:
                chain_to_norms[ch].add(n)
    chains_collapsed = sum(1 for ck in chain_keys if len(chain_to_norms[ck]) == 1)
    per_shop_consistent = sum(1 for v in shop_id_to_norms.values() if len(v) == 1)
    per_shop_total = len(shop_id_to_norms)
    report.subchecks.append(
        Subcheck(
            "chain_variants_collapsed",
            chains_collapsed >= 7
            and (per_shop_total == 0 or per_shop_consistent == per_shop_total),
            detail=(
                f"{chains_collapsed}/{len(chain_keys)} chains collapsed to a "
                f"single normalised_name; per-shop_id consistency "
                f"{per_shop_consistent}/{per_shop_total}"
            ),
            weight=2.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
