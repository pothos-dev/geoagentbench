"""Reference solution for spa-l3-paris-emergency-routing.

Fetches Paris highway network and hospitals from OSM Overpass, builds a
routable graph, and produces a four-layer GPKG:
  - incidents: sample emergency-call points
  - closest_hospital: shortest-path LineString from each incident to nearest hospital
  - distance_matrix: tabular m x n network distances (each incident x 3 nearest hospitals)
  - isochrones_15min: 15-minute drive-time isochrone MultiPolygon per hospital

L3 task — two consecutive runs may differ slightly due to live OSM data drift.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import requests
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

warnings.filterwarnings("ignore", category=FutureWarning)

TASK_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = TASK_DIR / "reference" / "solution" / "outputs"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "geo-agent-bench/0.1 (reference solution)"}

# Central Paris bounding box
BBOX_SOUTH, BBOX_WEST, BBOX_NORTH, BBOX_EAST = 48.83, 2.30, 48.88, 2.38

DEFAULT_SPEED_KMH = 30.0
ISOCHRONE_SECONDS = 15 * 60  # 15 minutes

# Eight deterministic sample incident locations within the bbox
INCIDENT_COORDS_WGS84 = [
    (48.8566, 2.3522),   # near Notre-Dame
    (48.8620, 2.3360),   # near Louvre
    (48.8462, 2.3464),   # Quartier Latin
    (48.8700, 2.3431),   # near Gare du Nord area
    (48.8530, 2.3325),   # Luxembourg Garden area
    (48.8600, 2.3700),   # Bastille area
    (48.8450, 2.3100),   # near Montparnasse
    (48.8750, 2.3600),   # near Republique
]

CRS_WGS84 = "EPSG:4326"
CRS_OUT = "EPSG:2154"


def _overpass_query(query: str) -> dict:
    """Run an Overpass query and return JSON response."""
    resp = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=300)
    resp.raise_for_status()
    return resp.json()


def fetch_hospitals() -> gpd.GeoDataFrame:
    """Fetch hospitals in the bbox from Overpass API."""
    bbox = f"{BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST}"
    query = (
        f"[out:json][timeout:120];"
        f'(node["amenity"="hospital"]({bbox});'
        f'way["amenity"="hospital"]({bbox});'
        f'relation["amenity"="hospital"]({bbox}););'
        f"out center;"
    )
    data = _overpass_query(query)

    rows = []
    seen_names: set[str] = set()
    for el in data["elements"]:
        tags = el.get("tags", {})
        name = tags.get("name", "")
        if el["type"] == "node":
            lat, lon = el["lat"], el["lon"]
        else:
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
            if lat is None or lon is None:
                continue
        # Deduplicate by name
        dedup_key = name.strip().lower() if name else f"unnamed_{el['id']}"
        if dedup_key in seen_names:
            continue
        seen_names.add(dedup_key)
        rows.append({
            "osm_id": el["id"],
            "name": name or f"Hospital_{el['id']}",
            "geometry": Point(lon, lat),
        })

    gdf = gpd.GeoDataFrame(rows, crs=CRS_WGS84)
    gdf = gdf.sort_values("osm_id").reset_index(drop=True)
    return gdf


def fetch_road_network() -> nx.DiGraph:
    """Fetch driveable roads from Overpass and build a networkx graph.

    Returns a directed graph where each node has 'x' (lon) and 'y' (lat)
    attributes, and each edge has 'length' (metres) and 'travel_time' (seconds).
    """
    bbox = f"{BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST}"
    # Fetch all highway ways that are driveable
    query = (
        f"[out:json][timeout:180];"
        f'way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|'
        f'secondary|secondary_link|tertiary|tertiary_link|residential|living_street|'
        f'unclassified|service)$"]({bbox});'
        f"(._;>;);"  # recurse down to get nodes
        f"out body;"
    )
    print("  Querying Overpass for road network...")
    data = _overpass_query(query)

    # Index nodes
    nodes: dict[int, tuple[float, float]] = {}  # osm_id -> (lat, lon)
    ways: list[dict] = []
    for el in data["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way":
            ways.append(el)

    print(f"  Fetched {len(nodes)} nodes, {len(ways)} ways")

    # Build directed graph
    G = nx.DiGraph()
    for nid, (lat, lon) in nodes.items():
        G.add_node(nid, x=lon, y=lat)

    for way in ways:
        tags = way.get("tags", {})
        oneway = tags.get("oneway", "no")
        maxspeed = _parse_speed(tags.get("maxspeed"))
        speed_ms = maxspeed / 3.6

        node_ids = way.get("nodes", [])
        for i in range(len(node_ids) - 1):
            u, v = node_ids[i], node_ids[i + 1]
            if u not in nodes or v not in nodes:
                continue
            lat1, lon1 = nodes[u]
            lat2, lon2 = nodes[v]
            length_m = _haversine_m(lat1, lon1, lat2, lon2)
            tt = length_m / speed_ms if speed_ms > 0 else float("inf")

            G.add_edge(u, v, length=length_m, travel_time=tt)
            if oneway not in ("yes", "1", "true", "-1"):
                G.add_edge(v, u, length=length_m, travel_time=tt)
            elif oneway == "-1":
                # Reverse oneway
                G.remove_edge(u, v)
                G.add_edge(v, u, length=length_m, travel_time=tt)

    # Keep only the largest strongly connected component
    if len(G) > 0:
        largest_cc = max(nx.strongly_connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    print(f"  Graph (largest SCC): {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in metres between two WGS84 points."""
    R = 6_371_000.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def _parse_speed(maxspeed) -> float:
    """Parse OSM maxspeed tag to km/h float."""
    if maxspeed is None:
        return DEFAULT_SPEED_KMH
    if isinstance(maxspeed, (int, float)):
        return float(maxspeed)
    s = str(maxspeed).strip().lower()
    if s in ("walk", "none", "signals", "variable"):
        return DEFAULT_SPEED_KMH
    if "mph" in s:
        try:
            return float(s.replace("mph", "").strip()) * 1.60934
        except ValueError:
            return DEFAULT_SPEED_KMH
    try:
        return float(s)
    except ValueError:
        return DEFAULT_SPEED_KMH


def find_nearest_node(G: nx.DiGraph, lat: float, lon: float) -> int:
    """Find the nearest graph node to a (lat, lon) point."""
    best_node = None
    best_dist = float("inf")
    for nid, data in G.nodes(data=True):
        d = (data["y"] - lat) ** 2 + (data["x"] - lon) ** 2
        if d < best_dist:
            best_dist = d
            best_node = nid
    return best_node


def find_nearest_nodes_fast(G: nx.DiGraph, coords: list[tuple[float, float]]) -> list[int]:
    """Find nearest graph nodes for a list of (lat, lon) points using numpy."""
    node_ids = list(G.nodes())
    node_lats = np.array([G.nodes[n]["y"] for n in node_ids])
    node_lons = np.array([G.nodes[n]["x"] for n in node_ids])

    result = []
    for lat, lon in coords:
        dists = (node_lats - lat) ** 2 + (node_lons - lon) ** 2
        idx = np.argmin(dists)
        result.append(node_ids[idx])
    return result


def shortest_path_geometry(G: nx.DiGraph, orig: int, dest: int) -> LineString | None:
    """Return LineString of shortest path by travel_time."""
    try:
        path = nx.shortest_path(G, orig, dest, weight="travel_time")
    except nx.NetworkXNoPath:
        return None
    coords = [(G.nodes[n]["x"], G.nodes[n]["y"]) for n in path]
    if len(coords) < 2:
        return None
    return LineString(coords)


def network_distance_m(G: nx.DiGraph, orig: int, dest: int) -> float:
    """Network distance in metres along the shortest travel_time path."""
    try:
        return nx.shortest_path_length(G, orig, dest, weight="length")
    except nx.NetworkXNoPath:
        return float("inf")


def compute_isochrone(G: nx.DiGraph, center_node: int, max_seconds: float) -> MultiPolygon | None:
    """Compute drive-time isochrone as convex hull of reachable nodes."""
    try:
        subgraph = nx.ego_graph(G, center_node, radius=max_seconds, distance="travel_time")
    except nx.NodeNotFound:
        return None

    node_points = [Point(data["x"], data["y"]) for _, data in subgraph.nodes(data=True)]
    if len(node_points) < 3:
        return None

    hull = unary_union(node_points).convex_hull
    if hull.geom_type == "Polygon":
        return MultiPolygon([hull])
    elif hull.geom_type == "MultiPolygon":
        return hull
    return None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outpath = OUTPUT_DIR / "emergency_routing.gpkg"

    print("Fetching hospitals from Overpass...")
    hospitals = fetch_hospitals()
    print(f"  Found {len(hospitals)} hospitals")

    print("Fetching road network from OSM...")
    G = fetch_road_network()

    # --- Incident points ---
    incidents_gdf = gpd.GeoDataFrame(
        {"incident_id": [f"INC_{i+1:03d}" for i in range(len(INCIDENT_COORDS_WGS84))]},
        geometry=[Point(lon, lat) for lat, lon in INCIDENT_COORDS_WGS84],
        crs=CRS_WGS84,
    )

    # Find nearest graph nodes
    incident_nodes = find_nearest_nodes_fast(G, INCIDENT_COORDS_WGS84)
    hospital_coords = [(row.geometry.y, row.geometry.x) for _, row in hospitals.iterrows()]
    hospital_nodes = find_nearest_nodes_fast(G, hospital_coords)

    # --- Closest hospital + shortest path ---
    print("Computing closest hospitals and shortest paths...")
    closest_rows = []
    for inc_id, inc_node in zip(incidents_gdf["incident_id"], incident_nodes):
        best_dist = float("inf")
        best_idx = None

        for j, hosp_node in enumerate(hospital_nodes):
            dist = network_distance_m(G, inc_node, hosp_node)
            if dist < best_dist:
                best_dist = dist
                best_idx = j

        if best_idx is not None and best_dist < float("inf"):
            path_geom = shortest_path_geometry(G, inc_node, hospital_nodes[best_idx])
            closest_rows.append({
                "incident_id": inc_id,
                "hospital_name": hospitals.iloc[best_idx]["name"],
                "hospital_osm_id": int(hospitals.iloc[best_idx]["osm_id"]),
                "network_distance_m": round(best_dist, 1),
                "geometry": path_geom,
            })

    closest_gdf = gpd.GeoDataFrame(closest_rows, crs=CRS_WGS84)

    # --- Distance matrix (each incident x 3 nearest hospitals) ---
    print("Computing distance matrix...")
    matrix_rows = []
    for inc_id, inc_node in zip(incidents_gdf["incident_id"], incident_nodes):
        dists = []
        for j, hosp_node in enumerate(hospital_nodes):
            d = network_distance_m(G, inc_node, hosp_node)
            dists.append((j, d))
        dists.sort(key=lambda x: x[1])
        for rank, (j, d) in enumerate(dists[:3], start=1):
            if d < float("inf"):
                matrix_rows.append({
                    "incident_id": inc_id,
                    "hospital_name": hospitals.iloc[j]["name"],
                    "hospital_osm_id": int(hospitals.iloc[j]["osm_id"]),
                    "rank": rank,
                    "network_distance_m": round(d, 1),
                })

    matrix_df = pd.DataFrame(matrix_rows)

    # --- Isochrones ---
    print("Computing 15-minute drive-time isochrones...")
    iso_rows = []
    for j, (hosp_node, (_, hosp_row)) in enumerate(
        zip(hospital_nodes, hospitals.iterrows())
    ):
        iso_geom = compute_isochrone(G, hosp_node, ISOCHRONE_SECONDS)
        if iso_geom is not None:
            iso_rows.append({
                "hospital_name": hosp_row["name"],
                "hospital_osm_id": int(hosp_row["osm_id"]),
                "travel_time_min": 15,
                "geometry": iso_geom,
            })

    iso_gdf = gpd.GeoDataFrame(iso_rows, crs=CRS_WGS84)

    # --- Reproject to Lambert-93 ---
    print("Reprojecting to EPSG:2154...")
    incidents_2154 = incidents_gdf.to_crs(CRS_OUT)
    closest_2154 = closest_gdf.to_crs(CRS_OUT) if len(closest_gdf) > 0 else closest_gdf
    iso_2154 = iso_gdf.to_crs(CRS_OUT) if len(iso_gdf) > 0 else iso_gdf

    # Sort deterministically
    incidents_2154 = incidents_2154.sort_values("incident_id").reset_index(drop=True)
    closest_2154 = closest_2154.sort_values("incident_id").reset_index(drop=True)
    matrix_df = matrix_df.sort_values(["incident_id", "rank"]).reset_index(drop=True)
    iso_2154 = iso_2154.sort_values("hospital_osm_id").reset_index(drop=True)

    # --- Write GPKG ---
    print(f"Writing {outpath}...")
    if outpath.exists():
        outpath.unlink()

    incidents_2154.to_file(outpath, layer="incidents", driver="GPKG")
    closest_2154.to_file(outpath, layer="closest_hospital", driver="GPKG")

    # Distance matrix: tabular layer with dummy geometry (GPKG needs geometry)
    matrix_gdf = gpd.GeoDataFrame(
        matrix_df,
        geometry=gpd.points_from_xy([0] * len(matrix_df), [0] * len(matrix_df)),
        crs=CRS_OUT,
    )
    matrix_gdf.to_file(outpath, layer="distance_matrix", driver="GPKG")

    iso_2154.to_file(outpath, layer="isochrones_15min", driver="GPKG")

    print("Done.")
    print(f"  incidents: {len(incidents_2154)} rows")
    print(f"  closest_hospital: {len(closest_2154)} rows")
    print(f"  distance_matrix: {len(matrix_df)} rows")
    print(f"  isochrones_15min: {len(iso_2154)} rows")


if __name__ == "__main__":
    main()
