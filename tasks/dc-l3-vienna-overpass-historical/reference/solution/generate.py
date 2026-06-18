"""Reference solution for dc-l3-vienna-overpass-historical.

Pipeline (live data):
1. Fetch Vienna's 23 Bezirke (admin_level=9) from Overpass — current.
2. Fetch the same set at [date:"2014-01-01T00:00:00Z"] via Overpass attic.
3. Normalise district names (strip Wien- prefix, numbering, casing drift).
4. Per matched district, compute:
   - unchanged = intersection(current, 2014)
   - added_since_2014 = difference(current, 2014)
   - removed_since_2014 = difference(2014, current)
5. Cascaded-union fragments sharing the same (district, change_type).
6. Compute touches_changed per district (intersects any changed geometry).
7. Write single GeoJSON FeatureCollection in EPSG:4326.

L3 drift note: the "current" snapshot changes with OSM edits; the 2014
snapshot is pinned via Overpass attic. Two consecutive runs may differ
because of current-side drift. The grader's tolerance windows absorb
realistic drift.

Determinism within a run: outputs sorted by (change_type, district_name).

Run:
    cd eval && uv run python tasks/dc-l3-vienna-overpass-historical/reference/solution/generate.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "vienna_boundary_changes.geojson"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_HEADERS = {
    "User-Agent": "geo-bench-author/0.1 (research)",
    "Accept": "application/json",
}

# Vienna bbox with margin — used as fallback if area query fails.
VIENNA_BBOX = (48.10, 16.17, 48.34, 16.58)


# ---- Overpass helpers --------------------------------------------------


def _overpass(query: str) -> dict:
    """POST an Overpass query with retries."""
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
    raise RuntimeError(f"Overpass failed after 3 attempts: {last_err}")


def _districts_query(date: str | None = None) -> str:
    """Build Overpass QL for Vienna Bezirke, optionally at a historical date."""
    date_dir = f'[date:"{date}"]' if date else ""
    return f"""
[out:json][timeout:600]{date_dir};
area["name"="Wien"]["admin_level"="4"]->.vienna;
(
  relation["boundary"="administrative"]["admin_level"="9"](area.vienna);
);
out geom;
"""


def _districts_query_bbox(date: str | None = None) -> str:
    """Fallback: bbox-based query if area lookup fails in attic mode."""
    date_dir = f'[date:"{date}"]' if date else ""
    s, w, n, e = VIENNA_BBOX
    return f"""
[out:json][timeout:600]{date_dir};
(
  relation["boundary"="administrative"]["admin_level"="9"]({s},{w},{n},{e});
);
out geom;
"""


# ---- Ring stitching (relation → polygon) --------------------------------


def _stitch_rings(
    ways: list[list[tuple[float, float]]],
) -> list[list[tuple[float, float]]]:
    """Stitch way segments into closed rings."""
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


def _build_polygon(rel: dict) -> Polygon | MultiPolygon | None:
    """Build a Polygon/MultiPolygon from an OSM relation's members."""
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
            outer_poly = make_valid(outer_poly)
        if outer_poly.is_empty:
            continue
        if not isinstance(outer_poly, Polygon):
            # make_valid may return a MultiPolygon; take parts individually
            for part in (
                outer_poly.geoms if hasattr(outer_poly, "geoms") else [outer_poly]
            ):
                if isinstance(part, Polygon) and not part.is_empty:
                    polys.append(part)
            continue
        holes = [
            list(ip.exterior.coords)
            for ip in inner_polys
            if outer_poly.contains(ip.representative_point())
        ]
        polys.append(Polygon(outer_poly.exterior, holes))
    if not polys:
        return None
    result = polys[0] if len(polys) == 1 else MultiPolygon(polys)
    if not result.is_valid:
        result = make_valid(result)
    return result


# ---- Name normalisation ------------------------------------------------


def normalize_district_name(raw: str) -> str:
    """Normalise a Vienna district name to a canonical form.

    Handles variations like:
      "Wien-Innere Stadt" -> "Innere Stadt"
      "Wien, 02. Leopoldstadt" -> "Leopoldstadt"
      "1. Bezirk, Innere Stadt" -> "Innere Stadt"
      "Innere Stadt" -> "Innere Stadt"
    """
    s = raw.strip()
    # Remove "Wien" prefix with various separators
    s = re.sub(r"^Wien\s*[-,/]\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^Wien\s+", "", s, flags=re.IGNORECASE)
    # Remove leading district number ("01.", "1.", "02. ", etc.)
    s = re.sub(r"^\d{1,2}\.\s*", "", s)
    # Remove standalone "Bezirk" or "bezirk"
    s = re.sub(r"\bBezirk\b[,]?\s*", "", s, flags=re.IGNORECASE)
    # Clean up whitespace
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(",").strip()
    return s


# ---- Geometry helpers ---------------------------------------------------


def _to_multipolygon(geom) -> MultiPolygon | None:
    """Coerce geometry to MultiPolygon, discarding non-polygonal parts."""
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        geom = make_valid(geom)
    if geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    # GeometryCollection — extract polygonal parts
    parts: list[Polygon] = []
    for g in getattr(geom, "geoms", []):
        if g.geom_type == "Polygon" and not g.is_empty:
            parts.append(g)
        elif g.geom_type == "MultiPolygon":
            parts.extend(p for p in g.geoms if not p.is_empty)
    return MultiPolygon(parts) if parts else None


# ---- Fetcher ------------------------------------------------------------


def fetch_districts(date: str | None = None) -> gpd.GeoDataFrame:
    """Fetch Vienna Bezirke from Overpass, optionally at a historical date."""
    label = date or "current"
    print(f"Fetching Vienna districts ({label}) from Overpass ...")

    # Try area-based query first; fall back to bbox if empty.
    data = _overpass(_districts_query(date))
    elements = [e for e in data.get("elements", []) if e.get("type") == "relation"]
    if len(elements) < 10:
        print(f"  Area query returned only {len(elements)} relations, trying bbox ...",
              file=sys.stderr)
        data = _overpass(_districts_query_bbox(date))
        elements = [e for e in data.get("elements", []) if e.get("type") == "relation"]

    rows = []
    for el in elements:
        tags = el.get("tags") or {}
        raw_name = tags.get("name", "")
        if not raw_name:
            continue
        geom = _build_polygon(el)
        if geom is None or geom.is_empty:
            continue
        rows.append(
            {
                "osm_id": int(el["id"]),
                "raw_name": raw_name,
                "district_name": normalize_district_name(raw_name),
                "geometry": geom,
            }
        )
    if not rows:
        raise RuntimeError(f"Overpass returned no Vienna districts for {label}.")
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    # Repair invalid geometries.
    gdf["geometry"] = gdf.geometry.apply(
        lambda g: make_valid(g) if not g.is_valid else g
    )
    gdf = gdf.sort_values("district_name", kind="stable").reset_index(drop=True)
    print(f"  -> {len(gdf)} districts ({label})")
    for _, r in gdf.iterrows():
        print(f"     {r.raw_name!r:40s} -> {r.district_name!r}")
    return gdf


# ---- Core pipeline ------------------------------------------------------


def compute_changes(
    current: gpd.GeoDataFrame, historical: gpd.GeoDataFrame
) -> list[dict]:
    """Compute per-district symmetric difference and intersection."""
    current_by_name = {}
    for _, r in current.iterrows():
        current_by_name[r.district_name] = r.geometry
    historical_by_name = {}
    for _, r in historical.iterrows():
        historical_by_name[r.district_name] = r.geometry

    all_names = sorted(set(current_by_name) | set(historical_by_name))
    features: list[dict] = []

    for name in all_names:
        cur = current_by_name.get(name)
        hist = historical_by_name.get(name)

        if cur is not None and hist is not None:
            # Both snapshots — compute set operations
            unchanged = cur.intersection(hist)
            added = cur.difference(hist)
            removed = hist.difference(cur)
            for change_type, geom in [
                ("unchanged", unchanged),
                ("added_since_2014", added),
                ("removed_since_2014", removed),
            ]:
                mp = _to_multipolygon(geom)
                if mp is not None and not mp.is_empty:
                    features.append(
                        {
                            "district_name": name,
                            "change_type": change_type,
                            "geometry": mp,
                        }
                    )
        elif cur is not None:
            # Only in current — entirely added
            mp = _to_multipolygon(cur)
            if mp is not None:
                features.append(
                    {
                        "district_name": name,
                        "change_type": "added_since_2014",
                        "geometry": mp,
                    }
                )
        else:
            # Only in historical — entirely removed
            mp = _to_multipolygon(hist)
            if mp is not None:
                features.append(
                    {
                        "district_name": name,
                        "change_type": "removed_since_2014",
                        "geometry": mp,
                    }
                )

    return features


def add_touches_changed(features: list[dict]) -> list[dict]:
    """Flag each district that neighbours any changed geometry."""
    changed_geoms = [
        f["geometry"]
        for f in features
        if f["change_type"] in ("added_since_2014", "removed_since_2014")
    ]
    if not changed_geoms:
        for f in features:
            f["touches_changed"] = False
        return features

    changed_union = unary_union(changed_geoms)

    # Per-district: union all of its geometries, check intersection.
    district_geoms: dict[str, list] = {}
    for f in features:
        district_geoms.setdefault(f["district_name"], []).append(f["geometry"])

    district_flag: dict[str, bool] = {}
    for name, geoms in district_geoms.items():
        full = unary_union(geoms)
        district_flag[name] = bool(full.intersects(changed_union))

    for f in features:
        f["touches_changed"] = district_flag[f["district_name"]]
    return features


def write_geojson(features: list[dict], path: Path) -> None:
    """Write features as a GeoJSON FeatureCollection."""
    features.sort(key=lambda f: (f["change_type"], f["district_name"]))
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": mapping(f["geometry"]),
                "properties": {
                    "district_name": f["district_name"],
                    "change_type": f["change_type"],
                    "touches_changed": f["touches_changed"],
                },
            }
            for f in features
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(fc, fh, indent=2)
    print(f"Wrote {len(features)} features to {path}")


# ---- Driver -------------------------------------------------------------


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    current = fetch_districts(date=None)
    # Pause to respect Overpass rate limits.
    print("Pausing 10 s before historical query ...")
    time.sleep(10)
    historical = fetch_districts(date="2014-01-01T00:00:00Z")

    # Filter historical districts to only those that overlap significantly
    # with the current Vienna coverage. The 2014 area query sometimes
    # returns nearby municipalities (e.g. Gerasdorf bei Wien) that were
    # tagged admin_level=9 in error or whose boundary overlapped the
    # Vienna area at that time.
    vienna_union = unary_union(current.geometry.tolist())
    keep = []
    for idx, row in historical.iterrows():
        overlap = row.geometry.intersection(vienna_union).area
        if overlap / row.geometry.area > 0.5:
            keep.append(idx)
        else:
            print(f"  Filtering out historical district {row.raw_name!r} "
                  f"(overlap {overlap / row.geometry.area:.1%})")
    historical = historical.loc[keep].reset_index(drop=True)
    print(f"  -> {len(historical)} historical districts after filtering")

    features = compute_changes(current, historical)
    features = add_touches_changed(features)
    write_geojson(features, OUT)

    # ---- Summary --------------------------------------------------------
    from collections import Counter

    ct = Counter(f["change_type"] for f in features)
    tc = sum(1 for f in features if f["touches_changed"])
    print(f"\nSummary: {dict(ct)}")
    print(f"Features with touches_changed=True: {tc}/{len(features)}")
    for change_type in ["unchanged", "added_since_2014", "removed_since_2014"]:
        geoms = [f["geometry"] for f in features if f["change_type"] == change_type]
        if geoms:
            total_area = sum(g.area for g in geoms)
            print(
                f"  {change_type}: {len(geoms)} features, "
                f"total area (deg^2) = {total_area:.10f}"
            )


if __name__ == "__main__":
    main()
