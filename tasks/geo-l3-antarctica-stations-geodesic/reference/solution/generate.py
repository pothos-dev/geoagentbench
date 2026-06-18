"""Reference solution for geo-l3-antarctica-stations-geodesic.

Fetches Antarctic research stations from Overture places.place, draws
200 km geodesic buffers, projects to EPSG:3031, clips to the Antarctic
landmass (from base.land), unions overlapping spheres into coalitions,
and computes over-water portions attributed with base.water and
base.bathymetry intersections.

Two consecutive runs may differ slightly due to Overture release drift.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
OUTPUTS = HERE / "outputs"

OVERTURE_RELEASE = "2026-04-15.0"
OVERTURE_S3 = f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}"

OUT_CRS = "EPSG:3031"  # WGS 84 / Antarctic Polar Stereographic
WGS84 = "EPSG:4326"

BUFFER_RADIUS_M = 200_000  # 200 km
LATITUDE_CUTOFF = -60.0  # Antarctic Treaty boundary

# Categories that are clearly NOT research stations
EXCLUDE_CATEGORIES = {
    "cafe", "gas_station", "souvenir_shop", "restaurant",
    "fast_food_restaurant", "industrial_equipment",
    "public_service_and_government", "beauty_salon",
    "shopping", "clothing_store", "furniture_store",
    "car_dealer", "automotive_repair", "fashion",
    "arts_and_crafts", "real_estate", "hotel",
    "professional_services",
}

# Deduplication distance in metres (stations within this range are dupes)
DEDUP_DISTANCE_M = 10_000  # 10 km


def _setup_duckdb() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; INSTALL spatial; LOAD httpfs; LOAD spatial;")
    con.execute("""
        CREATE OR REPLACE SECRET overture (
          TYPE s3, PROVIDER config, KEY_ID '', SECRET '',
          REGION 'us-west-2', USE_SSL true, URL_STYLE 'path'
        );
    """)
    return con


def _fetch_stations(con: duckdb.DuckDBPyConnection) -> gpd.GeoDataFrame:
    """Fetch Antarctic research stations from Overture places.place.

    Uses keyword filtering on names to identify station/base entries,
    then excludes obviously non-station categories and deduplicates
    by proximity.
    """
    from shapely import wkt

    url = f"{OVERTURE_S3}/theme=places/type=place/*"
    query = f"""
        SELECT
            id,
            names.primary AS name,
            categories.primary AS category,
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE bbox.ymax < {LATITUDE_CUTOFF}
          AND (
            LOWER(names.primary) LIKE '%station%'
            OR LOWER(names.primary) LIKE '% base%'
            OR LOWER(names.primary) LIKE 'base %'
            OR LOWER(names.primary) LIKE '%基地%'
            OR LOWER(names.primary) LIKE '%站%'
            OR LOWER(names.primary) LIKE '%stanice%'
            OR LOWER(names.primary) LIKE '%istasyonu%'
            OR categories.primary = 'educational_research_institute'
          )
    """
    df = con.execute(query).fetchdf()
    df["geometry"] = df["geom_wkt"].apply(wkt.loads)
    df = df.drop(columns=["geom_wkt"])
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=WGS84)
    print(f"  Raw candidates: {len(gdf)}")

    # Exclude obvious non-station categories
    if "category" in gdf.columns:
        mask = ~gdf["category"].str.lower().isin(EXCLUDE_CATEGORIES)
        gdf = gdf[mask].copy()
    print(f"  After category filter: {len(gdf)}")

    # Deduplicate by proximity: keep first occurrence, drop others within 10km
    gdf_3031 = gdf.to_crs(OUT_CRS)
    keep = []
    kept_geoms = []
    for idx in gdf_3031.index:
        pt = gdf_3031.geometry[idx]
        is_dup = False
        for kg in kept_geoms:
            if pt.distance(kg) < DEDUP_DISTANCE_M:
                is_dup = True
                break
        if not is_dup:
            keep.append(idx)
            kept_geoms.append(pt)

    gdf = gdf.loc[keep].copy()
    gdf = gdf.sort_values("name", kind="stable", na_position="last").reset_index(drop=True)
    print(f"  After dedup: {len(gdf)}")
    for _, row in gdf.iterrows():
        print(f"    {row['name']} ({row['category']}) at {row.geometry.y:.2f}, {row.geometry.x:.2f}")

    return gdf


def _fetch_layer(
    con: duckdb.DuckDBPyConnection,
    theme: str,
    layer_type: str,
    extra_cols: str = "",
    extra_sql: str = "",
) -> gpd.GeoDataFrame:
    """Generic fetcher for Overture base layers in Antarctica."""
    from shapely import wkt

    url = f"{OVERTURE_S3}/theme={theme}/type={layer_type}/*"
    cols = f"id, {extra_cols}" if extra_cols else "id"
    query = f"""
        SELECT
            {cols},
            ST_AsText(geometry) AS geom_wkt
        FROM read_parquet('{url}', hive_partitioning=true)
        WHERE bbox.ymax < {LATITUDE_CUTOFF}
        {extra_sql}
    """
    df = con.execute(query).fetchdf()
    df["geometry"] = df["geom_wkt"].apply(wkt.loads)
    df = df.drop(columns=["geom_wkt"])
    return gpd.GeoDataFrame(df, geometry="geometry", crs=WGS84)


def _geodesic_buffer(lon: float, lat: float, radius_m: float, n_points: int = 128) -> Polygon:
    """Create a geodesic buffer around a point on the WGS84 ellipsoid."""
    geod = Geod(ellps="WGS84")
    azimuths = np.linspace(0, 360, n_points, endpoint=False)
    lons, lats, _ = geod.fwd(
        np.full(n_points, lon),
        np.full(n_points, lat),
        azimuths,
        np.full(n_points, radius_m),
    )
    coords = list(zip(lons, lats))
    coords.append(coords[0])
    return Polygon(coords)


def _to_multi(geom) -> MultiPolygon:
    """Ensure geometry is MultiPolygon."""
    if geom is None or geom.is_empty:
        return MultiPolygon()
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            return MultiPolygon()
        return MultiPolygon(
            [p for g in polys for p in (g.geoms if g.geom_type == "MultiPolygon" else [g])]
        )
    return MultiPolygon()


def _clip_buffer_to_land(
    buf_geom: Polygon, land_gdf: gpd.GeoDataFrame
) -> MultiPolygon:
    """Clip a station buffer to land, using spatial filtering for speed."""
    buf_valid = make_valid(buf_geom)
    # Find land polygons that intersect this buffer
    candidates = land_gdf.sindex.query(buf_valid, predicate="intersects")
    if len(candidates) == 0:
        return MultiPolygon()
    local_land = unary_union(land_gdf.geometry.iloc[candidates].apply(make_valid).tolist())
    local_land = make_valid(local_land)
    clipped = buf_valid.intersection(local_land)
    clipped = make_valid(clipped)
    return _to_multi(clipped)


def _find_coalitions(gdf_3031: gpd.GeoDataFrame) -> list[int]:
    """Assign coalition IDs to overlapping station spheres via union-find."""
    n = len(gdf_3031)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            if gdf_3031.geometry.iloc[i].intersects(gdf_3031.geometry.iloc[j]):
                union(i, j)

    root_to_id = {}
    coalition_ids = []
    next_id = 0
    for i in range(n):
        root = find(i)
        if root not in root_to_id:
            root_to_id[root] = next_id
            next_id += 1
        coalition_ids.append(root_to_id[root])

    return coalition_ids


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    con = _setup_duckdb()

    # 1. Fetch stations
    print("Fetching Antarctic stations from Overture...")
    stations = _fetch_stations(con)

    if len(stations) == 0:
        print("WARNING: No stations found. Writing empty outputs.")
        _write_empty_outputs()
        return

    # 2. Fetch land, water, bathymetry
    print("Fetching Antarctic land polygons...")
    land = _fetch_layer(con, "base", "land",
                        extra_cols="names.primary AS name, subtype")
    print(f"  {len(land)} land features")

    print("Fetching Antarctic water polygons...")
    water = _fetch_layer(con, "base", "water",
                         extra_cols="names.primary AS name, subtype")
    print(f"  {len(water)} water features")

    print("Fetching Antarctic bathymetry polygons...")
    bathy = _fetch_layer(con, "base", "bathymetry",
                         extra_cols="depth")
    bathy["name"] = None
    bathy["subtype"] = None
    print(f"  {len(bathy)} bathymetry features")

    # 3. Create geodesic buffers for each station (in WGS84)
    print("Computing geodesic buffers (200 km)...")
    buffer_geoms = []
    for _, row in stations.iterrows():
        lon, lat = row.geometry.x, row.geometry.y
        buf = _geodesic_buffer(lon, lat, BUFFER_RADIUS_M)
        buffer_geoms.append(buf)

    # Build spatial index on land once
    land["geometry"] = land.geometry.apply(make_valid)

    # 4. Clip each buffer to land using spatial index
    print("Clipping buffers to land...")
    clipped_geoms = []
    valid_indices = []
    for i, buf_geom in enumerate(buffer_geoms):
        clipped = _clip_buffer_to_land(buf_geom, land)
        if not clipped.is_empty:
            clipped_geoms.append(clipped)
            valid_indices.append(i)
            print(f"  {stations.iloc[i]['name']}: clipped OK")
        else:
            print(f"  {stations.iloc[i]['name']}: no land intersection, skipped")

    if not valid_indices:
        print("WARNING: No buffers intersect land. Writing empty outputs.")
        _write_empty_outputs()
        return

    spheres_wgs84 = gpd.GeoDataFrame(
        {
            "station_id": stations.iloc[valid_indices]["id"].values,
            "station_name": stations.iloc[valid_indices]["name"].values,
        },
        geometry=clipped_geoms,
        crs=WGS84,
    )

    # 5. Project to EPSG:3031
    print("Projecting to EPSG:3031...")
    spheres_3031 = spheres_wgs84.to_crs(OUT_CRS)
    spheres_3031["geometry"] = spheres_3031.geometry.apply(
        lambda g: _to_multi(make_valid(g))
    )

    # 6. Find coalitions (overlapping clusters)
    print("Finding coalitions of overlapping spheres...")
    coalition_ids = _find_coalitions(spheres_3031)
    spheres_3031["coalition"] = coalition_ids

    # Sort deterministically
    spheres_3031 = spheres_3031.sort_values("station_id", kind="stable").reset_index(drop=True)

    # Write station_spheres.geoparquet
    out_spheres = OUTPUTS / "station_spheres.geoparquet"
    spheres_3031[["station_id", "station_name", "coalition", "geometry"]].to_parquet(
        out_spheres, index=False
    )
    print(f"  Wrote {out_spheres} ({len(spheres_3031)} features, "
          f"{spheres_3031['coalition'].nunique()} coalitions)")

    # 7. Compute over-water portions
    print("Computing over-water portions of station spheres...")

    # Build combined land geometry per station buffer for differencing
    # (reuse the spatial index approach)
    water_portions = []
    for i, vi in enumerate(valid_indices):
        sid = stations.iloc[vi]["id"]
        sname = stations.iloc[vi]["name"]
        buf_valid = make_valid(buffer_geoms[vi])

        # Get local land for this buffer
        candidates = land.sindex.query(buf_valid, predicate="intersects")
        if len(candidates) > 0:
            local_land = unary_union(land.geometry.iloc[candidates].tolist())
            local_land = make_valid(local_land)
            over_water = buf_valid.difference(local_land)
        else:
            over_water = buf_valid
        over_water = make_valid(over_water)
        if not over_water.is_empty:
            water_portions.append({
                "station_id": sid,
                "station_name": sname,
                "buffer_geom": over_water,
            })

    if not water_portions:
        print("  No over-water portions found.")
        _write_empty_water_output()
        return

    # Combine water + bathymetry features for intersection
    water_features = []
    for _, row in water.iterrows():
        water_features.append({
            "water_id": row["id"],
            "water_name": row.get("name"),
            "water_subtype": row.get("subtype"),
            "water_source": "base.water",
            "geometry": make_valid(row.geometry),
        })
    for _, row in bathy.iterrows():
        water_features.append({
            "water_id": row["id"],
            "water_name": row.get("name"),
            "water_subtype": row.get("subtype"),
            "water_source": "base.bathymetry",
            "geometry": make_valid(row.geometry),
        })

    if water_features:
        water_ref = gpd.GeoDataFrame(water_features, geometry="geometry", crs=WGS84)
    else:
        water_ref = None

    # Spatial join: for each station's over-water portion, find intersecting
    # water/bathy features using spatial index
    print("  Intersecting over-water portions with water/bathymetry...")
    overlap_rows = []

    if water_ref is not None and len(water_ref) > 0:
        for wp in water_portions:
            s_geom = wp["buffer_geom"]
            if s_geom.is_empty:
                continue
            # Use spatial index
            candidates = water_ref.sindex.query(s_geom, predicate="intersects")
            for cidx in candidates:
                wf_row = water_ref.iloc[cidx]
                inter = s_geom.intersection(wf_row.geometry)
                inter = make_valid(inter)
                if not inter.is_empty:
                    overlap_rows.append({
                        "station_id": wp["station_id"],
                        "station_name": wp["station_name"],
                        "water_id": wf_row["water_id"],
                        "water_name": wf_row["water_name"],
                        "water_subtype": wf_row["water_subtype"],
                        "water_source": wf_row["water_source"],
                        "geometry": _to_multi(inter),
                    })

    if overlap_rows:
        overlap_gdf = gpd.GeoDataFrame(overlap_rows, geometry="geometry", crs=WGS84)
    else:
        # Fallback: output the over-water portions without water feature attribution
        overlap_gdf = gpd.GeoDataFrame(
            [{
                "station_id": wp["station_id"],
                "station_name": wp["station_name"],
                "water_id": None,
                "water_name": None,
                "water_subtype": None,
                "water_source": None,
                "geometry": _to_multi(wp["buffer_geom"]),
            } for wp in water_portions],
            geometry="geometry",
            crs=WGS84,
        )

    # Project to EPSG:3031
    overlap_3031 = overlap_gdf.to_crs(OUT_CRS)
    overlap_3031["geometry"] = overlap_3031.geometry.apply(
        lambda g: _to_multi(make_valid(g))
    )

    # Sort deterministically
    overlap_3031 = overlap_3031.sort_values(
        ["station_id", "water_id"], kind="stable", na_position="last"
    ).reset_index(drop=True)

    out_water = OUTPUTS / "station_water_overlap.geoparquet"
    cols = ["station_id", "station_name", "water_id", "water_name",
            "water_subtype", "water_source", "geometry"]
    overlap_3031[cols].to_parquet(out_water, index=False)
    print(f"  Wrote {out_water} ({len(overlap_3031)} features)")


def _write_empty_outputs():
    """Write empty output files with correct schema."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    empty_spheres = gpd.GeoDataFrame(
        {"station_id": pd.Series(dtype="str"),
         "station_name": pd.Series(dtype="str"),
         "coalition": pd.Series(dtype="int64")},
        geometry=gpd.GeoSeries([], crs=OUT_CRS),
    )
    empty_spheres.to_parquet(OUTPUTS / "station_spheres.geoparquet", index=False)
    _write_empty_water_output()


def _write_empty_water_output():
    """Write empty water overlap output."""
    empty = gpd.GeoDataFrame(
        {"station_id": pd.Series(dtype="str"),
         "station_name": pd.Series(dtype="str"),
         "water_id": pd.Series(dtype="str"),
         "water_name": pd.Series(dtype="str"),
         "water_subtype": pd.Series(dtype="str"),
         "water_source": pd.Series(dtype="str")},
        geometry=gpd.GeoSeries([], crs=OUT_CRS),
    )
    empty.to_parquet(OUTPUTS / "station_water_overlap.geoparquet", index=False)


if __name__ == "__main__":
    main()
