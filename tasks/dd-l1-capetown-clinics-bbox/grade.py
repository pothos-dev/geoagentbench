"""Grader for dd-l1-capetown-clinics-bbox.

One hard gate (``format_schema_valid``) plus a checklist of binary
subchecks. The task's central skill is *parse a CSV-with-WKT export and
report a small inventory* — total count, overall bbox, and a
count-per-subdistrict roll-up. The grader splits these three
deliverables into independent subchecks (count strict-equality, bbox
componentwise tolerance, subdistrict key set, subdistrict per-key
values, and an internal-consistency check that the sum of subdistrict
counts equals the reported total) so an agent that nails some of the
deliverables but botches one is partially credited. Light coercion is
applied to the submitted values so a wrong-typed field costs one
subcheck rather than collapsing the score.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from geo_grading import Gate, ScoreReport, Subcheck

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "clinic_inventory.json"
OUTPUT_NAME = "clinic_inventory.json"

# Bbox values are reported in degrees (EPSG:4326). 1e-6° ≈ 11 cm at the
# equator, which is far tighter than any rounding the agent would
# legitimately apply but loose enough to absorb float printer differences
# (e.g. an agent that round-trips through numpy float64 vs. Python floats).
BBOX_EPS_DEG = 1e-6
REQUIRED_KEYS = ("count", "bbox", "count_per_subdistrict")


def _read_json_or_none(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _coerce_int(v) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    try:
        if isinstance(v, float) and math.isfinite(v) and float(int(v)) == v:
            return int(v)
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _coerce_bbox(v) -> list[float] | None:
    """Best-effort coercion of a bbox-shaped value to [xmin, ymin, xmax, ymax]."""
    candidates: list = []
    if isinstance(v, (list, tuple)):
        candidates = list(v)
    elif isinstance(v, dict):
        # Accept common dict-shaped bboxes.
        for keyset in (
            ("xmin", "ymin", "xmax", "ymax"),
            ("minx", "miny", "maxx", "maxy"),
            ("west", "south", "east", "north"),
            ("left", "bottom", "right", "top"),
        ):
            if all(k in v for k in keyset):
                candidates = [v[k] for k in keyset]
                break
    if len(candidates) != 4:
        return None
    out: list[float] = []
    for c in candidates:
        if isinstance(c, bool):
            return None
        try:
            out.append(float(c))
        except (TypeError, ValueError):
            return None
    return out


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dd-l1-capetown-clinics-bbox")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Hard gate: format / schema validity ---------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    sub = _read_json_or_none(submission_path)
    if sub is None:
        report.gates.append(
            Gate("format_schema_valid", False, "could not parse JSON object")
        )
        return report

    missing = [k for k in REQUIRED_KEYS if k not in sub]
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing top-level keys: {missing}",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = _read_json_or_none(REFERENCE_OUT)
    assert ref is not None, "reference output must exist and parse"
    ref_count = int(ref["count"])
    ref_bbox = [float(v) for v in ref["bbox"]]
    ref_cps = {str(k): int(v) for k, v in ref["count_per_subdistrict"].items()}

    # Light coercion of submission values; failures here will be visible
    # as failing subchecks rather than a collapsed score.
    sub_count = _coerce_int(sub.get("count"))
    sub_bbox = _coerce_bbox(sub.get("bbox"))
    raw_cps = sub.get("count_per_subdistrict")
    if isinstance(raw_cps, dict):
        sub_cps: dict[str, int | None] = {
            str(k): _coerce_int(v) for k, v in raw_cps.items()
        }
    else:
        sub_cps = {}

    # 1. Total count strict-equality. The dataset is a fully bundled,
    #    deterministic fixture of 80 rows; the persona's question is
    #    "how many records?" and any answer other than 80 is wrong.
    report.subchecks.append(
        Subcheck(
            "count_correct",
            sub_count is not None and sub_count == ref_count,
            detail=f"submission count {sub.get('count')!r} vs reference {ref_count}",
            weight=3.0,
        )
    )

    # 2-5. Bbox componentwise within 1e-6°. Four independent subchecks
    #     so a lat/lon swap (a common L1 failure) is partially credited
    #     rather than collapsed by a single "bbox matches" boolean.
    bbox_labels = ("xmin", "ymin", "xmax", "ymax")
    for i, label in enumerate(bbox_labels):
        if sub_bbox is None:
            report.subchecks.append(
                Subcheck(
                    f"bbox_{label}_correct",
                    False,
                    detail=f"bbox not coercible to 4 numbers (got {sub.get('bbox')!r})",
                    weight=3.0,
                )
            )
            continue
        diff = abs(sub_bbox[i] - ref_bbox[i])
        report.subchecks.append(
            Subcheck(
                f"bbox_{label}_correct",
                diff <= BBOX_EPS_DEG,
                detail=(
                    f"submission {sub_bbox[i]!r} vs reference {ref_bbox[i]!r} "
                    f"(|Δ|={diff:.3e}, eps={BBOX_EPS_DEG:.0e})"
                ),
                weight=3.0,
            )
        )

    # 6. count_per_subdistrict key set equality. Catches an agent that
    #    forgot subdistricts entirely, or invented spurious ones.
    sub_keys = set(sub_cps.keys())
    ref_keys = set(ref_cps.keys())
    keys_ok = sub_keys == ref_keys
    report.subchecks.append(
        Subcheck(
            "subdistrict_keys_match",
            keys_ok,
            detail=(
                f"missing: {sorted(ref_keys - sub_keys)}, "
                f"extra: {sorted(sub_keys - ref_keys)}"
            ),
            weight=3.0,
        )
    )

    # 7. count_per_subdistrict per-value match across the intersection.
    #    Catches an agent that listed the right subdistricts but
    #    mis-counted within each (e.g. assumed equal split).
    common = sorted(sub_keys & ref_keys)
    if common:
        per_key_correct = sum(
            1 for k in common if sub_cps[k] is not None and sub_cps[k] == ref_cps[k]
        )
        per_key_rate = per_key_correct / len(common)
    else:
        per_key_correct = 0
        per_key_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "subdistrict_counts_match",
            per_key_rate == 1.0 and keys_ok,
            detail=(
                f"{per_key_correct}/{len(common)} matching values "
                f"on the {len(common)} common keys"
            ),
            weight=3.0,
        )
    )

    # 8. Internal consistency: the per-subdistrict counts sum to the
    #    reported total. Catches a sneaky failure mode where the agent
    #    reports a plausible-looking count and a plausible-looking
    #    subdistrict mapping that don't actually agree with each other.
    coerced_vals = [v for v in sub_cps.values() if v is not None]
    cps_sum = sum(coerced_vals) if len(coerced_vals) == len(sub_cps) else None
    consistent = (
        cps_sum is not None and sub_count is not None and cps_sum == sub_count
    )
    report.subchecks.append(
        Subcheck(
            "count_equals_subdistrict_sum",
            consistent,
            detail=(
                f"sum(count_per_subdistrict.values()) = {cps_sum}, "
                f"count = {sub_count}"
            ),
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
