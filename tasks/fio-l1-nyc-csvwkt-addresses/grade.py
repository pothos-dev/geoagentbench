"""Grader for fio-l1-nyc-csvwkt-addresses.

One hard gate plus a checklist of subchecks. The persona's central
skill is *format conversion with attribute type coercion*: the input
is a CSV where the date and integer columns arrive as quoted strings,
and the agent must rewrite the file as GeoParquet with proper Arrow
types (`recorded_at` as `timestamp[us]`, `unit_count` as `int32`).

The grader inspects the *Arrow schema* of the submitted parquet
directly so a "loaded with geopandas, types accidentally widened to
timestamp[ns] / int64" pass partial-credits and is distinguishable from
a complete miss (column kept as string).

The single hard gate (`format_schema_valid`) only fails when the file
is missing, unparseable, missing required columns, or has no usable
CRS. CRS-quality grading lives in two soft subchecks
(`crs_is_canonical`, `crs_in_meaningful_set`); geometry-type uniformity
and row-count exactness move to soft subchecks too, so partial work
keeps partial credit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pyarrow as pa
import pyarrow.parquet as pq

from geo_grading import (
    Gate,
    ScoreReport,
    Subcheck,
    feature_set_equality_by_id,
    grade_crs_soft,
    read_geoparquet_lenient,
)

TASK_DIR = Path(__file__).resolve().parent
REFERENCE_OUT = TASK_DIR / "reference" / "solution" / "outputs" / "addresses.geoparquet"
OUTPUT_NAME = "addresses.geoparquet"

REQUIRED_COLUMNS = {
    "id", "country", "postcode", "street", "number", "unit", "postal_city",
    "recorded_at", "unit_count", "geometry",
}
STRING_COLUMNS = (
    "id", "country", "postcode", "street", "number", "unit", "postal_city",
)
NUMERIC_VALUE_REL_TOL = 1e-6
GEOM_EPS_DEG = 1e-9

CANONICAL_EPSG = 4326
MEANINGFUL_EPSGS = {4326}


def _read_table_or_none(path: Path) -> pa.Table | None:
    try:
        return pq.read_table(path)
    except Exception:
        return None


def grade(submission_dir: Path) -> ScoreReport:
    report = ScoreReport(task_id="fio-l1-nyc-csvwkt-addresses")
    submission_path = submission_dir / OUTPUT_NAME

    # ---- Gate: format / schema validity --------------------------------
    if not submission_path.exists():
        report.gates.append(
            Gate("format_schema_valid", False, f"missing output file: {OUTPUT_NAME}")
        )
        return report

    table = _read_table_or_none(submission_path)
    sub, crs_compliant = read_geoparquet_lenient(submission_path)
    if table is None or sub is None:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                "could not read parquet (pyarrow or geopandas read failed)",
            )
        )
        return report

    schema = table.schema
    column_names = set(schema.names)
    missing = REQUIRED_COLUMNS - column_names
    if missing:
        report.gates.append(
            Gate(
                "format_schema_valid",
                False,
                f"missing columns: {sorted(missing)}",
            )
        )
        return report

    crs_res = grade_crs_soft(
        sub, MEANINGFUL_EPSGS, CANONICAL_EPSG, treat_none_as_wgs84=False
    )
    if not crs_res.gate_ok:
        report.gates.append(
            Gate("format_schema_valid", False, crs_res.gate_reason)
        )
        return report

    sub = crs_res.normalized
    report.gates.append(Gate("format_schema_valid", True))

    # ---- Subchecks ------------------------------------------------------
    ref_table = pq.read_table(REFERENCE_OUT)
    ref_gdf = gpd.read_parquet(REFERENCE_OUT)

    # 0a. Geometry-type uniformity — all geometries should be Point.
    geom_types = set(sub.geometry.geom_type.dropna().unique())
    geom_type_ok = geom_types == {"Point"}
    report.subchecks.append(
        Subcheck(
            "geometry_type_point_only",
            geom_type_ok,
            detail=f"geometry types: {sorted(geom_types)} (expected only Point)",
        )
    )

    # 0b. Row count exact. Format-conversion task: any silent row drop
    #     breaks downstream SUM/COUNT/WHERE queries, so a tight equality
    #     is appropriate.
    n_sub = table.num_rows
    n_ref = ref_table.num_rows
    count_ok = n_sub == n_ref
    report.subchecks.append(
        Subcheck(
            "row_count_exact",
            count_ok,
            detail=f"submission {n_sub} rows vs reference {n_ref}",
            weight=2.0,
        )
    )

    # 1. recorded_at is an Arrow timestamp[us]. The inventory's central
    #    spec — accept either tz-naive or UTC-tagged us-precision; the
    #    persona only needs `> '2024-01-01'` to work, which works with
    #    either flavour.
    recorded_at_type = schema.field("recorded_at").type
    recorded_at_ok = (
        pa.types.is_timestamp(recorded_at_type)
        and recorded_at_type.unit == "us"
    )
    report.subchecks.append(
        Subcheck(
            "recorded_at_is_timestamp_us",
            recorded_at_ok,
            detail=f"recorded_at Arrow type: {recorded_at_type}",
            weight=3.0,
        )
    )

    # 2. unit_count is Arrow int32 specifically (not int64, not string).
    #    The inventory pins int32 so SUM aggregations don't silently
    #    widen and the file stays compact.
    unit_count_type = schema.field("unit_count").type
    unit_count_ok = pa.types.is_int32(unit_count_type)
    report.subchecks.append(
        Subcheck(
            "unit_count_is_int32",
            unit_count_ok,
            detail=f"unit_count Arrow type: {unit_count_type}",
            weight=3.0,
        )
    )

    # 3. The other Overture address columns are still strings (not
    #    accidentally re-typed to int / float because they happen to
    #    contain digits like postcode "10002" or number "37").
    string_type_pass = sum(
        1
        for c in STRING_COLUMNS
        if pa.types.is_string(schema.field(c).type)
        or pa.types.is_large_string(schema.field(c).type)
    )
    string_type_ok = string_type_pass == len(STRING_COLUMNS)
    report.subchecks.append(
        Subcheck(
            "address_columns_are_strings",
            string_type_ok,
            detail=(
                f"{string_type_pass}/{len(STRING_COLUMNS)} of "
                f"{list(STRING_COLUMNS)} are Arrow string"
            ),
            weight=3.0,
        )
    )

    # 4. Feature-id set preserved (Jaccard via shared library primitive).
    sub_jaccard = feature_set_equality_by_id(sub, ref_gdf, key="id")
    report.subchecks.append(
        Subcheck(
            "id_set_preserved",
            sub_jaccard >= 0.99,
            detail=f"id Jaccard {sub_jaccard:.4f}",
            weight=2.0,
        )
    )

    # 5. unit_count values agree per id (parsed back to int regardless
    #    of the storage type). A grader that only checked types would
    #    miss an agent that typed the column int32 but kept all the
    #    values from the *wrong* row order.
    common_ids = sorted(
        set(sub["id"].astype(str)) & set(ref_gdf["id"].astype(str))
    )
    sub_by_id = sub.set_index(sub["id"].astype(str))
    ref_by_id = ref_gdf.set_index(ref_gdf["id"].astype(str))
    if common_ids:
        sub_uc = sub_by_id.loc[common_ids, "unit_count"].astype("int64")
        ref_uc = ref_by_id.loc[common_ids, "unit_count"].astype("int64")
        unit_match = int((sub_uc.values == ref_uc.values).sum())
        unit_rate = unit_match / len(common_ids)
    else:
        unit_match = 0
        unit_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "unit_count_values_preserved",
            unit_rate >= 0.99,
            detail=f"{unit_match}/{len(common_ids)} unit_count values match",
            weight=2.0,
        )
    )

    # 6. recorded_at values agree per id (compared as ISO seconds so
    #    timezone-naive vs timezone-aware us-precision both pass).
    if common_ids:
        sub_ts = sub_by_id.loc[common_ids, "recorded_at"]
        ref_ts = ref_by_id.loc[common_ids, "recorded_at"]
        # Normalise both to tz-naive us so the comparison is purely
        # about the wall-clock instant.
        sub_norm = _normalise_datetime(sub_ts)
        ref_norm = _normalise_datetime(ref_ts)
        ts_match = int((sub_norm.values == ref_norm.values).sum())
        ts_rate = ts_match / len(common_ids)
    else:
        ts_match = 0
        ts_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "recorded_at_values_preserved",
            ts_rate >= 0.99,
            detail=f"{ts_match}/{len(common_ids)} recorded_at instants match",
            weight=2.0,
        )
    )

    # 7. Geometry per id within sub-degree epsilon (CSV WKT round-trip
    #    should be exact — any drift here means the agent reprojected,
    #    rounded, or read the WKT axes swapped).
    if common_ids:
        sub_g = sub_by_id.loc[common_ids, "geometry"]
        ref_g = ref_by_id.loc[common_ids, "geometry"]
        match = 0
        for sg, rg in zip(sub_g.values, ref_g.values):
            if sg is None or rg is None:
                continue
            if (
                abs(sg.x - rg.x) <= GEOM_EPS_DEG
                and abs(sg.y - rg.y) <= GEOM_EPS_DEG
            ):
                match += 1
        geom_rate = match / len(common_ids)
    else:
        match = 0
        geom_rate = 0.0
    report.subchecks.append(
        Subcheck(
            "geometry_preserved_per_id",
            geom_rate >= 0.99,
            detail=f"{match}/{len(common_ids)} points match within {GEOM_EPS_DEG:.0e}°",
            weight=2.0,
        )
    )

    # 8. No leftover `geometry_wkt` text column. A common partial-credit
    #    failure is to add the parsed geometry but forget to drop the
    #    original WKT string column, doubling storage and confusing
    #    downstream consumers.
    no_wkt_column = "geometry_wkt" not in column_names
    report.subchecks.append(
        Subcheck(
            "no_residual_geometry_wkt_column",
            no_wkt_column,
            detail=(
                "geometry_wkt column absent"
                if no_wkt_column
                else "geometry_wkt column is still present"
            ),
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
        )
    )

    # CRS metadata spec-compliance. A name-only / underspecified PROJJSON
    # (e.g. a hand-rolled `{"type":"GeographicCRS","properties":{"name":
    # "EPSG:4326"}}`) is recoverable by name so the geometry still grades,
    # but it is off-spec — PROJ 9 rejects it and standard readers choke. Dock
    # a soft point rather than hard-failing the whole submission.
    report.subchecks.append(
        Subcheck(
            "crs_spec_compliant",
            crs_compliant,
            detail=(
                "output CRS is a spec-compliant PROJJSON"
                if crs_compliant
                else "CRS metadata is an underspecified/non-compliant PROJJSON; "
                "recovered by name (full PROJJSON expected)"
            ),
        )
    )

    return report


def _normalise_datetime(series):
    """Strip timezone if present so two us-precision timestamps compare equal
    regardless of whether one is tz-naive and the other tz-aware UTC."""
    import pandas as pd

    s = pd.to_datetime(series, errors="coerce")
    if getattr(s.dt, "tz", None) is not None:
        s = s.dt.tz_convert("UTC").dt.tz_localize(None)
    return s.astype("datetime64[us]")


if __name__ == "__main__":
    report = grade(Path(sys.argv[1]))
    print(json.dumps(report.to_dict(), indent=2))
