"""Authoring-time helper: build the bundled Paris amenities + arrondissements GPKG.

Run once at authoring time inside the project's Docker container. The
output ``paris_amenities.gpkg`` (two layers: ``amenities`` and
``arrondissements``) is committed to the repo and served to systems under
test by the harness. Do not run this at grading time.

Source: Overture Maps release 2026-04-15.0.

  * **Arrondissements** — ``divisions/division_area`` rows with
    ``subtype='neighborhood'``, ``country='FR'``, ``region='FR-IDF'``,
    and ``names.primary LIKE '%Arrondissement%'``. Returns the 20
    administrative subdivisions of Paris (1er Arrondissement through
    20e Arrondissement). Overture's ``names.primary`` values are
    "Paris 1er Arrondissement", "Paris 2e Arrondissement", …,
    "Paris 20e Arrondissement" — French ordinal suffixes ``1er``,
    ``2e``, …, ``20e``. The persona's deliverable demands the integer
    1–20 in the output, so the agent has to strip the suffix.

  * **Amenities** — ``places/place`` rows with ``categories.primary IN
    (curated amenity-style set)`` over a central-Paris bbox that
    brackets the périphérique. The inventory's OSM-tag axis names
    ``amenity=*``; Overture's ``places.place`` is the canonical
    Overture-side analogue and covers the same persona-relevant
    point-of-interest space (pharmacy, bakery, cafe, bank, library,
    restaurant). After id-sort and a per-category cap, the slice is
    spatially clipped to the union of the 20 arrondissements so every
    point lands inside exactly one arrondissement (no within-join
    misses to disambiguate at grading time).

Both layers are reprojected to RGF93 / Lambert-93 (EPSG:2154) — the
inventory's declared input CRS — before being written to the GPKG.

Output schemas:

  * ``amenities`` (Point, EPSG:2154):
      - ``osm_id`` (int64) — synthetic OSM-style integer, stable across
        re-runs (assigned in id-sort order so the same Overture id maps
        to the same osm_id every time).
      - ``amenity_class`` (string) — the leaf amenity category (one of
        ``pharmacy``, ``bakery``, ``cafe``, ``bank``, ``library``,
        ``restaurant``).
      - ``name`` (string) — Overture ``names.primary``, kept for
        realism so the layer looks like a hand-curated POI extract.
      - ``geometry`` (Point) — POI location in EPSG:2154 metres.

  * ``arrondissements`` (Polygon / MultiPolygon, EPSG:2154):
      - ``id`` (string) — Overture id, verbatim.
      - ``name`` (string) — Overture ``names.primary`` verbatim
        (e.g. "Paris 13e Arrondissement", "Paris 1er Arrondissement").
        The integer arrondissement number is *not* exposed as a
        separate column: deriving it from the name is the persona's
        gotcha.
      - ``geometry`` (Polygon / MultiPolygon).

Determinism: the Overture id-sort + per-category cap + bbox clip is
closed-form given the pinned release. The amenities synthetic
``osm_id`` is assigned by row position after id-sort. The two layers
are written to the GPKG in a fixed order (``amenities`` then
``arrondissements``).

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l1-paris-amenity-within/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
OUT = HERE / "paris_amenities.gpkg"
RELEASE = "2026-04-15.0"

# Central-Paris bbox, roughly bracketing the Périphérique. Wide enough
# to cover all 20 arrondissements; narrow enough to keep the amenity
# fetch cheap.
XMIN, YMIN, XMAX, YMAX = 2.224, 48.815, 2.470, 48.905

# Amenity-style place categories. The inventory's OSM-tag axis names
# ``amenity=*``; we pick six leaf categories that map cleanly onto OSM
# amenity values (the persona's "amenity points" framing).
# Amenity-style place categories. Five OSM-flavoured leaf values that
# map cleanly onto OSM ``amenity=*`` (pharmacy, bakery, cafe, library,
# restaurant). The Overture leaf taxonomy uses the same singulars on
# these five, so the bundled ``amenity_class`` column carries
# OSM-compatible values verbatim — the agent does not have to
# normalise plurals or synonyms.
AMENITY_CATEGORIES = (
    "pharmacy",
    "bakery",
    "cafe",
    "library",
    "restaurant",
)

# Per-category cap (after id-sort). Five categories × 22 ≈ ~110
# amenities, matching the inventory's "Small (~10² amenities)" tier.
PER_CATEGORY_LIMIT = 22


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute(
        """
        CREATE OR REPLACE SECRET overture (
          TYPE s3,
          PROVIDER config,
          KEY_ID '',
          SECRET '',
          REGION 'us-west-2',
          USE_SSL true,
          URL_STYLE 'path'
        );
        """
    )
    return con


def _fetch_arrondissements(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    df = con.execute(
        f"""
        SELECT
            id,
            names.primary AS name,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=divisions/type=division_area/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND country = 'FR'
          AND region = 'FR-IDF'
          AND subtype = 'neighborhood'
          AND names.primary LIKE '%Arrondissement%'
        ORDER BY id
        """
    ).fetchdf()
    if len(df) != 20:
        raise RuntimeError(
            f"Expected exactly 20 Paris arrondissements; got {len(df)}."
        )
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    return gdf


def _fetch_amenities(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    cat_list = ", ".join(f"'{c}'" for c in AMENITY_CATEGORIES)
    df = con.execute(
        f"""
        SELECT
            id,
            names.primary AS name,
            categories.primary AS amenity_class,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND categories.primary IN ({cat_list})
          AND names.primary IS NOT NULL
        ORDER BY id
        """
    ).fetchdf()
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    return gdf


def main() -> None:
    con = _connect()

    arr_wgs = _fetch_arrondissements(con)
    amen_wgs = _fetch_amenities(con)

    arr = (
        arr_wgs.to_crs("EPSG:2154")
        .sort_values("id", kind="stable")
        .reset_index(drop=True)
    )
    amen = (
        amen_wgs.to_crs("EPSG:2154")
        .sort_values("id", kind="stable")
        .reset_index(drop=True)
    )

    # Per-category cap (stable across re-runs given the id-sort).
    amen = (
        amen.groupby("amenity_class", group_keys=False)
        .head(PER_CATEGORY_LIMIT)
        .reset_index(drop=True)
    )

    # Spatially clip to the union of the 20 arrondissements so every
    # bundled amenity lands inside exactly one arrondissement (no
    # within-join misses for the agent to disambiguate).
    paris_union = unary_union(arr.geometry.tolist())
    inside = amen[amen.geometry.within(paris_union)].reset_index(drop=True)

    # Synthetic OSM-style integer ids, assigned by row position after
    # id-sort. Start at a large constant so they look like real OSM
    # node ids (which are typically 9-10 digit ints).
    osm_id_base = 9_000_000_000
    inside["osm_id"] = list(range(osm_id_base, osm_id_base + len(inside)))
    inside = inside[["osm_id", "amenity_class", "name", "geometry"]]

    arr_out = arr[["id", "name", "geometry"]]

    if OUT.exists():
        OUT.unlink()
    inside.to_file(OUT, driver="GPKG", layer="amenities")
    arr_out.to_file(OUT, driver="GPKG", layer="arrondissements")

    print(f"Wrote {OUT}")
    print(
        f"  amenities: {len(inside)} features, "
        f"classes: {inside['amenity_class'].value_counts().to_dict()}"
    )
    print(f"  arrondissements: {len(arr_out)} features")
    print("  Sample arrondissement names:")
    for nm in arr_out["name"].tolist():
        print(f"    {nm}")


if __name__ == "__main__":
    main()
