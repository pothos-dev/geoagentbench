"""Authoring-time helper: build the bundled NYC parks GPKG with two layers.

Slices `theme=base/type=land_use` filtered to `subtype='park'` over a
central NYC bbox, reprojects to EPSG:6539 (NAD83(2011) / NY State Plane
Long Island — the inventory-declared CRS), then writes two layers into
a single GPKG:

  * `parks_official`: the full Overture park set, treated as the
                      authoritative NYC Parks polygon layer.
  * `parks_osm`     : the same set with deterministic mutations:
                        - drop a handful of polygons (will appear in
                          parks_official only),
                        - add a handful of hand-crafted park polygons
                          (will appear in parks_osm only),
                        - shift a handful of polygons by ~30 m (creates
                          symdiff slivers on both sides — `source=both`
                          clusters in the reference output).

The mutations model a real-world reconciliation problem: the official
NYC Parks dataset and an OSM-derived parks export disagree in dozens of
places, and the persona needs the symmetric difference clustered with
label anchors.

Why Overture: AUTHOR_CONTEXT.md prefers Overture as the default
authoring source. `base.land_use` with `subtype='park'` matches the
inventory row's `base.infrastructure` theme intent (park polygons
treated as infrastructure in the inventory) — recorded as inventory
change proposal: the closer Overture match is `base.land_use` /
`subtype=park`, not `base.infrastructure`. We use the closer match.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/geo-l2-nyc-park-symdiff/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
OUT_GPKG = HERE / "nyc_parks.gpkg"
RELEASE = "2026-04-15.0"

# Central NYC bbox (covers Manhattan, parts of Brooklyn / Queens / the
# Bronx). Wide enough for ~10^3 park polygons after the subtype filter.
XMIN, YMIN, XMAX, YMAX = -74.05, 40.65, -73.85, 40.85

TARGET_CRS = "EPSG:6539"


def _candidate_extras_wgs84() -> list[Polygon]:
    """Candidate small synthetic park rectangles spread across the bbox.

    Returns more candidates than needed; the caller filters out any
    that overlap real parks and keeps the first `target` survivors. Each
    is a ~75 m square in projected metres (0.00035 deg half-side ≈ 38 m
    at lat 40.7).
    """
    polys = []
    half = 0.00035
    for ix in range(12):
        for iy in range(12):
            cx = -74.04 + ix * 0.0125
            cy = 40.66 + iy * 0.013
            polys.append(
                Polygon(
                    [
                        (cx - half, cy - half),
                        (cx + half, cy - half),
                        (cx + half, cy + half),
                        (cx - half, cy + half),
                        (cx - half, cy - half),
                    ]
                )
            )
    return polys


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
            class,
            ST_AsText(geometry) AS wkt
        FROM read_parquet(
            's3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=land_use/*',
            hive_partitioning=1
        )
        WHERE bbox.xmin BETWEEN {XMIN} AND {XMAX}
          AND bbox.ymin BETWEEN {YMIN} AND {YMAX}
          AND subtype = 'park'
        """
    ).fetchdf()

    print(f"Fetched {len(df)} park rows from Overture {RELEASE}")

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["wkt"]),
        geometry=gpd.GeoSeries.from_wkt(df["wkt"]),
        crs="EPSG:4326",
    )
    gdf = gdf[gdf.geometry.geom_type.isin(("Polygon", "MultiPolygon"))].copy()
    gdf = gdf.sort_values("id", kind="stable").reset_index(drop=True)

    # ---- parks_official: the full set, projected to EPSG:6539. -------
    official = gdf.to_crs(TARGET_CRS).copy()
    official = official.rename(columns={"class": "park_class"})
    official["park_id"] = official["id"]
    official = official[["park_id", "park_class", "geometry"]]
    official = official.sort_values("park_id", kind="stable").reset_index(drop=True)

    # ---- parks_osm: mutate the official set deterministically. -------
    rng = np.random.default_rng(seed=20260508)
    n = len(official)

    # Pick mutation positions deterministically.
    drop_idx = sorted(rng.choice(n, size=20, replace=False).tolist())
    remaining = [i for i in range(n) if i not in set(drop_idx)]
    shift_idx = sorted(rng.choice(remaining, size=15, replace=False).tolist())

    osm_rows = []
    for i, row in official.iterrows():
        if i in set(drop_idx):
            continue
        geom = row.geometry
        if i in set(shift_idx):
            # Shift by ~30 m east+north — produces (A-B) and (B-A)
            # half-moon slivers on either side of the original.
            geom = translate(geom, xoff=30.0, yoff=30.0)
        osm_rows.append(
            {
                "park_id": row.park_id,
                "park_class": row.park_class,
                "geometry": geom,
            }
        )

    # Hand-crafted extras: pick the first 12 candidates that do NOT
    # overlap any real Overture park. This keeps the synthetic polygons
    # genuinely "OSM only" — symdiff against the official layer must
    # report them in full.
    candidates_wgs = _candidate_extras_wgs84()
    cand_gdf = gpd.GeoDataFrame(
        {"geometry": candidates_wgs},
        geometry="geometry",
        crs="EPSG:4326",
    ).to_crs(TARGET_CRS)
    official_union = official.geometry.union_all()
    selected = []
    for g in cand_gdf.geometry:
        if not g.intersects(official_union):
            selected.append(g)
        if len(selected) == 12:
            break
    if len(selected) < 12:
        raise RuntimeError(
            f"Only {len(selected)} non-overlapping candidate extras found"
        )
    extras_gdf = gpd.GeoDataFrame(
        {
            "park_id": [f"osm-extra-{i:02d}" for i in range(len(selected))],
            "park_class": ["park"] * len(selected),
            "geometry": selected,
        },
        geometry="geometry",
        crs=TARGET_CRS,
    )

    osm = gpd.GeoDataFrame(osm_rows, geometry="geometry", crs=TARGET_CRS)
    osm = pd_concat_sort(osm, extras_gdf)

    print(
        f"parks_official: {len(official)} polygons; "
        f"parks_osm: {len(osm)} polygons "
        f"(dropped {len(drop_idx)}, shifted {len(shift_idx)}, "
        f"added {len(extras_gdf)})"
    )

    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    official.to_file(OUT_GPKG, layer="parks_official", driver="GPKG")
    osm.to_file(OUT_GPKG, layer="parks_osm", driver="GPKG")
    print(f"Wrote two layers → {OUT_GPKG}")


def pd_concat_sort(a: gpd.GeoDataFrame, b: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    import pandas as pd

    out = gpd.GeoDataFrame(
        pd.concat([a, b], ignore_index=True), geometry="geometry", crs=a.crs
    )
    return out.sort_values("park_id", kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    main()
