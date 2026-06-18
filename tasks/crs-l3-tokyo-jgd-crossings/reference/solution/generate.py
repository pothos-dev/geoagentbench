"""Reference solution for crs-l3-tokyo-jgd-crossings.

Pipeline (live data):
1. Fetch Tokyo's 23 special wards (admin_level=7 boundary relations
   inside the Tokyo Metropolis area) from OSM Overpass.
2. Fetch the drivable highway network within the 23-wards bounding box
   from Overpass.
3. Reproject both layers from EPSG:4326 to EPSG:6677 (JGD2011 / Japan
   Plane Rectangular IX), the conformal national grid covering Tokyo,
   so geometric measurements are honest in metres.
4. Identify crossing points: for each (highway, ward) pair where the
   highway transversally crosses the ward's boundary line, compute the
   intersection geometry and record each Point as a "crossing" of that
   ward.
5. Build a 50 m planar buffer around each crossing point in JGD metres.
6. Intersect each buffer with the ward polygon that produced the
   crossing (the half-disc on that ward's side of the boundary).
7. Compute per-ward crossings_per_km2 from the count of crossings
   divided by the ward area in km^2 (JGD area).
8. Reproject the per-ward density layer back to EPSG:4326 for the
   public dashboard.
9. Write all five layers into a single multi-layer GPKG with mixed
   per-layer CRSes.

L3 drift note: two consecutive runs against live Overpass may differ
slightly because OSM is updated minute-by-minute. The grader's
tolerance windows (count +/-10%, area +/-10%, density per-ward
correlation) absorb realistic drift. To pin a specific OSM snapshot
during development, set the OSM_DATE environment variable to an ISO-
8601 timestamp; the script will inject an Overpass attic
``[date:"..."]`` directive. With no env var set, the live current
state is queried.

Determinism: outputs are sorted by stable IDs (OSM relation id for
wards; ward_id + osm_way_id + crossing_index for crossings/buffers).
The crossings_per_km2 metric is purely a function of feature counts
and ward areas, both of which are deterministic given a snapshot.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/crs-l3-tokyo-jgd-crossings/reference/solution/generate.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import (
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "tokyo_crossings.gpkg"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_HEADERS = {
    "User-Agent": "geo-bench-author/0.1 (research)",
    "Accept": "application/json",
}

# Tokyo's 23 special wards bbox with a small margin. Used to clip the
# Overpass highway query so we don't fetch all of Kanto.
TOKYO_BBOX_S, TOKYO_BBOX_W, TOKYO_BBOX_N, TOKYO_BBOX_E = 35.50, 139.55, 35.84, 139.93

# Drivable + minor-road highway tags. We exclude footways/cycleways/
# service roads to keep the network at a meaningful "road" scale and
# the Overpass response within practical limits.
HIGHWAY_REGEX = (
    "^("
    "motorway|trunk|primary|secondary|tertiary|"
    "motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|"
    "residential|unclassified|living_street"
    ")$"
)


def _date_directive() -> str:
    ts = os.environ.get("OSM_DATE", "").strip()
    return f'[date:"{ts}"]' if ts else ""


def _wards_query() -> str:
    date = _date_directive()
    return f"""
[out:json][timeout:300]{date};
area["name:en"="Tokyo"]["admin_level"="4"]->.tokyo;
(
  relation["boundary"="administrative"]["admin_level"="7"](area.tokyo);
);
out geom;
"""


def _highways_query() -> str:
    date = _date_directive()
    return f"""
[out:json][timeout:300]{date};
(
  way["highway"~"{HIGHWAY_REGEX}"]({TOKYO_BBOX_S},{TOKYO_BBOX_W},{TOKYO_BBOX_N},{TOKYO_BBOX_E});
);
out geom;
"""


def _overpass(query: str) -> dict:
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            r = requests.post(
                OVERPASS_URL,
                data={"data": query},
                headers=OVERPASS_HEADERS,
                timeout=600,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            print(f"Overpass attempt {attempt + 1} failed: {e}", file=sys.stderr)
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"Overpass query failed after 3 attempts: {last_err}")


# ---- Ring stitching for relation-based polygons --------------------


def _stitch_rings(
    ways: list[list[tuple[float, float]]],
) -> list[list[tuple[float, float]]]:
    pool = [list(w) for w in ways if len(w) >= 2]
    closed: list[list[tuple[float, float]]] = []
    while pool:
        ring = pool.pop(0)
        if ring[0] == ring[-1] and len(ring) >= 4:
            closed.append(ring)
            continue
        progressed = True
        while progressed and ring[0] != ring[-1]:
            progressed = False
            for i, candidate in enumerate(pool):
                if candidate[0] == ring[-1]:
                    ring.extend(candidate[1:])
                    pool.pop(i)
                    progressed = True
                    break
                if candidate[-1] == ring[-1]:
                    ring.extend(reversed(candidate[:-1]))
                    pool.pop(i)
                    progressed = True
                    break
                if candidate[0] == ring[0]:
                    ring[:0] = list(reversed(candidate[1:]))
                    pool.pop(i)
                    progressed = True
                    break
                if candidate[-1] == ring[0]:
                    ring[:0] = candidate[:-1]
                    pool.pop(i)
                    progressed = True
                    break
        if ring[0] == ring[-1] and len(ring) >= 4:
            closed.append(ring)
    return closed


def _build_polygon_from_relation(rel: dict) -> Polygon | MultiPolygon | None:
    outer_ways: list[list[tuple[float, float]]] = []
    inner_ways: list[list[tuple[float, float]]] = []
    for member in rel.get("members", []):
        if member.get("type") != "way":
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in member.get("geometry", [])]
        if len(coords) < 2:
            continue
        role = (member.get("role") or "outer").strip() or "outer"
        if role == "outer":
            outer_ways.append(coords)
        elif role == "inner":
            inner_ways.append(coords)

    closed_outer = _stitch_rings(outer_ways)
    if not closed_outer:
        return None
    closed_inner = _stitch_rings(inner_ways)
    inner_polys = [Polygon(r) for r in closed_inner]
    polys: list[Polygon] = []
    for outer in closed_outer:
        outer_poly = Polygon(outer)
        if not outer_poly.is_valid:
            outer_poly = outer_poly.buffer(0)
        if outer_poly.is_empty:
            continue
        holes = [
            list(ip.exterior.coords)
            for ip in inner_polys
            if outer_poly.contains(ip.representative_point())
        ]
        polys.append(Polygon(outer, holes))
    if not polys:
        return None
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


# ---- Fetchers ------------------------------------------------------


def fetch_wards() -> gpd.GeoDataFrame:
    print("Fetching Tokyo special-wards boundaries from Overpass ...")
    data = _overpass(_wards_query())
    rows = []
    for el in data.get("elements", []):
        if el.get("type") != "relation":
            continue
        tags = el.get("tags") or {}
        name_en = tags.get("name:en") or tags.get("int_name") or ""
        name = tags.get("name") or ""
        # Tokyo's 23 special wards have name:en ending with " Ward"
        # (e.g. "Chiyoda Ward") and the kanji name ending with "区".
        # The admin_level=7 set inside the Tokyo Metropolis area
        # in OSM is exactly the 23 special wards plus zero non-ward
        # entities, but we filter defensively.
        if "Ward" not in name_en and not name.endswith("区"):
            continue
        geom = _build_polygon_from_relation(el)
        if geom is None or geom.is_empty:
            continue
        rows.append(
            {
                "ward_id": int(el["id"]),
                "ward_name_en": name_en or None,
                "ward_name": name or None,
                "geometry": geom,
            }
        )
    if not rows:
        raise RuntimeError("Overpass returned no Tokyo special wards.")
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    # Repair anything not strictly valid.
    gdf["geometry"] = gdf.geometry.buffer(0)
    gdf = gdf.sort_values("ward_id", kind="stable").reset_index(drop=True)
    print(f"  -> {len(gdf)} wards")
    return gdf


def fetch_highways(wards_wgs: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    print("Fetching Tokyo highways from Overpass ...")
    data = _overpass(_highways_query())
    rows = []
    for el in data.get("elements", []):
        if el.get("type") != "way":
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in el.get("geometry", [])]
        if len(coords) < 2:
            continue
        rows.append(
            {
                "osm_way_id": int(el["id"]),
                "highway": (el.get("tags") or {}).get("highway"),
                "name": (el.get("tags") or {}).get("name"),
                "geometry": LineString(coords),
            }
        )
    if not rows:
        raise RuntimeError("Overpass returned no highways for Tokyo.")
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    # Restrict to highways that intersect the union of the 23 wards
    # (Overpass' bbox cut returns features in the rectangular extent,
    # which slightly overshoots the actual ward boundary).
    union = wards_wgs.unary_union
    gdf = gdf[gdf.geometry.intersects(union)].reset_index(drop=True)
    gdf = gdf.sort_values("osm_way_id", kind="stable").reset_index(drop=True)
    print(f"  -> {len(gdf)} highway segments")
    return gdf


# ---- Core analysis -------------------------------------------------


def _extract_points(geom: BaseGeometry) -> list[Point]:
    """Pull all 0D Point components out of an arbitrary intersection result."""
    if geom.is_empty:
        return []
    gtype = geom.geom_type
    if gtype == "Point":
        return [geom]
    if gtype == "MultiPoint":
        return list(geom.geoms)
    if gtype == "GeometryCollection":
        out: list[Point] = []
        for sub in geom.geoms:
            out.extend(_extract_points(sub))
        return out
    # LineString / Polygon intersections are coincident segments, not
    # crossings -- ignore.
    return []


def compute_crossings(
    highways_jgd: gpd.GeoDataFrame, wards_jgd: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """For each (highway, ward) where the highway transversally crosses
    the ward's boundary line, emit one row per intersection Point.
    """
    rows = []
    sindex = highways_jgd.sindex
    for _, ward in wards_jgd.iterrows():
        boundary = ward.geometry.boundary
        # Spatial-index prefilter on bbox.
        cand_idx = list(sindex.query(boundary, predicate="intersects"))
        for hi in cand_idx:
            highway = highways_jgd.iloc[hi]
            if not highway.geometry.crosses(boundary):
                continue
            inter = highway.geometry.intersection(boundary)
            pts = _extract_points(inter)
            for k, pt in enumerate(pts):
                rows.append(
                    {
                        "ward_id": int(ward.ward_id),
                        "ward_name_en": ward.ward_name_en,
                        "ward_name": ward.ward_name,
                        "osm_way_id": int(highway.osm_way_id),
                        "highway_class": highway.highway,
                        "crossing_index": k,
                        "geometry": pt,
                    }
                )
    if not rows:
        raise RuntimeError("Zero crossings detected -- something is off.")
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=wards_jgd.crs)
    gdf = gdf.sort_values(
        ["ward_id", "osm_way_id", "crossing_index"], kind="stable"
    ).reset_index(drop=True)
    print(f"  -> {len(gdf)} crossings across {gdf['ward_id'].nunique()} wards")
    return gdf


def build_buffers(crossings: gpd.GeoDataFrame, radius_m: float = 50.0) -> gpd.GeoDataFrame:
    buf = crossings.copy()
    buf["geometry"] = buf.geometry.buffer(radius_m)
    return buf


def buffer_ward_intersection(
    buffers: gpd.GeoDataFrame, wards_jgd: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    ward_geom_by_id = dict(zip(wards_jgd["ward_id"], wards_jgd.geometry))
    rows = []
    for _, b in buffers.iterrows():
        wgeom = ward_geom_by_id.get(int(b.ward_id))
        if wgeom is None:
            continue
        clipped = b.geometry.intersection(wgeom)
        if clipped.is_empty:
            continue
        rows.append(
            {
                "ward_id": int(b.ward_id),
                "ward_name_en": b.ward_name_en,
                "ward_name": b.ward_name,
                "osm_way_id": int(b.osm_way_id),
                "crossing_index": int(b.crossing_index),
                "geometry": clipped,
            }
        )
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=buffers.crs)
    gdf = gdf.sort_values(
        ["ward_id", "osm_way_id", "crossing_index"], kind="stable"
    ).reset_index(drop=True)
    return gdf


def density_layer(
    wards_jgd: gpd.GeoDataFrame, crossings: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    counts = (
        crossings.groupby("ward_id").size().rename("crossing_count").reset_index()
    )
    out = wards_jgd.merge(counts, on="ward_id", how="left")
    out["crossing_count"] = out["crossing_count"].fillna(0).astype(int)
    out["ward_area_km2"] = out.geometry.area / 1_000_000.0
    out["crossings_per_km2"] = out["crossing_count"] / out["ward_area_km2"]
    out_wgs = out.to_crs("EPSG:4326")
    out_wgs = out_wgs[
        [
            "ward_id",
            "ward_name_en",
            "ward_name",
            "crossing_count",
            "ward_area_km2",
            "crossings_per_km2",
            "geometry",
        ]
    ]
    out_wgs = out_wgs.sort_values("ward_id", kind="stable").reset_index(drop=True)
    return out_wgs


# ---- Driver --------------------------------------------------------


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    wards_wgs = fetch_wards()
    highways_wgs = fetch_highways(wards_wgs)

    # Engineering frame: JGD2011 / Japan Plane Rectangular IX.
    wards_jgd = wards_wgs.to_crs("EPSG:6677")
    highways_jgd = highways_wgs.to_crs("EPSG:6677")

    crossings = compute_crossings(highways_jgd, wards_jgd)
    buffers = build_buffers(crossings, radius_m=50.0)
    inter = buffer_ward_intersection(buffers, wards_jgd)
    density_wgs = density_layer(wards_jgd, crossings)

    # Slim wards layer
    wards_out = wards_jgd[
        ["ward_id", "ward_name_en", "ward_name", "geometry"]
    ].copy()
    wards_out = wards_out.sort_values("ward_id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()

    print(f"Writing multi-layer GPKG to {OUT}")
    wards_out.to_file(OUT, layer="wards_jgd", driver="GPKG")
    crossings.to_file(OUT, layer="crossing_points", driver="GPKG")
    buffers.to_file(OUT, layer="crossing_buffers_50m", driver="GPKG")
    inter.to_file(OUT, layer="buffer_ward_intersection", driver="GPKG")
    density_wgs.to_file(OUT, layer="ward_crossing_density_wgs84", driver="GPKG")

    # Quick preview
    print("\nPer-ward density preview:")
    preview = density_wgs.sort_values("crossings_per_km2", ascending=False)
    for _, r in preview.iterrows():
        print(
            f"  {int(r.ward_id):>10}  {str(r.ward_name_en or r.ward_name)[:24]:24s}  "
            f"count={int(r.crossing_count):>4}  "
            f"area_km2={r.ward_area_km2:>6.2f}  "
            f"density={r.crossings_per_km2:>7.3f}"
        )
    print(f"\nLayers: wards={len(wards_out)} crossings={len(crossings)} "
          f"buffers={len(buffers)} intersection={len(inter)} "
          f"density={len(density_wgs)}")


if __name__ == "__main__":
    main()
