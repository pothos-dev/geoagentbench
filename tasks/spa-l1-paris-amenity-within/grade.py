"""Grader for spa-l1-paris-amenity-within.

One hard gate then six binary subchecks. The task is *spatial join
(within) of 85 Paris amenity Points against 20 arrondissement
Polygons*, with one tabular CSV row per amenity carrying the integer
arrondissement number. The grader's job is to distinguish:

  - a wrong-format / missing-column solution → gate fails, score 0.
  - a *join-correct, suffix-not-stripped* solution (the agent left
    ``arrondissement_number`` as ``"1er"``, ``"20e"``, etc., instead of
    coercing to an integer — the persona's explicit gotcha) → gate
    passes, the integer-shape and per-row number subchecks fail,
    partial score.
  - a *join-correct, name-column-misused* solution (the agent put the
    arrondissement Overture *id* into ``arrondissement_name`` — a
    common confusion when both layers carry an ``id`` and a ``name``)
    → gate passes, only the name subcheck fails, higher partial score.
  - a fully-correct solution → 1.0.

Join key: rows align on ``osm_id`` (preserved verbatim from the input
amenity layer). The grader does not attempt a geometry-based fallback —
the output is non-spatial CSV.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    jaccard_similarity_set,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "amenity_to_arrondissement.csv"
OUTPUT_NAME = "amenity_to_arrondissement.csv"

REQUIRED_COLS = (
    "osm_id",
    "amenity_class",
    "arrondissement_number",
    "arrondissement_name",
)
PER_ROW_PASS_RATE = 0.95


def _read_csv(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _coerce_int(value: object) -> int | None:
    """Best-effort int coercion. Returns None if value can't become an int.

    Accepts plain ints, int-valued floats (e.g. ``20.0``), and bare-digit
    strings (``"20"``). Rejects French ordinals (``"20e"``, ``"1er"``)
    and any other non-numeric junk — that's the persona's explicit
    gotcha and the grader should not paper over it.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if pd.isna(value):
            return None
        if float(value).is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            f = float(stripped)
        except ValueError:
            return None
        if not f.is_integer():
            return None
        return int(f)
    return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="spa-l1-paris-amenity-within")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format/schema validity -----------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing output file: {OUTPUT_NAME}",
            )
        )
        return report

    sub = _read_csv(submission_path)
    if sub is None:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "could not parse file as CSV",
            )
        )
        return report

    missing = [c for c in REQUIRED_COLS if c not in sub.columns]
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing required column(s): {missing}",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    ref = pd.read_csv(REFERENCE_OUT)

    # ---- Subchecks ------------------------------------------------------

    # 1. Exact count parity. L1 deterministic — every correct solution
    #    produces exactly len(ref) rows.
    count_exact = len(sub) == len(ref)
    report.subchecks.append(
        Subcheck(
            "exact_count_match",
            count_exact,
            detail=f"submission has {len(sub)} rows; reference has {len(ref)}",
            weight=3.0,
        )
    )

    # 2. osm_id set Jaccard ≥ 0.95. Catches solutions that dropped a
    #    chunk of amenities or fabricated extras.
    sub_ids = sub["osm_id"].astype(str).tolist()
    ref_ids = ref["osm_id"].astype(str).tolist()
    set_jaccard = jaccard_similarity_set(sub_ids, ref_ids)
    report.subchecks.append(
        Subcheck(
            "osm_id_set_jaccard",
            set_jaccard >= 0.95,
            detail=f"osm_id-set Jaccard {set_jaccard:.4f}",
            weight=3.0,
        )
    )

    # 3. ``arrondissement_number`` is plain-integer-valued in 1..20.
    #    The persona's explicit gotcha — the downstream join wants
    #    ``20``, not ``"20e"`` and not ``"Paris 20e Arrondissement"``.
    int_pass = 0
    int_total = 0
    for v in sub["arrondissement_number"].tolist():
        int_total += 1
        coerced = _coerce_int(v)
        if coerced is not None and 1 <= coerced <= 20:
            int_pass += 1
    int_rate = int_pass / int_total if int_total else 0.0
    report.subchecks.append(
        Subcheck(
            "arrondissement_number_is_integer_1_to_20",
            int_rate >= PER_ROW_PASS_RATE,
            detail=(
                f"{int_pass}/{int_total} rows have an integer "
                f"arrondissement_number in 1..20"
            ),
            # Attribute *format* shape (the persona's ordinal gotcha), not
            # the within-join itself: a join-correct solution that left
            # "20e" still placed every amenity in the right arrondissement.
            # Cosmetic/recoverable -> lowest weight.
            weight=1.0,
        )
    )

    # ---- Per-row attribute match (joined on osm_id) ----
    sub_keys = sub["osm_id"].astype(str)
    ref_keys = ref["osm_id"].astype(str)
    common = sorted(set(sub_keys) & set(ref_keys))

    sub_indexed = sub.set_index(sub_keys)
    ref_indexed = ref.set_index(ref_keys)

    # 4. ``arrondissement_number`` matches the reference on each row.
    #    Coerces both sides to int before comparing so a submission that
    #    wrote ``20`` as a string ("20") still matches; a submission that
    #    wrote ``"20e"`` or any non-int does not.
    num_pass = 0
    num_total = 0
    for k in common:
        sg = sub_indexed.loc[k, "arrondissement_number"]
        rg = ref_indexed.loc[k, "arrondissement_number"]
        if isinstance(sg, pd.Series) or isinstance(rg, pd.Series):
            num_total += 1
            continue
        num_total += 1
        sg_int = _coerce_int(sg)
        rg_int = _coerce_int(rg)
        if sg_int is not None and rg_int is not None and sg_int == rg_int:
            num_pass += 1
    num_rate = num_pass / num_total if num_total else 0.0
    report.subchecks.append(
        Subcheck(
            "arrondissement_number_per_row_match",
            num_rate >= PER_ROW_PASS_RATE,
            detail=(
                f"{num_pass}/{num_total} matched-id rows agree on "
                f"integer arrondissement_number"
            ),
            # THE central skill: did the within-join place each amenity in
            # the correct arrondissement? This compares the joined number
            # per row after int-coercion, so a wrong *containment* (not
            # just a format slip) fails here. Highest weight.
            weight=3.0,
        )
    )

    # 5. ``arrondissement_name`` matches the reference on each row.
    #    String exact match after strip — the reference name is the
    #    Overture ``names.primary`` value verbatim.
    name_pass = 0
    name_total = 0
    for k in common:
        sg = sub_indexed.loc[k, "arrondissement_name"]
        rg = ref_indexed.loc[k, "arrondissement_name"]
        if isinstance(sg, pd.Series) or isinstance(rg, pd.Series):
            name_total += 1
            continue
        name_total += 1
        if str(sg).strip() == str(rg).strip():
            name_pass += 1
    name_rate = name_pass / name_total if name_total else 0.0
    report.subchecks.append(
        Subcheck(
            "arrondissement_name_per_row_match",
            name_rate >= PER_ROW_PASS_RATE,
            detail=(
                f"{name_pass}/{name_total} matched-id rows agree on "
                f"arrondissement_name"
            ),
            # Also evidence of correct containment per row, but largely
            # redundant with the number-per-row check; its distinct
            # signal is the id-vs-name projection confusion, which is a
            # column-pick slip rather than a join error. Mid weight.
            weight=2.0,
        )
    )

    # 6. ``amenity_class`` carried through unchanged from the input.
    cls_pass = 0
    cls_total = 0
    for k in common:
        sg = sub_indexed.loc[k, "amenity_class"]
        rg = ref_indexed.loc[k, "amenity_class"]
        if isinstance(sg, pd.Series) or isinstance(rg, pd.Series):
            cls_total += 1
            continue
        cls_total += 1
        if str(sg).strip() == str(rg).strip():
            cls_pass += 1
    cls_rate = cls_pass / cls_total if cls_total else 0.0
    report.subchecks.append(
        Subcheck(
            "amenity_class_per_row_match",
            cls_rate >= PER_ROW_PASS_RATE,
            detail=(
                f"{cls_pass}/{cls_total} matched-id rows agree on "
                f"amenity_class"
            ),
            # Pure input passthrough column - no spatial reasoning, no
            # parsing. A mismatch here is a clerical carry-through slip.
            # Cosmetic -> lowest weight.
            weight=1.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
