"""Authoring-time helper: build the bundled Bangkok land-cover GeoParquet.

Slices `theme=base/type=land_cover` over a Bangkok-metro bbox, reprojects
to EPSG:32647 (WGS84 / UTM 47N — the inventory-declared CRS for this
task), injects a deterministic set of self-intersecting "bowtie" rings
(modelling the persona's complaint that some land-cover polygons crash
his desktop GIS), and writes the result as GeoParquet. The companion
`bma_study_area.geojson` is hand-crafted as a single polygon
approximating the Bangkok Metropolitan Administration boundary; the
agent intersects every land-cover polygon with that study area.

Why Overture: AUTHOR_CONTEXT.md prefers Overture as the default
authoring source, and `base.land_cover` matches the inventory row
verbatim. The corruption is layered on top so the bundled file carries
the data-quality issue the persona describes.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/geo-l2-bangkok-landuse-intersect/inputs/_prepare.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import geopandas as gpd
from shapely.geometry import Polygon, mapping
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
OUT_LANDCOVER = HERE / "bangkok_landcover.parquet"
OUT_STUDYAREA = HERE / "bma_study_area.geojson"
RELEASE = "2026-04-15.0"

# Bangkok metropolitan bbox (WGS84). Wide enough for ~10^4 land_cover
# polygons after polygon-only filtering.
XMIN, YMIN, XMAX, YMAX = 100.30, 13.50, 100.95, 14.00

TARGET_CRS = "EPSG:32647"

# Hand-crafted BMA study-area polygon in WGS84. Approximates the BMA
# boundary as an irregular octagon over central Bangkok — covers the
# urban core but deliberately excludes the eastern fringe and the
# western suburbs so that the intersection is a strict subset of the
# bundled land-cover slice.
STUDY_AREA_WGS84_RING = [
    (100.42, 13.62),
    (100.50, 13.55),
    (100.62, 13.54),
    (100.74, 13.62),
    (100.78, 13.74),
    (100.72, 13.86),
    (100.58, 13.92),
    (100.45, 13.85),
    (100.40, 13.74),
    (100.42, 13.62),
]


def _bowtie(geom):
    """Replace a polygon's exterior ring with a self-intersecting bowtie.

    Swaps the two upper vertices of the geometry's bounding rectangle so
    the ring crosses itself once on the diagonal. shapely.make_valid()
    repairs each into a 2-triangle MultiPolygon. We deliberately retain
    the original interior rings (if any) so the corruption is realistic
    rather than synthetic.
    """
    minx, miny, maxx, maxy = geom.bounds
    coords = [
        (minx, miny),
        (maxx, maxy),
        (minx, maxy),
        (maxx, miny),
        (minx, miny),
    ]
    return Polygon(coords)


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
            subtype AS class,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=land_cover/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND subtype IS NOT NULL
        """
    ).fetchdf()

    print(f"Fetched {len(df)} land_cover rows from Overture {RELEASE}")

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )

    # Polygons only — intersection is areal.
    gdf = gdf[gdf.geometry.geom_type.isin(("Polygon", "MultiPolygon"))].copy()

    # Reproject to EPSG:32647 (UTM 47N).
    gdf = gdf.to_crs(TARGET_CRS)

    # Stable ordering by Overture id so the bundled output is byte-stable.
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    # Inject self-intersecting bowtie rings on a fixed set of indices
    # spread evenly through the dataset. Use Polygon-only candidates so
    # the corruption is a single self-intersecting ring rather than a
    # multipart geometry. ~25 corruptions out of ~10^4 polygons.
    n = len(gdf)
    polygon_idx = [i for i, gt in enumerate(gdf.geometry.geom_type) if gt == "Polygon"]
    step = max(1, len(polygon_idx) // 25)
    bowtie_positions = polygon_idx[::step][:25]
    for i in bowtie_positions:
        gdf.at[i, "geometry"] = _bowtie(gdf.geometry.iloc[i])
    n_invalid = int((~gdf.geometry.is_valid).sum())
    print(f"Injected bowties at {len(bowtie_positions)} positions; "
          f"{n_invalid} features now invalid")

    if OUT_LANDCOVER.exists():
        OUT_LANDCOVER.unlink()
    gdf.to_parquet(OUT_LANDCOVER, index=False)

    print(f"Wrote {len(gdf)} polygons → {OUT_LANDCOVER}")
    print(f"Distinct classes: {gdf['class'].nunique()}")
    print(gdf["class"].value_counts().to_string())

    # ---- Study-area polygon -------------------------------------------
    study_wgs84 = orient(Polygon(STUDY_AREA_WGS84_RING), sign=1.0)
    study_gdf = gpd.GeoDataFrame(
        {"name": ["BMA study area"]},
        geometry=[study_wgs84],
        crs="EPSG:4326",
    ).to_crs(TARGET_CRS)

    # Hand-write the GeoJSON so the file layout is byte-stable.
    feature = {
        "type": "FeatureCollection",
        "name": "bma_study_area",
        "crs": {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:EPSG::{TARGET_CRS.split(':')[1]}"},
        },
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(study_gdf.geometry.iloc[0]),
                "properties": {"name": "BMA study area"},
            }
        ],
    }
    if OUT_STUDYAREA.exists():
        OUT_STUDYAREA.unlink()
    with OUT_STUDYAREA.open("w", encoding="utf-8") as f:
        json.dump(feature, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote BMA study area → {OUT_STUDYAREA}")
    print(f"Study-area projected area: {study_gdf.geometry.area.iloc[0]:.0f} m²")


if __name__ == "__main__":
    main()
