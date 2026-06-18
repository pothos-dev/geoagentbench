"""Grader for dd-l2-bangkok-multicrs-audit.

One hard gate (``format_schema_valid``) plus a per-layer subcheck
checklist. The persona's deliverable is a one-row-per-layer audit CSV;
each layer scores five subchecks (declared CRS, geometry type, feature
count, sample-coord plausibility in the declared CRS, encoding
classification). A `layers_complete` subcheck distinguishes solutions
that enumerate the wrong layer set.

Sample coordinates are graded by *plausibility window for the declared
CRS* rather than by exact match. The persona's question is "are the
declared coordinates internally consistent with the declared CRS?",
not "did the agent pick the same first feature as the reference"; an
agent that samples any feature is fine as long as the coordinate
values fall in the expected metric / degree range for the layer's
CRS. Type-related failures (count not numeric, coords not numeric)
are scored as failing subchecks rather than collapsing the score.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from geo_grading import Gate, ScoreReport, Subcheck

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "crs_audit.csv"
OUTPUT_NAME = "crs_audit.csv"

REQUIRED_COLUMNS = (
    "layer_name",
    "declared_crs",
    "geometry_type",
    "feature_count",
    "sample_x",
    "sample_y",
    "encoding_detected",
)

# Plausibility windows for the three CRSes that appear in the bundled
# fixture. Bangkok-area bbox in each CRS, expanded by a generous margin
# so any feature an agent might pick still falls inside.
COORD_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "EPSG:4326": {"x": (100.0, 101.0), "y": (13.0, 14.0)},
    "EPSG:24047": {"x": (5.0e5, 8.0e5), "y": (1.40e6, 1.62e6)},
    "EPSG:32647": {"x": (5.0e5, 8.0e5), "y": (1.40e6, 1.62e6)},
}


def _read_csv(path: Path) -> list[dict] | None:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return None


def _index_by_layer(rows: list[dict]) -> dict[str, dict]:
    return {
        r["layer_name"]: r
        for r in rows
        if isinstance(r, dict) and isinstance(r.get("layer_name"), str)
    }


def _crs_match(a: str, b: str) -> bool:
    return a.strip().upper() == b.strip().upper()


def _geom_match(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def _encoding_match(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def _coords_plausible(declared_crs: str, x_str: str, y_str: str) -> bool:
    declared_crs = declared_crs.strip().upper()
    if declared_crs not in COORD_RANGES:
        return False
    try:
        x = float(x_str)
        y = float(y_str)
    except (TypeError, ValueError):
        return False
    rng = COORD_RANGES[declared_crs]
    return rng["x"][0] <= x <= rng["x"][1] and rng["y"][0] <= y <= rng["y"][1]


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dd-l2-bangkok-multicrs-audit")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Hard gate: format / schema validity ---------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    rows = _read_csv(submission_path)
    if rows is None:
        report.gates.append(
            Gate("format_schema_valid", False, "submission is not parseable CSV")
        )
        return report

    if not rows:
        report.gates.append(
            Gate("format_schema_valid", False, "CSV has no data rows")
        )
        return report

    missing = [c for c in REQUIRED_COLUMNS if c not in rows[0]]
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"CSV missing required columns: {missing}",
            )
        )
        return report
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref_rows = _read_csv(REFERENCE_OUT)
    assert ref_rows, "reference audit CSV must exist and parse"
    ref_by_name = _index_by_layer(ref_rows)
    sub_by_name = _index_by_layer(rows)
    expected_names = sorted(ref_by_name.keys())

    layers_match = set(sub_by_name.keys()) == set(ref_by_name.keys())
    report.subchecks.append(
        Subcheck(
            "layers_complete",
            layers_match,
            detail=(
                f"submitted {sorted(sub_by_name.keys())} "
                f"vs expected {expected_names}"
            ),
            weight=4.0,
        )
    )

    for name in expected_names:
        ref_rec = ref_by_name[name]
        sub_rec = sub_by_name.get(name)

        crs_ok = sub_rec is not None and _crs_match(
            sub_rec.get("declared_crs", ""), ref_rec["declared_crs"]
        )
        report.subchecks.append(
            Subcheck(
                f"{name}_declared_crs_correct",
                crs_ok,
                detail=(
                    f"submitted {sub_rec.get('declared_crs')!r} vs expected "
                    f"{ref_rec['declared_crs']!r}"
                    if sub_rec
                    else f"layer {name!r} missing from submission"
                ),
                weight=3.0,
            )
        )

        geom_ok = sub_rec is not None and _geom_match(
            sub_rec.get("geometry_type", ""), ref_rec["geometry_type"]
        )
        report.subchecks.append(
            Subcheck(
                f"{name}_geometry_type_correct",
                geom_ok,
                detail=(
                    f"submitted {sub_rec.get('geometry_type')!r} vs expected "
                    f"{ref_rec['geometry_type']!r}"
                    if sub_rec
                    else f"layer {name!r} missing from submission"
                ),
            )
        )

        count_ok = False
        count_detail = f"layer {name!r} missing from submission"
        if sub_rec is not None:
            try:
                count_ok = int(sub_rec["feature_count"]) == int(
                    ref_rec["feature_count"]
                )
                count_detail = (
                    f"submitted {sub_rec['feature_count']} vs expected "
                    f"{ref_rec['feature_count']}"
                )
            except (TypeError, ValueError):
                count_ok = False
                count_detail = (
                    f"submitted feature_count {sub_rec.get('feature_count')!r} "
                    f"not coercible to int"
                )
        report.subchecks.append(
            Subcheck(
                f"{name}_feature_count_correct",
                count_ok,
                detail=count_detail,
            )
        )

        coords_ok = False
        coords_detail = f"layer {name!r} missing from submission"
        if sub_rec is not None:
            coords_ok = _coords_plausible(
                sub_rec.get("declared_crs", ""),
                sub_rec.get("sample_x", ""),
                sub_rec.get("sample_y", ""),
            )
            coords_detail = (
                f"submitted ({sub_rec.get('sample_x')}, "
                f"{sub_rec.get('sample_y')}) under "
                f"{sub_rec.get('declared_crs')!r}; "
                f"plausible window for that CRS = "
                f"{COORD_RANGES.get(sub_rec.get('declared_crs', '').strip().upper())}"
            )
        report.subchecks.append(
            Subcheck(
                f"{name}_sample_coords_plausible",
                coords_ok,
                detail=coords_detail,
                weight=3.0,
            )
        )

        enc_ok = sub_rec is not None and _encoding_match(
            sub_rec.get("encoding_detected", ""), ref_rec["encoding_detected"]
        )
        report.subchecks.append(
            Subcheck(
                f"{name}_encoding_correct",
                enc_ok,
                detail=(
                    f"submitted {sub_rec.get('encoding_detected')!r} vs expected "
                    f"{ref_rec['encoding_detected']!r}"
                    if sub_rec
                    else f"layer {name!r} missing from submission"
                ),
                weight=2.0,
            )
        )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
