"""Grader for dc-l1-bangkok-attribute-coercion.

Single hard gate (`format_schema_valid`) when the file is missing,
unparseable, lacks a usable CRS, or is missing required properties.
Everything else (geometry type, row count, per-column type checks,
value/name/geometry preservation, CRS pick) is a one-point subcheck.

The task's central skill is *attribute type coercion* — every numeric
column in the bundled GeoJSON arrives as a JSON string
(`"sensor_value": "42.7"`) and the agent must rewrite the file with
proper JSON numeric types (`"sensor_value": 42.7`). The grader
detects type by parsing the submission's raw JSON (NOT through
GeoPandas, which would coerce strings back to numbers on read and
defeat the test).

The four type subchecks score independently so an agent that fixed the
floats but forgot `station_id` (or vice versa) lands in a distinct
range from one that left every column stringified. Two CRS subchecks
at the end grade the agent's CRS pick:
- `crs_is_canonical` — declared CRS is EPSG:4326 (the spec'd output
  CRS).
- `crs_in_meaningful_set` — declared CRS is in {EPSG:4326}. The task
  is attribute-only; reprojection is not in scope, so any non-4326
  CRS is docked both subchecks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    count_within_tolerance,
    feature_set_equality_by_id,
    grade_crs_soft,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "bangkok_aq_typed.geojson"
OUTPUT_NAME = "bangkok_aq_typed.geojson"

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}

REQUIRED_PROPERTIES = {
    "station_id",
    "name_th",
    "sensor_value",
    "pm25_ug_m3",
    "elevation_m",
}
FLOAT_FIELDS = ("sensor_value", "pm25_ug_m3", "elevation_m")
NUMERIC_VALUE_REL_TOL = 1e-3
GEOM_EPS_DEG = 1e-6
TYPE_PASS_THRESHOLD = 0.95


def _read_json_or_none(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _read_gdf_or_none(path: Path) -> gpd.GeoDataFrame | None:
    try:
        return gpd.read_file(path)
    except Exception:
        return None


def _is_strict_int(value: object) -> bool:
    """True if `value` is a JSON-typed integer (int, not bool, not float)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number_not_string(value: object) -> bool:
    """True if `value` is a JSON-typed number (int or float, not string).

    Booleans are excluded because Python treats them as int subclasses;
    a stray boolean in a numeric column would be a defect we want to
    catch separately.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _to_float(value: object) -> float | None:
    """Best-effort coercion to float. Returns None if not coercible."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="dc-l1-bangkok-attribute-coercion")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format/schema validity ----------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing output file: {OUTPUT_NAME}",
            )
        )
        return report

    raw = _read_json_or_none(submission_path)
    sub = _read_gdf_or_none(submission_path)
    if raw is None or sub is None or "features" not in (raw or {}):
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "could not parse GeoJSON (raw json or geopandas read failed)",
            )
        )
        return report

    crs_res = grade_crs_soft(
        sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=True
    )
    sub_props_first = (
        raw["features"][0]["properties"] if raw["features"] else {}
    )
    missing = REQUIRED_PROPERTIES - set(sub_props_first.keys())
    columns_ok = not missing

    if not (crs_res.gate_ok and columns_ok):
        reason_parts = []
        if not crs_res.gate_ok:
            reason_parts.append(crs_res.gate_reason)
        if not columns_ok:
            reason_parts.append(f"missing properties: {sorted(missing)}")
        report.gates.append(
            Gate("format_schema_valid", False, "; ".join(reason_parts))
        )
        return report

    sub = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref = gpd.read_file(REFERENCE_OUT)

    # Geometry type uniformity (Point) — salvageable; one point if wrong.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    geom_type_ok = geom_types == {"Point"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_point_only",
            bool(geom_type_ok),
            detail=f"got geometry types {sorted(geom_types)}, expected Point",
            weight=1.0,
        )
    )

    # Feature count within ±5% of the reference.
    count_ok = count_within_tolerance(sub, ref, pct=0.05)
    report.subchecks.append(
        Subcheck(
            "feature_count_within_tolerance",
            bool(count_ok),
            detail=f"submission {len(sub)} vs reference {len(ref)} (±5%)",
            weight=2.0,
        )
    )

    raw_features: list[dict] = raw["features"]
    n_features = len(raw_features)

    # 1. station_id is a JSON integer in every feature. The inventory's
    #    central spec — "station_id typed as integer" — and the most
    #    obvious tell-tale that an agent went one level deep and stopped.
    station_id_int_count = sum(
        1
        for feat in raw_features
        if _is_strict_int(feat.get("properties", {}).get("station_id"))
    )
    station_id_pass_rate = (
        station_id_int_count / n_features if n_features else 0.0
    )
    report.subchecks.append(
        Subcheck(
            "station_id_is_integer",
            station_id_pass_rate >= TYPE_PASS_THRESHOLD,
            detail=(
                f"{station_id_int_count}/{n_features} features have "
                "station_id as JSON integer"
            ),
            weight=6.0,
        )
    )

    # 2-4. Each float-typed numeric field must be a JSON number (not a
    #      string) in every feature. We accept either int- or
    #      float-typed JSON numbers — the persona's complaint is purely
    #      that the field is a string, and a dashboard that does
    #      `parseFloat` works equally well on `42` or `42.7`.
    for field in FLOAT_FIELDS:
        passed = sum(
            1
            for feat in raw_features
            if _is_number_not_string(feat.get("properties", {}).get(field))
        )
        rate = passed / n_features if n_features else 0.0
        report.subchecks.append(
            Subcheck(
                f"{field}_is_number_not_string",
                rate >= TYPE_PASS_THRESHOLD,
                detail=(
                    f"{passed}/{n_features} features have {field} as "
                    "JSON number (not string)"
                ),
                weight=6.0,
            )
        )

    # 5. station_id set preserved. We coerce to string on both sides so
    #    the Jaccard works whether the submission used string or int
    #    (the type subcheck above already grades the type — set
    #    preservation is about *which* rows survived, not how they were
    #    encoded).
    sub_ids_raw = [
        feat.get("properties", {}).get("station_id") for feat in raw_features
    ]
    ref_raw = _read_json_or_none(REFERENCE_OUT) or {"features": []}
    ref_ids_raw = [
        feat.get("properties", {}).get("station_id") for feat in ref_raw["features"]
    ]
    sub_ids_str = {str(v) for v in sub_ids_raw if v is not None}
    ref_ids_str = {str(v) for v in ref_ids_raw if v is not None}
    if not sub_ids_str and not ref_ids_str:
        id_jaccard = 1.0
    else:
        id_jaccard = (
            len(sub_ids_str & ref_ids_str) / len(sub_ids_str | ref_ids_str)
        )
    report.subchecks.append(
        Subcheck(
            "station_id_set_preserved",
            id_jaccard >= 0.95,
            detail=f"station_id Jaccard {id_jaccard:.4f}",
            weight=2.0,
        )
    )

    # 6. Numeric values themselves are preserved. We coerce both sides
    #    to float for the comparison so this subcheck is *content*-only,
    #    independent of whether the agent fixed the JSON types. An agent
    #    that left every numeric field as a string still passes this if
    #    the underlying value `float("42.7") == 42.7` agrees.
    sub_by_id: dict[str, dict] = {}
    for feat in raw_features:
        sid = feat.get("properties", {}).get("station_id")
        if sid is not None:
            sub_by_id[str(sid)] = feat["properties"]
    ref_by_id: dict[str, dict] = {}
    for feat in ref_raw["features"]:
        sid = feat.get("properties", {}).get("station_id")
        if sid is not None:
            ref_by_id[str(sid)] = feat["properties"]

    common_ids = sorted(set(sub_by_id) & set(ref_by_id))
    all_numeric_fields = ("station_id",) + FLOAT_FIELDS
    n_pairs = 0
    n_match = 0
    for sid in common_ids:
        for field in all_numeric_fields:
            sub_val = _to_float(sub_by_id[sid].get(field))
            ref_val = _to_float(ref_by_id[sid].get(field))
            if sub_val is None or ref_val is None:
                n_pairs += 1
                continue
            n_pairs += 1
            denom = max(abs(ref_val), 1e-9)
            if abs(sub_val - ref_val) / denom <= NUMERIC_VALUE_REL_TOL:
                n_match += 1
    value_match_rate = n_match / n_pairs if n_pairs else 0.0
    report.subchecks.append(
        Subcheck(
            "numeric_values_preserved",
            value_match_rate >= 0.99,
            detail=(
                f"{n_match}/{n_pairs} numeric cells agree to within "
                f"{NUMERIC_VALUE_REL_TOL:.0e} relative tolerance"
            ),
            weight=2.0,
        )
    )

    # 7. `name_th` preserved verbatim per station_id. Catches any
    #    agent that re-encoded the file through a non-UTF-8 stage and
    #    mangled the Thai script (very common when KML / Shapefile is
    #    used as a staging format) or that ran the column through a
    #    string-cleaning pass it shouldn't have.
    name_match = 0
    name_pairs = 0
    for sid in common_ids:
        sub_name = sub_by_id[sid].get("name_th")
        ref_name = ref_by_id[sid].get("name_th")
        if sub_name is None or ref_name is None:
            name_pairs += 1
            continue
        name_pairs += 1
        if sub_name == ref_name:
            name_match += 1
    name_match_rate = name_match / name_pairs if name_pairs else 0.0
    report.subchecks.append(
        Subcheck(
            "name_th_preserved_verbatim",
            name_match_rate >= 0.95,
            detail=(
                f"{name_match}/{name_pairs} name_th values match the "
                "reference exactly (Thai script preserved)"
            ),
            weight=2.0,
        )
    )

    # 8. Point geometry preserved per station_id. The cleanup is
    #    attribute-only; coordinate edits (reprojection round-trip,
    #    rounding) flag here.
    sub_geom_by_id: dict[str, tuple[float, float] | None] = {}
    for feat in raw_features:
        sid = feat.get("properties", {}).get("station_id")
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") if isinstance(geom, dict) else None
        if (
            sid is not None
            and isinstance(coords, list)
            and len(coords) >= 2
            and all(isinstance(c, (int, float)) for c in coords[:2])
        ):
            sub_geom_by_id[str(sid)] = (float(coords[0]), float(coords[1]))

    ref_geom_by_id: dict[str, tuple[float, float]] = {}
    for feat in ref_raw["features"]:
        sid = feat.get("properties", {}).get("station_id")
        coords = (feat.get("geometry") or {}).get("coordinates")
        if sid is not None and isinstance(coords, list) and len(coords) >= 2:
            ref_geom_by_id[str(sid)] = (float(coords[0]), float(coords[1]))

    geom_match = 0
    geom_pairs = 0
    for sid in common_ids:
        sg = sub_geom_by_id.get(sid)
        rg = ref_geom_by_id.get(sid)
        if sg is None or rg is None:
            geom_pairs += 1
            continue
        geom_pairs += 1
        if (
            abs(sg[0] - rg[0]) <= GEOM_EPS_DEG
            and abs(sg[1] - rg[1]) <= GEOM_EPS_DEG
        ):
            geom_match += 1
    geom_match_rate = geom_match / geom_pairs if geom_pairs else 0.0
    report.subchecks.append(
        Subcheck(
            "geometry_preserved_per_id",
            geom_match_rate >= 0.95,
            detail=(
                f"{geom_match}/{geom_pairs} points match the reference "
                f"to within {GEOM_EPS_DEG:.0e}°"
            ),
            weight=2.0,
        )
    )

    # 9. Feature-id Jaccard via the shared library primitive (works on
    #    GeoDataFrames, complements the raw-JSON set check above by
    #    confirming the GeoPandas-readable view also agrees).
    sub_jaccard = feature_set_equality_by_id(
        sub.assign(_sid=sub["station_id"].astype(str)),
        ref.assign(_sid=ref["station_id"].astype(str)),
        key="_sid",
    )
    report.subchecks.append(
        Subcheck(
            "feature_id_set_via_geopandas",
            sub_jaccard >= 0.95,
            detail=f"GeoPandas-view station_id Jaccard {sub_jaccard:.4f}",
            weight=1.0,
        )
    )

    report.subchecks.append(
        Subcheck(
            "crs_is_canonical",
            crs_res.is_canonical,
            detail=(
                f"original EPSG:{crs_res.original_epsg}; "
                f"canonical EPSG:{CANONICAL_EPSG}"
            ),
            weight=1.0,
        )
    )
    report.subchecks.append(
        Subcheck(
            "crs_in_meaningful_set",
            crs_res.in_meaningful_set,
            detail=(
                f"original EPSG:{crs_res.original_epsg}; "
                f"meaningful set {sorted(MEANINGFUL_EPSGS)}"
            ),
            weight=1.0,
        )
    )

    return report


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
