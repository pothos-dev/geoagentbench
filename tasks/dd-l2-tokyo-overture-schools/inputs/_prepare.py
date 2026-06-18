"""Authoring-time helper: build the bundled Overture places slice.

Slices `theme=places/type=place` over an extended Tokyo-23-wards bbox
(slightly larger than the wards themselves so the spatial-join step
actually removes places). To stay near the inventory's ~10⁴ scale we
keep every `school` we find inside the extended bbox plus a
deterministic systematic sample of non-school places, target total
~10 000 rows.

Output layout — Hive-partitioned by a synthetic 4-bucket hash of the
Overture id, mirroring how Overture itself ships partitioned data:

    data/tokyo_places/bucket=0/part.parquet
    data/tokyo_places/bucket=1/part.parquet
    data/tokyo_places/bucket=2/part.parquet
    data/tokyo_places/bucket=3/part.parquet

Plus a single bbox polygon for the 23 special wards:

    data/tokyo_23wards_bbox.geojson  (one Polygon, EPSG:4326)

The bbox polygon is *strictly inside* the parquet slice's spatial
extent, so an agent that only attribute-filters and skips the
spatial crop will report ~6 % too many features.

Run once at authoring time inside the project Docker container:

    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/dd-l2-tokyo-overture-schools/inputs/_prepare.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
PARQUET_ROOT = HERE / "tokyo_places"
BBOX_OUT = HERE / "tokyo_23wards_bbox.geojson"
RELEASE = "2026-04-15.0"

# Outer bbox — the parquet slice's spatial extent. Slightly larger
# than the 23-wards rectangle below so the spatial-join step is not a
# no-op (some schools fall in the outer band but outside the wards).
OUTER = (139.50, 35.45, 139.95, 35.85)

# Inner bbox — the 23 special wards. This is what the persona's
# polygon describes; the spatial-join "contains" predicate runs
# against it. Coordinates approximate the Tokyo Metropolitan
# Government's special-ward rectangle.
WARDS = (139.560, 35.520, 139.910, 35.820)

# Deterministic systematic sample of non-school places. ~447k places
# in the outer bbox; keep ~1/45 of them → ~10k non-schools, plus all
# ~1.5k schools.
NON_SCHOOL_SAMPLE_DENOM = 45

NUM_BUCKETS = 4


def main() -> None:
    if PARQUET_ROOT.exists():
        shutil.rmtree(PARQUET_ROOT)
    PARQUET_ROOT.mkdir(parents=True, exist_ok=True)

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

    src = (
        f"'s3://overturemaps-us-west-2/release/{RELEASE}/"
        f"theme=places/type=place/*'"
    )
    xmin, ymin, xmax, ymax = OUTER

    con.execute(
        f"""
        CREATE TABLE all_places AS
        SELECT
            id,
            geometry,
            bbox,
            confidence,
            categories,
            names,
            addresses
        FROM read_parquet({src}, hive_partitioning=1)
        WHERE bbox.xmin BETWEEN {xmin} AND {xmax}
          AND bbox.ymin BETWEEN {ymin} AND {ymax}
        """
    )

    total = con.execute("SELECT count(*) FROM all_places").fetchone()[0]
    print(f"Outer-bbox places fetched: {total}")

    # Keep every school + every Nth non-school. The non-school filter
    # uses a hash of the id so the sampling is deterministic across
    # reruns of this helper.
    con.execute(
        f"""
        CREATE TABLE kept AS
        SELECT *
        FROM all_places
        WHERE categories.primary = 'school'
           OR (hash(id) % {NON_SCHOOL_SAMPLE_DENOM}) = 0
        """
    )
    n_kept = con.execute("SELECT count(*) FROM kept").fetchone()[0]
    n_schools = con.execute(
        "SELECT count(*) FROM kept WHERE categories.primary = 'school'"
    ).fetchone()[0]
    print(f"Kept rows: {n_kept} (of which {n_schools} schools)")

    # Schools inside the wards polygon (= reference answer count).
    wxmin, wymin, wxmax, wymax = WARDS
    n_wards_schools = con.execute(
        f"""
        SELECT count(*) FROM kept
        WHERE categories.primary = 'school'
          AND ST_X(geometry) BETWEEN {wxmin} AND {wxmax}
          AND ST_Y(geometry) BETWEEN {wymin} AND {wymax}
        """
    ).fetchone()[0]
    print(f"Schools inside the 23-wards bbox polygon: {n_wards_schools}")

    # Write four bucketed parquet partitions, each in its own
    # `bucket=<n>/part.parquet` Hive-style directory.
    for bucket in range(NUM_BUCKETS):
        out_dir = PARQUET_ROOT / f"bucket={bucket}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "part.parquet"
        con.execute(
            f"""
            COPY (
                SELECT id, geometry, bbox, confidence, categories, names, addresses
                FROM kept
                WHERE (hash(id) % {NUM_BUCKETS}) = {bucket}
                ORDER BY id
            ) TO '{out}' (FORMAT PARQUET);
            """
        )
        n = con.execute(
            f"SELECT count(*) FROM kept WHERE (hash(id) % {NUM_BUCKETS}) = {bucket}"
        ).fetchone()[0]
        print(f"  bucket={bucket}: {n} rows → {out.relative_to(HERE.parent)}")

    # Write the 23-wards bbox polygon as a single-feature GeoJSON.
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [wxmin, wymin],
                [wxmax, wymin],
                [wxmax, wymax],
                [wxmin, wymax],
                [wxmin, wymin],
            ]
        ],
    }
    feature_collection = {
        "type": "FeatureCollection",
        "name": "tokyo_23wards_bbox",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Tokyo 23 Special Wards (bbox)"},
                "geometry": polygon,
            }
        ],
    }
    BBOX_OUT.write_text(
        json.dumps(feature_collection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {BBOX_OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
