"""Grader for dd-l1-vienna-gpkg-manifest.

One hard gate (``format_schema_valid``) plus a checklist of subchecks.
The persona's deliverable is a manifest of the seven layers in the
bundled GPKG, so each layer's four metadata fields (CRS, geometry type,
feature count, bbox) is its own subcheck — a solution that nails six
layers but botches one is partially credited proportionally. Per-record
values are coerced with light casting (string → int for the count,
4-element list/tuple/dict for the bbox), so wrong-typed fields show up
as failing subchecks rather than collapsing the score.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from geo_grading import Gate, ScoreReport, Subcheck

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "manifest.json"
OUTPUT_NAME = "manifest.json"

# Bbox is reported in the layer's native CRS (EPSG:31287, metres). 1 m
# tolerance per component is far below the rounding precision the
# reference applies (2 decimal places = 1 cm) but loose enough to absorb
# pyogrio / fiona float drift across reads.
BBOX_EPS_M = 1.0

REQUIRED_KEYS = ("layer_name", "crs", "geometry_type", "feature_count", "bbox")


def _read_json_or_none(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


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
    candidates: list = []
    if isinstance(v, (list, tuple)):
        candidates = list(v)
    elif isinstance(v, dict):
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


def _index_by_layer(manifest: list) -> dict[str, dict]:
    return {
        rec["layer_name"]: rec
        for rec in manifest
        if isinstance(rec, dict) and isinstance(rec.get("layer_name"), str)
    }


def _crs_match(a, b: str) -> bool:
    if not isinstance(a, str):
        return False
    return a.strip().upper() == b.strip().upper()


def _geom_match(a, b: str) -> bool:
    if not isinstance(a, str):
        return False
    return a.strip().lower() == b.strip().lower()


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dd-l1-vienna-gpkg-manifest")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Hard gate: format / schema validity ---------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    sub = _read_json_or_none(submission_path)
    if not isinstance(sub, list):
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "manifest.json must be a top-level JSON list",
            )
        )
        return report

    if not sub or not all(isinstance(r, dict) for r in sub):
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "manifest.json must be a non-empty list of objects",
            )
        )
        return report

    missing_keys = sorted({k for r in sub for k in REQUIRED_KEYS if k not in r})
    if missing_keys:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"records missing required keys: {missing_keys}",
            )
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = _read_json_or_none(REFERENCE_OUT)
    assert isinstance(ref, list), "reference manifest must exist and parse"
    ref_by_name = _index_by_layer(ref)
    sub_by_name = _index_by_layer(sub)
    expected_names = sorted(ref_by_name.keys())

    # 1. layers_complete: the set of submitted layer_names must equal
    #    the set of layers actually in the GPKG. Catches both omissions
    #    and spurious extras (e.g. an agent that hand-rolled a manifest
    #    instead of opening the file).
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

    # 2. Per-layer attribute subchecks. A missing layer in the
    #    submission flips all four of its subchecks to fail.
    for name in expected_names:
        ref_rec = ref_by_name[name]
        sub_rec = sub_by_name.get(name)

        crs_ok = sub_rec is not None and _crs_match(sub_rec.get("crs"), ref_rec["crs"])
        report.subchecks.append(
            Subcheck(
                f"{name}_crs_correct",
                crs_ok,
                detail=(
                    f"submitted {sub_rec.get('crs')!r} vs expected {ref_rec['crs']!r}"
                    if sub_rec
                    else f"layer {name!r} missing from submission"
                ),
            )
        )

        geom_ok = sub_rec is not None and _geom_match(
            sub_rec.get("geometry_type"), ref_rec["geometry_type"]
        )
        report.subchecks.append(
            Subcheck(
                f"{name}_geom_type_correct",
                geom_ok,
                detail=(
                    f"submitted {sub_rec.get('geometry_type')!r} vs expected "
                    f"{ref_rec['geometry_type']!r}"
                    if sub_rec
                    else f"layer {name!r} missing from submission"
                ),
            )
        )

        if sub_rec is None:
            report.subchecks.append(
                Subcheck(
                    f"{name}_count_correct",
                    False,
                    detail=f"layer {name!r} missing from submission",
                )
            )
        else:
            sub_count = _coerce_int(sub_rec.get("feature_count"))
            ref_count = int(ref_rec["feature_count"])
            count_ok = sub_count is not None and sub_count == ref_count
            report.subchecks.append(
                Subcheck(
                    f"{name}_count_correct",
                    count_ok,
                    detail=(
                        f"submitted {sub_rec.get('feature_count')!r} vs expected "
                        f"{ref_count}"
                    ),
                )
            )

        if sub_rec is None:
            report.subchecks.append(
                Subcheck(
                    f"{name}_bbox_correct",
                    False,
                    detail=f"layer {name!r} missing from submission",
                )
            )
        else:
            sub_bbox = _coerce_bbox(sub_rec.get("bbox"))
            ref_bbox = [float(v) for v in ref_rec["bbox"]]
            if sub_bbox is None:
                report.subchecks.append(
                    Subcheck(
                        f"{name}_bbox_correct",
                        False,
                        detail=(
                            f"bbox not coercible to 4 numbers "
                            f"(got {sub_rec.get('bbox')!r})"
                        ),
                    )
                )
            else:
                diffs = [abs(s - r) for s, r in zip(sub_bbox, ref_bbox)]
                bbox_ok = max(diffs) <= BBOX_EPS_M
                report.subchecks.append(
                    Subcheck(
                        f"{name}_bbox_correct",
                        bbox_ok,
                        detail=(
                            f"submitted {sub_bbox} vs expected {ref_bbox} "
                            f"(max |Δ|={max(diffs):.3f}, eps={BBOX_EPS_M})"
                        ),
                    )
                )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
