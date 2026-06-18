"""Authoring-time helper: build the broken-solution outputs.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l2-cairo-shop-knn/reference/failures/_make_brokens.py

Each broken solution targets a distinct failure class so the grader's
observed scores land in distinct ranges.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
REF = TASK_DIR / "reference" / "solution" / "outputs" / "market_neighbourhoods.json"

WRONG_FORMAT = HERE / "broken_wrong_format" / "outputs" / "market_neighbourhoods.csv"
NO_NORM = HERE / "broken_no_chain_normalisation" / "outputs" / "market_neighbourhoods.json"
WRONG_KNN = HERE / "broken_wrong_knn_set" / "outputs" / "market_neighbourhoods.json"


def _load() -> list:
    return json.loads(REF.read_text(encoding="utf-8"))


def make_wrong_format() -> None:
    """Output as a CSV instead of the required JSON. Gate 1 rejects on
    missing `.json` filename → score 0."""
    WRONG_FORMAT.parent.mkdir(parents=True, exist_ok=True)
    if WRONG_FORMAT.exists():
        WRONG_FORMAT.unlink()
    rows = ["anchor_id,knn0_shop_id,knn0_distance_m"]
    for r in _load():
        k0 = r["knn"][0]
        rows.append(f"{r['anchor_id']},{k0['shop_id']},{k0['distance_m']}")
    WRONG_FORMAT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {WRONG_FORMAT}")


def make_no_chain_normalisation() -> None:
    """Reverts `normalised_name` to a per-shop unique value (the agent
    never collapsed transliterations). Schema, distances, knn order,
    matrix, anchor names — all valid. Only `chain_variants_collapsed`
    fails. Expected: 5/6 ≈ 0.83."""
    data = _load()
    out = copy.deepcopy(data)
    for r in out:
        for k in r["knn"]:
            # Replace every normalised_name with the literal shop_id —
            # guarantees per-shop uniqueness and per-chain divergence.
            k["normalised_name"] = f"raw::{k['shop_id']}"
    NO_NORM.parent.mkdir(parents=True, exist_ok=True)
    if NO_NORM.exists():
        NO_NORM.unlink()
    NO_NORM.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {NO_NORM}")


def make_wrong_knn_set() -> None:
    """For each anchor, pick the LAST 5 shops in the reference's knn
    sorted in REVERSE order and inflate their distances 10×.

    Concretely: keep schema, anchor ids, normalised_name (correct
    canonical form preserved), within_1km flag updated to be
    (distance_m ≤ 1000) so flag-vs-distance is internally consistent
    — but the distances no longer match the actual coords-derived
    distances, and the distance vector no longer matches the
    reference's. Trips:
      - knn_distances_agree_with_coords (distances no longer match
        the named shops' coords).
      - knn_distance_vector_matches_reference (vectors are inflated).
      - distance_matrix_consistent_with_coords (matrix unchanged but
        the per-row column anchor cannot reproduce all 5 inflated
        distances).
    Subchecks 1, 3, 6 still pass. Expected: 3/6 = 0.5.
    """
    data = _load()
    out = copy.deepcopy(data)
    for r in out:
        # Reverse the knn order and scale distances 10×.
        knn = list(reversed(r["knn"]))
        for k in knn:
            k["distance_m"] = round(float(k["distance_m"]) * 10.0, 3)
            k["within_1km"] = bool(k["distance_m"] <= 1000.0)
        r["knn"] = knn
        # Leave full_distance_matrix_m unchanged so subcheck 5 also
        # diverges (now keyed against reversed knn shop ordering).
    WRONG_KNN.parent.mkdir(parents=True, exist_ok=True)
    if WRONG_KNN.exists():
        WRONG_KNN.unlink()
    WRONG_KNN.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {WRONG_KNN}")


if __name__ == "__main__":
    make_wrong_format()
    make_no_chain_normalisation()
    make_wrong_knn_set()
