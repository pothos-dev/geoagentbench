"""Grader for dd-l1-london-parks-count.

One hard gate (``format_schema_valid``) plus a checklist of subchecks.
The persona's three deliverables — count of parks ≥ 1 ha, their combined
area in hectares, and the WGS84 bounding box around that subset — map
onto independent subchecks so a solution that nails some of them but
botches one is partially credited. Light coercion is applied so a
wrong-typed value costs one subcheck rather than collapsing the score.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from geo_grading import Gate, ScoreReport, Subcheck

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "parks_summary.json"
OUTPUT_NAME = "parks_summary.json"

# Bbox reported in WGS84 degrees. 1e-4° ≈ 11 m at this latitude — far
# tighter than any rounding an agent would legitimately apply, but loose
# enough to absorb minor reprojection-library differences (PROJ vs pyproj
# minor versions, geographic-vs-projected order of operations, etc.).
BBOX_EPS_DEG = 1e-4

# Total-area tolerance is ±1 % rather than the L1 strict-equality default
# because hectare-conversion + planar-area summation in EPSG:27700 can
# differ at the 0.01 ha level depending on which library the agent uses
# (pyogrio vs fiona round-trips, ogr2ogr precision, etc.). 1 % over
# ~520 ha is ~5 ha — large enough to absorb that float drift, tight
# enough to flag any agent that miscomputed area in a different CRS.
AREA_TOLERANCE_PCT = 0.01

REQUIRED_KEYS = ("count", "total_area_ha", "bbox_wgs84")


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


def _coerce_float(v) -> float | None:
    if isinstance(v, bool):
        return None
    try:
        return float(v)
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


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dd-l1-london-parks-count")
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
            Gate("format_schema_valid", False, f"missing top-level keys: {missing}")
        )
        return report

    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = _read_json_or_none(REFERENCE_OUT)
    assert ref is not None, "reference output must exist and parse"
    ref_count = int(ref["count"])
    ref_area = float(ref["total_area_ha"])
    ref_bbox = [float(v) for v in ref["bbox_wgs84"]]

    sub_count = _coerce_int(sub.get("count"))
    sub_area = _coerce_float(sub.get("total_area_ha"))
    sub_bbox = _coerce_bbox(sub.get("bbox_wgs84"))

    # 1. Count strict-equality. The bundled FlatGeobuf is deterministic
    #    and the persona's question is "how many ≥ 1 ha?" — any answer
    #    other than `ref_count` is wrong by definition.
    report.subchecks.append(
        Subcheck(
            "count_correct",
            sub_count is not None and sub_count == ref_count,
            detail=f"submission count {sub.get('count')!r} vs reference {ref_count}",
            # Central deliverable: the headline answer to the persona's
            # question ("how many parks >= 1 ha?"). A wrong count means
            # the area filter -- the single primary GIS operation this
            # task probes -- was botched. Highest weight.
            weight=3.0,
        )
    )

    # 2. Total area within ±1 %. Captures both "agent forgot the filter"
    #    (area would jump by ~6×) and "agent computed area in degrees²
    #    via EPSG:4326" (area would be ~7 orders of magnitude off).
    if sub_area is None:
        area_ok = False
        rel_err_str = "not coercible to float"
    else:
        if ref_area > 0:
            rel_err = abs(sub_area - ref_area) / ref_area
        else:
            rel_err = 0.0 if sub_area == 0 else float("inf")
        area_ok = rel_err <= AREA_TOLERANCE_PCT
        rel_err_str = f"rel err {rel_err:.4f}, tol {AREA_TOLERANCE_PCT}"
    report.subchecks.append(
        Subcheck(
            "total_area_ha_correct",
            area_ok,
            detail=(
                f"submission {sub.get('total_area_ha')!r} ha vs reference "
                f"{ref_area} ha ({rel_err_str})"
            ),
            # Central deliverable: the combined area in hectares, the
            # second headline number the persona asked for. Catches the
            # forgot-the-filter and m2-vs-ha unit-slip failure modes.
            # Highest weight, on par with count.
            weight=3.0,
        )
    )

    # 3-6. Bbox componentwise within 1e-4°. Four independent subchecks so
    #     a lat / lon swap is partially credited (and distinguishable from
    #     "bbox in the wrong CRS entirely"). Reporting the bbox in the
    #     input CRS (EPSG:27700, metres) shows up as deltas of ~10⁵, far
    #     outside the tolerance, so all four flip together.
    #
    #     Weight 1.0 each (was 3.0). The bbox is the *secondary*
    #     deliverable -- a perimeter the procurement officer would draw,
    #     not the headline count/area answer. The four components are
    #     deliberately split for lat/lon-swap partial credit, so they
    #     almost always fail as a group; at weight 3.0 each they carried
    #     12 of 19 points (63 %) and let a single bbox-construction
    #     subtlety (envelope-of-envelope, run-20260609-084636Z) sink an
    #     otherwise-perfect count+area submission to 0.37. Weight 1.0
    #     keeps the bbox meaningful (4 of 10.5 points combined) without
    #     letting it dominate the central deliverables.
    bbox_labels = ("xmin", "ymin", "xmax", "ymax")
    for i, label in enumerate(bbox_labels):
        if sub_bbox is None:
            report.subchecks.append(
                Subcheck(
                    f"bbox_{label}_correct",
                    False,
                    detail=f"bbox_wgs84 not coercible to 4 numbers (got {sub.get('bbox_wgs84')!r})",
                    weight=1.0,
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
                weight=1.0,
            )
        )

    # 7. Internal consistency: bbox_wgs84 must look like WGS84 — values
    #    inside the standard lon/lat ranges. Catches an agent that
    #    forgot to reproject (the canonical L1 failure on this task).
    if sub_bbox is None:
        bbox_in_wgs84_range = False
        wgs_detail = f"bbox_wgs84 not coercible to 4 numbers (got {sub.get('bbox_wgs84')!r})"
    else:
        bbox_in_wgs84_range = (
            -180.0 <= sub_bbox[0] <= 180.0
            and -90.0 <= sub_bbox[1] <= 90.0
            and -180.0 <= sub_bbox[2] <= 180.0
            and -90.0 <= sub_bbox[3] <= 90.0
        )
        wgs_detail = f"bbox {sub_bbox} must lie in lon[-180,180], lat[-90,90]"
    report.subchecks.append(
        Subcheck(
            "bbox_in_wgs84_range",
            bbox_in_wgs84_range,
            detail=wgs_detail,
            # Structural sanity check, not a data-content answer: "are the
            # four numbers plausibly WGS84 lon/lat at all?". Lowest weight.
            # It is a coarse backstop for the forgot-to-reproject mode that
            # the componentwise checks already catch with full precision.
            weight=0.5,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
