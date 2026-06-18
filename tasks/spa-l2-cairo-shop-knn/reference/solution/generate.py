"""Reference solution for spa-l2-cairo-shop-knn.

Reads the bundled `cairo_retail.gpkg` (shops + anchors layers, both
EPSG:22992) and emits `market_neighbourhoods.json` per the persona's
schema.

Pipeline:
  1. Read both layers; normalise anchor names (strip + collapse
     whitespace + casefold).
  2. Map shop `raw_name` to a canonical `normalised_name`. Known chain
     variants collapse to a single canonical label per chain (taken
     from CHAIN_VARIANTS, lowercase). Non-chain rows fall back to
     casefold + whitespace-strip — this leaves "Local Shop NNNNN"
     style filler unique-per-row.
  3. For each anchor, compute Euclidean distance (metres) to all
     shops. Take the 5 closest, ties broken by shop_id.
  4. For each anchor, compute distance to every other anchor; take
     the 3 closest siblings, ties broken by anchor_id.
  5. Build the 5 × 3 distance matrix between the 5 knn shops and the
     3 sibling anchors.
  6. Serialise JSON, anchors sorted by anchor_id, knn rows in distance
     order, sibling columns in distance order. Distances rounded to
     3 decimals (mm precision) so two runs match exactly.

Determinism:
  - Both layers ship sorted by their stable ids (`shop_id`, `anchor_id`).
  - All sort keys are deterministic.
  - JSON written with `sort_keys=False`, `indent=2`, fixed key order.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
INPUT_GPKG = TASK_DIR / "inputs" / "cairo_retail.gpkg"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "market_neighbourhoods.json"

K_NN = 5
N_SIBLINGS = 3
WITHIN_M = 1000.0
DIST_PRECISION = 3  # decimals (mm)

# Canonical chain map: every variant string → a canonical lowercase
# chain label. Mirrors data/_prepare_input.py CHAIN_VARIANTS exactly.
CHAIN_VARIANTS: dict[str, list[str]] = {
    "carrefour": ["Carrefour", "carrefour", "Carrefour Egypt", "كارفور"],
    "metro": ["Metro Market", "metro", "Metro Markets", "مترو"],
    "spinneys": ["Spinneys", "spinneys cairo", "Spineys", "سبينيز"],
    "hyperone": ["HyperOne", "Hyper One", "hyperone", "هايبر وان"],
    "oscar": ["Oscar", "Oscar Grand Stores", "OSCAR", "اوسكار"],
    "seoudi": ["Seoudi", "Seoudi Market", "seoudi supermarket", "سعودي"],
    "kheir_zaman": ["Kheir Zaman", "kheir zaman", "Khair Zaman", "خير زمان"],
    "abu_zekry": ["Abu Zekry", "abou zekry", "Abu Zikri", "أبو زكري"],
}
VARIANT_TO_CANON: dict[str, str] = {
    v: canon for canon, variants in CHAIN_VARIANTS.items() for v in variants
}


def _normalise_anchor_name(s: str) -> str:
    s = unicodedata.normalize("NFC", s).strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s


def _normalise_shop_name(raw: str) -> str:
    raw = unicodedata.normalize("NFC", raw).strip()
    if raw in VARIANT_TO_CANON:
        return VARIANT_TO_CANON[raw]
    return re.sub(r"\s+", " ", raw.casefold())


def _round(d: float) -> float:
    return round(float(d), DIST_PRECISION)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    shops = gpd.read_file(INPUT_GPKG, layer="shops")
    anchors = gpd.read_file(INPUT_GPKG, layer="anchors")
    assert shops.crs and shops.crs.to_epsg() == 22992
    assert anchors.crs and anchors.crs.to_epsg() == 22992

    shops = shops.sort_values("shop_id", kind="stable").reset_index(drop=True)
    anchors = anchors.sort_values("anchor_id", kind="stable").reset_index(drop=True)

    shops["normalised_name"] = shops["raw_name"].map(_normalise_shop_name)
    anchors["anchor_name_normalised"] = anchors["anchor_name"].map(
        _normalise_anchor_name
    )

    shop_xy = np.array([(g.x, g.y) for g in shops.geometry], dtype=float)
    anchor_xy = np.array([(g.x, g.y) for g in anchors.geometry], dtype=float)
    shop_ids = shops["shop_id"].to_numpy()
    shop_norms = shops["normalised_name"].to_numpy()
    anchor_ids = anchors["anchor_id"].to_numpy()
    anchor_norms = anchors["anchor_name_normalised"].to_numpy()

    records = []
    for i in range(len(anchors)):
        ax, ay = anchor_xy[i]

        # Shop distances.
        d_shops = np.hypot(shop_xy[:, 0] - ax, shop_xy[:, 1] - ay)
        # Sort by (distance, shop_id) — np.lexsort with primary key last.
        order = np.lexsort((shop_ids, d_shops))
        knn_idx = order[:K_NN]

        # Sibling-anchor distances (exclude self).
        d_anchors = np.hypot(
            anchor_xy[:, 0] - ax, anchor_xy[:, 1] - ay
        )
        d_anchors[i] = np.inf
        sib_order = np.lexsort((anchor_ids, d_anchors))
        sib_idx = sib_order[:N_SIBLINGS]

        # Build knn list.
        knn_rows = []
        for s_idx in knn_idx:
            d = float(d_shops[s_idx])
            knn_rows.append(
                {
                    "shop_id": str(shop_ids[s_idx]),
                    "normalised_name": str(shop_norms[s_idx]),
                    "distance_m": _round(d),
                    "within_1km": bool(d <= WITHIN_M),
                }
            )

        # 5×3 distance matrix.
        sib_xy = anchor_xy[sib_idx]
        knn_xy = shop_xy[knn_idx]
        # rows=knn (5), cols=siblings (3)
        diff = knn_xy[:, None, :] - sib_xy[None, :, :]
        matrix = np.hypot(diff[..., 0], diff[..., 1])
        matrix_rounded = [
            [_round(matrix[r, c]) for c in range(N_SIBLINGS)]
            for r in range(K_NN)
        ]

        records.append(
            {
                "anchor_id": str(anchor_ids[i]),
                "anchor_name_normalised": str(anchor_norms[i]),
                "knn": knn_rows,
                "full_distance_matrix_m": matrix_rounded,
            }
        )

    if OUT.exists():
        OUT.unlink()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    n_chain_rows = sum(1 for n in shop_norms if n in CHAIN_VARIANTS)
    print(f"Read {len(shops)} shops, {len(anchors)} anchors")
    print(f"Distinct shop normalised_name values: {len(set(shop_norms))}")
    print(f"Chain rows (matched canonical): {n_chain_rows}")
    print(f"Wrote {len(records)} anchor records → {OUT}")
    sample_knn = records[0]["knn"][0]
    print(f"Sample knn[0] for {records[0]['anchor_id']}: {sample_knn}")


if __name__ == "__main__":
    main()
