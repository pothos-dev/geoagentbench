"""Authoring-time helper: build the bundled Vienna stations + districts GeoJSON.

Run once at authoring time inside the project's Docker container. The
two outputs (``stations.geojson``, ``districts.geojson``) are committed
to the repo and served to systems under test by the harness. Do not
run this at grading time.

Source: OpenStreetMap via Overpass attic query at a pinned timestamp.

Why OSM and not Overture: the inventory's OSM-tag axis names
``boundary=administrative`` (for the 23 Vienna Bezirke as polygons)
and ``place=*`` / ``man_made=monitoring_station`` (for environmental
monitoring points). Overture's ``divisions/division_area`` does not
expose Vienna's 23 statutory ``Gemeindebezirke`` cleanly: a probe of
release 2026-04-15.0 returns only 21 ``subtype='macrohood'`` rows
covering Vienna, and the set is *not* the 23 Bezirke — it includes
sub-Bezirk locales (Spittelberg, Schottenfeld), excludes whole
Bezirke (Wieden, Neubau, Alsergrund, Rudolfsheim-Fünfhaus, Döbling,
Donaustadt), and mixes ``Katastralgemeinden`` ("KG ...") into the
same subtype. OSM's ``boundary=administrative admin_level=9``
relations under Vienna give a clean 23 — one per Bezirk, with the
official Bezirk number in the ``ref`` tag and the German Bezirk name
in ``name``. Overpass also has ``man_made=monitoring_station`` for
the environmental stations the persona references. Recorded under
``audit/AUTHORING_HISTORY.md > Open issues`` so the orchestrator can
audit the OSM-vs-Overture choice.

Determinism: the Overpass ``[date:"YYYY-MM-DDTHH:MM:SSZ"]`` directive
returns the historical OSM state at that timestamp, so two runs
fetched months apart produce the same elements. Both layers are
sorted by OSM id before writing.

Output schemas:

  * ``districts.geojson`` (Polygon / MultiPolygon, EPSG:31287, 23 rows):
      - ``district_code`` (int) — the official Bezirk number 1..23
        (parsed from the OSM ``ref`` tag).
      - ``district_name`` (string) — the OSM ``name`` tag verbatim
        ("Innere Stadt", "Leopoldstadt", …, "Liesing"). German
        diacritics preserved (Währing, Döbling, Landstraße).
      - ``osm_relation_id`` (int) — the OSM relation id, kept for
        provenance.

  * ``stations.geojson`` (Point, EPSG:31287, ~50 rows):
      - ``station_id`` (int) — the OSM node id.
      - ``name`` (string, nullable) — OSM ``name`` tag if present.

The persona's deliverable joins on the polygon set (one CSV row per
of the 23 districts) and counts stations within each. The bundled
extract is constructed so that a non-zero number of districts have
zero stations — coverage gaps are the whole point of the persona's
diagnostic — and several districts have multiple stations.

Run:
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work \\
        geo-bench-author uv run python \\
        tasks/spa-l1-vienna-pip-count/inputs/_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import MultiPolygon, Point, Polygon, shape

HERE = Path(__file__).resolve().parent
DISTRICTS_OUT = HERE / "districts.geojson"
STATIONS_OUT = HERE / "stations.geojson"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMESTAMP = "2026-05-01T00:00:00Z"
OVERPASS_HEADERS = {
    "User-Agent": "geo-bench-author/0.1 (research)",
    "Accept": "application/json",
}

DISTRICTS_QUERY = f"""
[out:json][timeout:120][date:"{OVERPASS_TIMESTAMP}"];
area["ISO3166-2"="AT-9"][admin_level=4]->.vienna;
(
  relation["boundary"="administrative"]["admin_level"="9"](area.vienna);
);
out geom;
"""

STATIONS_QUERY = f"""
[out:json][timeout:120][date:"{OVERPASS_TIMESTAMP}"];
area["ISO3166-2"="AT-9"][admin_level=4]->.vienna;
(
  node["man_made"="monitoring_station"](area.vienna);
);
out body;
"""


def _overpass(query: str) -> dict:
    r = requests.post(OVERPASS_URL, data={"data": query}, headers=OVERPASS_HEADERS, timeout=180)
    r.raise_for_status()
    return r.json()


def _stitch_rings(
    ways: list[list[tuple[float, float]]],
) -> list[list[tuple[float, float]]]:
    """Greedy ring builder: glue ways with matching endpoints into closed rings.

    Each ``way`` is a list of (lon, lat) vertices. We repeatedly pick an
    unused way as the seed of a ring, then keep extending the ring by
    finding a way whose first or last vertex matches the ring's open
    endpoint (reversing the way if needed), until the ring closes.
    Already-closed ways become rings on their own. Discards any
    fragments left over.
    """
    pool = [list(w) for w in ways if len(w) >= 2]
    closed: list[list[tuple[float, float]]] = []

    while pool:
        ring = pool.pop(0)
        # Maybe this single way is already closed.
        if ring[0] == ring[-1] and len(ring) >= 4:
            closed.append(ring)
            continue
        # Otherwise extend it with adjacent ways from the pool.
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
        # else: dangling fragment, discard.
    return closed


def _build_polygon_from_relation(rel: dict) -> Polygon | MultiPolygon:
    """Stitch outer/inner ways from an Overpass relation into a (Multi)Polygon."""
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
    closed_inner = _stitch_rings(inner_ways)

    if not closed_outer:
        raise RuntimeError(
            f"Could not assemble any closed outer ring for relation {rel.get('id')}."
        )

    inner_polys = [Polygon(r) for r in closed_inner]
    polys = []
    for outer in closed_outer:
        outer_poly = Polygon(outer)
        holes = [
            list(ip.exterior.coords)
            for ip in inner_polys
            if outer_poly.contains(ip.representative_point())
        ]
        polys.append(Polygon(outer, holes))

    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def _fetch_districts() -> gpd.GeoDataFrame:
    data = _overpass(DISTRICTS_QUERY)
    rows = []
    for rel in data["elements"]:
        if rel.get("type") != "relation":
            continue
        tags = rel.get("tags", {})
        ref = tags.get("ref")
        name = tags.get("name")
        if ref is None or name is None:
            continue
        try:
            district_code = int(ref)
        except ValueError:
            continue
        if not (1 <= district_code <= 23):
            continue
        geom = _build_polygon_from_relation(rel)
        rows.append(
            {
                "district_code": district_code,
                "district_name": name,
                "osm_relation_id": rel["id"],
                "geometry": geom,
            }
        )
    if len(rows) != 23:
        raise RuntimeError(f"Expected 23 Vienna Bezirke; got {len(rows)}.")
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    gdf = gdf.sort_values("district_code", kind="stable").reset_index(drop=True)
    return gdf


def _fetch_stations() -> gpd.GeoDataFrame:
    data = _overpass(STATIONS_QUERY)
    rows = []
    for el in data["elements"]:
        if el.get("type") != "node":
            continue
        tags = el.get("tags", {})
        rows.append(
            {
                "station_id": el["id"],
                "name": tags.get("name"),
                "geometry": Point(el["lon"], el["lat"]),
            }
        )
    if not rows:
        raise RuntimeError("Overpass returned zero monitoring stations.")
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    gdf = gdf.sort_values("station_id", kind="stable").reset_index(drop=True)
    return gdf


def main() -> None:
    districts_wgs = _fetch_districts()
    stations_wgs = _fetch_stations()

    districts = districts_wgs.to_crs("EPSG:31287")
    stations = stations_wgs.to_crs("EPSG:31287")

    # Drop stations whose location does not fall inside any Bezirk —
    # Overpass area-bounded queries occasionally include nodes near the
    # Vienna boundary that are technically in Niederösterreich. Keeping
    # them would push the station_count totals off the 23-Bezirk
    # accounting the persona expects.
    union = districts.union_all()
    inside_mask = stations.geometry.within(union)
    stations = stations[inside_mask].reset_index(drop=True)

    if DISTRICTS_OUT.exists():
        DISTRICTS_OUT.unlink()
    if STATIONS_OUT.exists():
        STATIONS_OUT.unlink()

    districts.to_file(DISTRICTS_OUT, driver="GeoJSON")
    stations.to_file(STATIONS_OUT, driver="GeoJSON")

    print(f"Wrote {DISTRICTS_OUT}  ({len(districts)} districts)")
    print(f"Wrote {STATIONS_OUT}  ({len(stations)} stations)")
    # Quick coverage preview
    joined = gpd.sjoin(stations, districts, how="left", predicate="within")
    counts = joined.groupby(["district_code", "district_name"]).size()
    full = (
        districts[["district_code", "district_name"]]
        .merge(
            counts.rename("station_count").reset_index(),
            on=["district_code", "district_name"],
            how="left",
        )
        .fillna({"station_count": 0})
    )
    full["station_count"] = full["station_count"].astype(int)
    print("Coverage preview (district_code, district_name, station_count):")
    for _, r in full.iterrows():
        print(
            f"  {r['district_code']:2d}  {r['district_name']:25s}  "
            f"{r['station_count']}"
        )


if __name__ == "__main__":
    main()
