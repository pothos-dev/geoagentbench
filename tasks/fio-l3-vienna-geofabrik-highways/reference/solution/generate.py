"""Reference solution — fio-l3-vienna-geofabrik-highways

Fetches Vienna highway segments and public-transport route relations from
OpenStreetMap via the Overpass API.  Identifies the Gürtel ring road (ways
whose name ends in 'Gürtel'), buffers it by 500 m in EPSG:31287
(MGI / Austria Lambert), then filters all highway=* ways and PT route
relations to those intersecting the buffer.

L3 task — two consecutive runs may differ because of upstream OSM edits.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union

OVERPASS_URL = "https://lz4.overpass-api.de/api/interpreter"
TARGET_CRS = "EPSG:31287"
BUFFER_M = 500

TASK_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = TASK_DIR / "reference" / "solution" / "outputs"


def _overpass(query: str) -> dict:
    """Run an Overpass QL query and return parsed JSON."""
    headers = {"User-Agent": "GeoAgentBench/1.0", "Accept": "*/*"}
    resp = requests.post(
        OVERPASS_URL, data={"data": query}, headers=headers, timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def _ways_to_gdf(elements: list[dict], tag_cols: list[str]) -> gpd.GeoDataFrame:
    """Convert Overpass way elements (with ``out geom``) to a GeoDataFrame."""
    rows: list[dict] = []
    for el in elements:
        if el["type"] != "way" or "geometry" not in el:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
        if len(coords) < 2:
            continue
        tags = el.get("tags", {})
        row = {"geometry": LineString(coords), "osm_id": el["id"]}
        for col in tag_cols:
            row[col] = tags.get(col, "")
        rows.append(row)
    return gpd.GeoDataFrame(rows, crs="EPSG:4326") if rows else gpd.GeoDataFrame()


# ── data fetchers ──────────────────────────────────────────────────────


def fetch_guertel() -> gpd.GeoDataFrame:
    """Fetch ways named '*Gürtel' with a highway tag inside Vienna."""
    q = """
    [out:json][timeout:120];
    area["name"="Wien"]["admin_level"="4"]->.vienna;
    way["highway"]["name"~"ürtel$"](area.vienna);
    out geom;
    """
    data = _overpass(q)
    return _ways_to_gdf(data["elements"], ["name", "highway"])


def fetch_highways_bbox(south: float, west: float, north: float, east: float) -> gpd.GeoDataFrame:
    """Fetch all highway=* ways inside a lon/lat bbox."""
    q = f"""
    [out:json][timeout:300];
    way["highway"]({south},{west},{north},{east});
    out geom;
    """
    data = _overpass(q)
    return _ways_to_gdf(
        data["elements"],
        ["name", "highway", "maxspeed", "lanes", "surface", "oneway"],
    )


def fetch_pt_routes_bbox(south: float, west: float, north: float, east: float) -> gpd.GeoDataFrame:
    """Fetch public-transport route relations whose bbox overlaps the given bbox."""
    q = f"""
    [out:json][timeout:300];
    relation["type"="route"]["route"~"^(bus|tram|subway|train|trolleybus|light_rail)$"]({south},{west},{north},{east});
    out geom;
    """
    data = _overpass(q)
    rows: list[dict] = []
    for el in data["elements"]:
        if el["type"] != "relation":
            continue
        lines: list[LineString] = []
        for member in el.get("members", []):
            if member.get("type") == "way" and "geometry" in member:
                coords = [(pt["lon"], pt["lat"]) for pt in member["geometry"]]
                if len(coords) >= 2:
                    lines.append(LineString(coords))
        if not lines:
            continue
        tags = el.get("tags", {})
        rows.append({
            "geometry": MultiLineString(lines),
            "osm_id": el["id"],
            "ref": tags.get("ref", ""),
            "name": tags.get("name", ""),
            "operator": tags.get("operator", ""),
            "route": tags.get("route", ""),
        })
    return gpd.GeoDataFrame(rows, crs="EPSG:4326") if rows else gpd.GeoDataFrame()


# ── main pipeline ──────────────────────────────────────────────────────


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Identify the Gürtel ring road
    guertel = fetch_guertel()
    print(f"Gürtel ways fetched: {len(guertel)}")

    # 2. Project → EPSG:31287, buffer 500 m
    guertel_proj = guertel.to_crs(TARGET_CRS)
    guertel_union = unary_union(guertel_proj.geometry)
    buffer_geom = guertel_union.buffer(BUFFER_M)

    # 3. Compute a WGS-84 bbox around the buffer for Overpass queries
    buf_gdf = gpd.GeoDataFrame(geometry=[buffer_geom], crs=TARGET_CRS)
    bounds = buf_gdf.to_crs("EPSG:4326").total_bounds  # minx miny maxx maxy
    # Add a small margin so edge ways aren't clipped
    margin = 0.005  # ~500 m at this latitude
    s, w, n, e = bounds[1] - margin, bounds[0] - margin, bounds[3] + margin, bounds[2] + margin

    # 4. Fetch highways and PT routes
    highways = fetch_highways_bbox(s, w, n, e)
    print(f"Highway ways in bbox: {len(highways)}")

    pt_routes = fetch_pt_routes_bbox(s, w, n, e)
    print(f"PT route relations in bbox: {len(pt_routes)}")

    # 5. Reproject to target CRS
    if not highways.empty:
        highways = highways.to_crs(TARGET_CRS)
    if not pt_routes.empty:
        pt_routes = pt_routes.to_crs(TARGET_CRS)

    # 6. Spatial filter — intersects the 500 m Gürtel buffer
    if not highways.empty:
        highways = highways[highways.intersects(buffer_geom)].copy()
    print(f"Highways after spatial filter: {len(highways)}")

    if not pt_routes.empty:
        pt_routes = pt_routes[pt_routes.intersects(buffer_geom)].copy()
    print(f"PT routes after spatial filter: {len(pt_routes)}")

    # 7. Select & sort output columns
    hw_cols = ["geometry", "osm_id", "name", "highway", "maxspeed", "lanes", "surface", "oneway"]
    highways_out = highways[hw_cols].sort_values("osm_id").reset_index(drop=True)

    pt_cols = ["geometry", "osm_id", "ref", "name", "operator", "route"]
    pt_out = pt_routes[pt_cols].sort_values("osm_id").reset_index(drop=True)

    # 8. Write multi-layer GPKG
    out_path = OUTPUT_DIR / "vienna_network.gpkg"
    if out_path.exists():
        out_path.unlink()
    highways_out.to_file(out_path, layer="highways", driver="GPKG")
    pt_out.to_file(out_path, layer="pt_routes", driver="GPKG")

    print(f"\nWritten: {out_path}")
    print(f"  highways layer : {len(highways_out)} features")
    print(f"  pt_routes layer: {len(pt_out)} features")


if __name__ == "__main__":
    main()
