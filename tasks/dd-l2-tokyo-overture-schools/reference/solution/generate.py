"""Reference solution for dd-l2-tokyo-overture-schools.

Reads the bundled Hive-partitioned `places.place` GeoParquet, filters
to the Overture primary-category set that serves children aged 8–14 in
Japan (compulsory education range: 小学校 + 中学校, with the generic
`school` catch-all and the ownership-tagged `private_school` /
`public_school` variants), restricts to points contained within the
supplied 23-wards bbox polygon, and writes a GeoJSON file with the
persona's required attribute schema.

Output GeoJSON schema (per feature):
    id                  — Overture place id (string)
    name                — names.primary (often CJK)
    confidence          — Overture confidence score (float, 0-1)
    address_freeform    — first address record's freeform string
    address_locality    — first address record's locality (ward)
    address_postcode    — first address record's postcode

Geometry is the original Point in EPSG:4326. Features are sorted by
`id` lexically, so two consecutive runs are byte-identical.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import geopandas as gpd
from shapely import wkt

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
PARQUET_GLOB = TASK_DIR / "inputs" / "tokyo_places" / "**" / "*.parquet"
BBOX_PATH = TASK_DIR / "inputs" / "tokyo_23wards_bbox.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "tokyo_schools.geojson"

# Overture primary-category accept-list for the age-8–14 framing.
# Hardcoded rather than discovered from data so the reference is
# deterministic across input refreshes.
ACCEPTED_CATEGORIES = (
    "school",
    "elementary_school",
    "middle_school",
    "private_school",
    "public_school",
)


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    bbox_gdf = gpd.read_file(BBOX_PATH)
    assert len(bbox_gdf) == 1, "bbox file must contain exactly one polygon"
    bbox_polygon = bbox_gdf.geometry.iloc[0]

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    in_list = ", ".join(f"'{c}'" for c in ACCEPTED_CATEGORIES)
    rows = con.execute(
        f"""
        SELECT
            id,
            names.primary AS name,
            confidence,
            addresses[1].freeform AS address_freeform,
            addresses[1].locality AS address_locality,
            addresses[1].postcode AS address_postcode,
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=1)
        WHERE categories.primary IN ({in_list})
        ORDER BY id
        """
    ).fetchdf()

    rows["geometry"] = rows["geom_wkt"].apply(wkt.loads)
    rows = rows.drop(columns=["geom_wkt"])
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # Spatial-join "contains": keep only places whose point lies
    # inside the bbox polygon.
    inside_mask = gdf.geometry.within(bbox_polygon)
    kept = gdf.loc[inside_mask].copy()
    kept = kept.sort_values("id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()

    # Hand-write the GeoJSON FeatureCollection so we control field
    # order and ensure CJK strings round-trip without ASCII escaping.
    features = []
    for _, row in kept.iterrows():
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": row["id"],
                    "name": row["name"],
                    "confidence": (
                        float(row["confidence"])
                        if row["confidence"] is not None
                        else None
                    ),
                    "address_freeform": row["address_freeform"],
                    "address_locality": row["address_locality"],
                    "address_postcode": row["address_postcode"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(row.geometry.x),
                        float(row.geometry.y),
                    ],
                },
            }
        )

    fc = {
        "type": "FeatureCollection",
        "name": "tokyo_schools",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    OUT.write_text(
        json.dumps(fc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Schools (all) in slice: {len(gdf)}")
    print(f"Schools inside the 23-wards bbox polygon: {len(kept)}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
