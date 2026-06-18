"""Authoring-time helper: build the bundled CSV-with-WKT input from Overture.

Slices `theme=addresses/type=address` over a small lower-Manhattan bbox,
projects WKT into a `geometry_wkt` column, and writes a CSV that mimics
the kind of malformed export the persona received from a vendor SQL
tool: every numeric and date field comes out as a quoted string so a
naive `pd.read_csv` infers them as `object` dtype rather than the
intended `int32` and `timestamp[us]`.

The two synthesised columns are:
  * recorded_at — ISO-8601 timestamp string (`2024-MM-DDThh:mm:ssZ`)
                  derived deterministically from the row index so two
                  consecutive runs of the helper produce a byte-identical
                  CSV.
  * unit_count  — small non-negative integer derived from the row index;
                  represents the number of subunits known for the
                  address (mostly 0, occasionally 1-12 for buildings
                  with named units).

The schema otherwise matches Overture's address column set: `id`,
`country`, `postcode`, `street`, `number`, `unit`, `postal_city`,
`recorded_at`, `unit_count`, `geometry_wkt`.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/fio-l1-nyc-csvwkt-addresses/inputs/_prepare.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
OUT = HERE / "nyc_addresses.csv"
RELEASE = "2026-04-15.0"

# Lower-Manhattan bbox (Tribeca / Financial District / Chinatown). Tight
# enough to keep the bundled CSV at the inventory's "small (~10³)" tier.
XMIN, YMIN, XMAX, YMAX = -74.020, 40.700, -73.990, 40.730


def _recorded_at(idx: int) -> str:
    """Deterministic ISO-8601 timestamp for row `idx`.

    Spreads timestamps across calendar year 2024 so a downstream
    `WHERE recorded_at > '2024-01-01'` filter has a non-trivial answer
    (every row passes; a date-as-string column would silently work for
    that particular query but fail on `> '2024-06-01'`).
    """
    # Day in [0, 364], hour in [0, 23], minute in [0, 59], second in [0, 59]
    day = (idx * 11) % 365
    hour = (idx * 7) % 24
    minute = (idx * 13) % 60
    second = (idx * 17) % 60
    # Map day-of-year to (month, day) without dateutil
    days_in_month = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    remaining = day
    month = 1
    for dim in days_in_month:
        if remaining < dim:
            break
        remaining -= dim
        month += 1
    dom = remaining + 1
    return f"2024-{month:02d}-{dom:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"


def _unit_count(idx: int) -> int:
    """Deterministic non-negative integer.

    Most rows are 0 (single-family / no subunit info); ~25% are 1-12
    (multi-unit buildings). Enough variance that an int32 column is
    distinguishable from a string column at grading time.
    """
    if idx % 4 == 0:
        return (idx // 4) % 13
    return 0


def main() -> None:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute(
        """
        CREATE OR REPLACE SECRET overture (
            TYPE s3, PROVIDER config, KEY_ID '', SECRET '',
            REGION 'us-west-2', USE_SSL true, URL_STYLE 'path'
        );
        """
    )

    df = con.execute(
        f"""
        SELECT
            id,
            COALESCE(country, '') AS country,
            COALESCE(postcode, '') AS postcode,
            COALESCE(street, '') AS street,
            COALESCE(number, '') AS number,
            COALESCE(unit, '') AS unit,
            COALESCE(postal_city, '') AS postal_city,
            ST_AsText(geometry) AS geometry_wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=addresses/type=address/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND country = 'US'
        ORDER BY id
        """
    ).fetchdf()

    print(f"Fetched {len(df)} address rows from Overture {RELEASE}")

    # Sub-sample to keep size in the small ~10³ tier deterministically.
    if len(df) > 1500:
        # Stable stride sample so the bundled file stays compact.
        step = math.ceil(len(df) / 1200)
        df = df.iloc[::step].reset_index(drop=True)
        print(f"Down-sampled to {len(df)} rows (every {step}-th)")

    df["recorded_at"] = [_recorded_at(i) for i in range(len(df))]
    df["unit_count"] = [_unit_count(i) for i in range(len(df))]

    cols = [
        "id", "country", "postcode", "street", "number", "unit",
        "postal_city", "recorded_at", "unit_count", "geometry_wkt",
    ]
    df = df[cols]

    if OUT.exists():
        OUT.unlink()
    # Quote *all* non-numeric values so that a naive pd.read_csv with
    # default options reads `unit_count` as `object` (because the column
    # contains plenty of values, all of them quoted strings). The CSV
    # writer below uses QUOTE_NONNUMERIC which still serialises the
    # string-typed `unit_count` column quoted.
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(cols)
        for row in df.itertuples(index=False, name=None):
            writer.writerow([str(v) for v in row])

    print(f"Wrote {len(df)} rows → {OUT}")
    print(f"First row: {df.iloc[0].to_dict()}")


if __name__ == "__main__":
    main()
