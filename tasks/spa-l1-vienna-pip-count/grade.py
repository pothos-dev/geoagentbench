"""Grader for spa-l1-vienna-pip-count.

One hard gate then five binary subchecks. The task is *point-in-polygon
count of 49 monitoring stations against 23 Vienna Bezirk polygons*,
with one tabular CSV row per Bezirk carrying the station count. The
grader's job is to distinguish:

  - wrong-format / missing-column → gate fails, score 0.
  - inner-join solution (the agent grouped stations by their containing
    Bezirk but never left-joined the result back onto the full Bezirk
    list, so the four zero-count Bezirke disappear) → 19 rows. Gate
    passes; ``exact_count_match`` and ``district_code_set_complete``
    fail; the per-row attribute and total subchecks still pass on the
    19 districts present. Partial score around 0.6.
  - wrong-attribute solution (the agent did the join correctly,
    produced 23 rows, but pulled the OSM relation id into the
    ``district_name`` column instead of the human-readable name —
    confusing the two columns of the input district layer) → 5/5
    except per-row name match. Partial score around 0.8.
  - fully-correct solution → 1.0.

Join key: rows align on ``district_code`` (1..23). The grader coerces
both sides to int before joining so a submission that wrote
``district_code`` as ``"01"`` (zero-padded string), ``1.0`` (float), or
``1`` still aligns. A submission that wrote a totally different code
scheme (e.g. postal codes 1010, 1020, …) will not align and will
zero-out per-row subchecks — intentional.
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
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "stations_per_district.csv"
OUTPUT_NAME = "stations_per_district.csv"

REQUIRED_COLS = ("district_code", "district_name", "station_count")
PER_ROW_PASS_RATE = 0.95


def _read_csv(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _coerce_int(value: object) -> int | None:
    """Best-effort int coercion. Returns None if value can't become an int.

    Accepts plain ints, int-valued floats (``1.0``), and bare-digit
    strings (``"1"`` or zero-padded ``"01"``). Rejects floats with a
    fractional part and any non-numeric junk.
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
    report = ScoreReport(task_id="spa-l1-vienna-pip-count")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format/schema validity -----------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    sub = _read_csv(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not parse file as CSV")
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

    # 1. Exact count parity. Vienna has exactly 23 Bezirke and the
    #    persona's instruction says zero-count districts must appear,
    #    so a correct solution emits exactly 23 rows. The inner-join
    #    failure mode (drops the four zero-count districts) lands here.
    exact_count = len(sub) == len(ref)
    report.subchecks.append(
        Subcheck(
            "exact_count_match",
            exact_count,
            detail=f"submission has {len(sub)} rows; reference has {len(ref)}",
            weight=3.0,
        )
    )

    # 2. district_code set completeness. The 23 official Vienna Bezirk
    #    numbers (1..23) must all appear. Coerces both sides to int so
    #    "01" / 1 / 1.0 all alias.
    sub_codes = {
        c for c in (_coerce_int(v) for v in sub["district_code"].tolist()) if c is not None
    }
    ref_codes = {int(c) for c in ref["district_code"].tolist()}
    set_jaccard = jaccard_similarity_set(sub_codes, ref_codes)
    set_complete = sub_codes == ref_codes
    report.subchecks.append(
        Subcheck(
            "district_code_set_complete",
            set_complete,
            detail=(
                f"submission codes={sorted(sub_codes)}; "
                f"reference={sorted(ref_codes)}; jaccard={set_jaccard:.4f}"
            ),
            weight=3.0,
        )
    )

    # ---- Per-row attribute match (joined on district_code) ----
    sub_int_codes = sub["district_code"].map(_coerce_int)
    sub_keyed = sub.assign(_int_code=sub_int_codes).dropna(subset=["_int_code"])
    sub_keyed["_int_code"] = sub_keyed["_int_code"].astype(int)
    ref_keyed = ref.assign(_int_code=ref["district_code"].astype(int))

    common = sorted(set(sub_keyed["_int_code"]) & set(ref_keyed["_int_code"]))
    sub_indexed = sub_keyed.set_index("_int_code")
    ref_indexed = ref_keyed.set_index("_int_code")

    # 3. district_name per-row match. String exact-after-strip — the
    #    reference name is the German Bezirk name verbatim ("Innere
    #    Stadt", "Währing", "Landstraße"). The wrong-attribute broken
    #    (district_name set to the OSM relation id) collapses this.
    name_pass = 0
    name_total = 0
    for k in common:
        sg = sub_indexed.loc[k, "district_name"]
        rg = ref_indexed.loc[k, "district_name"]
        if isinstance(sg, pd.Series) or isinstance(rg, pd.Series):
            name_total += 1
            continue
        name_total += 1
        if str(sg).strip() == str(rg).strip():
            name_pass += 1
    name_rate = name_pass / name_total if name_total else 0.0
    report.subchecks.append(
        Subcheck(
            "district_name_per_row_match",
            name_rate >= PER_ROW_PASS_RATE,
            detail=(
                f"{name_pass}/{name_total} matched-code rows agree on district_name"
            ),
            # Cosmetic / attribute-label check: only the human-readable
            # display column. When this is the *sole* failure the join,
            # per-district counts, and total are all correct (the
            # name_used_id broken), so it is the least central skill —
            # weighted lowest. The four count/join checks carry weight
            # 3.0 because they detect the central PIP-count skill.
            weight=1.0,
        )
    )

    # 4. station_count per-row match. Coerces both sides to int so a
    #    submission that wrote ``2.0`` or ``"2"`` matches ``2``.
    cnt_pass = 0
    cnt_total = 0
    for k in common:
        sg = sub_indexed.loc[k, "station_count"]
        rg = ref_indexed.loc[k, "station_count"]
        if isinstance(sg, pd.Series) or isinstance(rg, pd.Series):
            cnt_total += 1
            continue
        cnt_total += 1
        sg_int = _coerce_int(sg)
        rg_int = _coerce_int(rg)
        if sg_int is not None and rg_int is not None and sg_int == rg_int:
            cnt_pass += 1
    cnt_rate = cnt_pass / cnt_total if cnt_total else 0.0
    report.subchecks.append(
        Subcheck(
            "station_count_per_row_match",
            cnt_rate >= PER_ROW_PASS_RATE,
            detail=(
                f"{cnt_pass}/{cnt_total} matched-code rows agree on station_count"
            ),
            weight=3.0,
        )
    )

    # 5. station_count total. The sum across all rows must equal the
    #    reference sum (49 — every station inside exactly one Bezirk).
    #    Picks up unit / scaling errors and double-counted boundary
    #    points. NOTE: an inner-join solution still passes this — the
    #    49 stations all live in the 19 non-zero districts, so the sum
    #    is preserved. That's by design: the inner-join failure is
    #    diagnosed by subchecks 1+2, not by this subcheck.
    sub_int_sum = sum(
        v if v is not None else 0
        for v in (_coerce_int(x) for x in sub["station_count"].tolist())
    )
    ref_sum = int(ref["station_count"].sum())
    total_match = sub_int_sum == ref_sum
    report.subchecks.append(
        Subcheck(
            "station_count_total_match",
            total_match,
            detail=f"submission total {sub_int_sum}; reference total {ref_sum}",
            weight=3.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
