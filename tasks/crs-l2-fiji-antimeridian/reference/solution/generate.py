"""Reference solution for crs-l2-fiji-antimeridian.

Pipeline:
1. Read the bundled Fiji-transect GeoJSON in EPSG:4326. Some LineStrings
   violate RFC 7946 §3.1.9: their consecutive vertices straddle ±180°
   without a discontinuity, so a single LineString purports to span
   ~359° of longitude.
2. For each transect, walk consecutive vertex pairs; whenever a pair's
   longitude difference exceeds 180°, the segment crosses the
   antimeridian. Insert an interpolated vertex at ±180°, snap the next
   vertex to the matching -/+180°, and start a new sub-line. The
   per-feature output is therefore a list of one or more LineString
   parts that, together, cover the transect without wrapping the long
   way around the globe.
3. Reproject each sub-line into EPSG:3460 (Fiji 1986 / Fiji Map Grid)
   and assemble the parts into a single MultiLineString per transect.
4. Compute `length_m` as the sum of part lengths in the projected CRS.
5. Sort by `transect_id` for byte-stable output and write GeoJSON.

Determinism: input is sorted by transect_id; we sort the output again
defensively. No random state, no dict-ordering reliance.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import transform as shp_transform
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent.parent.parent
INPUT = TASK_DIR / "inputs" / "fiji_transects_wgs84.geojson"
OUTPUTS = HERE / "outputs"
OUT = OUTPUTS / "fiji_transects_fmg.geojson"

ANTIMERIDIAN_THRESHOLD_DEG = 180.0


def _split_at_antimeridian(line: LineString) -> list[list[tuple[float, float]]]:
    """Split a single LineString into parts that do not cross ±180°.

    Walks consecutive vertex pairs. When the absolute longitude
    difference of a pair exceeds 180° the segment is encoded across
    the antimeridian; we interpolate the latitude at lon=±180°,
    terminate the current part there, and begin a new part on the
    matching opposite side.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return [coords]

    parts: list[list[tuple[float, float]]] = [[(coords[0][0], coords[0][1])]]

    for i in range(1, len(coords)):
        x0, y0 = coords[i - 1][0], coords[i - 1][1]
        x1, y1 = coords[i][0], coords[i][1]
        dx = x1 - x0
        if abs(dx) > ANTIMERIDIAN_THRESHOLD_DEG:
            # Adjust x1 by ±360 so the segment runs the *short* way and
            # can be linearly interpolated. dx > 180 means x1 jumped
            # forward (e.g. 179 → -179 yields dx = -358; that's the
            # other branch). dx > 180 means x1 jumped a long way
            # forward, so its true position is 360 lower.
            if dx > ANTIMERIDIAN_THRESHOLD_DEG:
                adj_x1 = x1 - 360.0
            else:
                adj_x1 = x1 + 360.0
            # Sign of the boundary the segment crosses (= sign of x0).
            sign = 1.0 if x0 >= 0 else -1.0
            target_lon = sign * 180.0
            denom = adj_x1 - x0
            t = (target_lon - x0) / denom if denom != 0 else 0.0
            lat_at_boundary = y0 + t * (y1 - y0)
            parts[-1].append((target_lon, lat_at_boundary))
            parts.append([(-target_lon, lat_at_boundary), (x1, y1)])
        else:
            parts[-1].append((x1, y1))

    # Drop any degenerate single-vertex parts that could arise if a
    # segment's endpoint sits exactly on ±180° (doesn't happen with the
    # bundled input but is cheap insurance).
    return [p for p in parts if len(p) >= 2]


def _project_parts_to_fmg(
    parts_lonlat: list[list[tuple[float, float]]],
    transformer: Transformer,
) -> list[LineString]:
    """Reproject each WGS84 part to EPSG:3460, return list of LineStrings."""
    projected: list[LineString] = []
    for part in parts_lonlat:
        line = LineString(part)
        projected.append(shp_transform(transformer.transform, line))
    return projected


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(INPUT)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3460", always_xy=True)

    out_geoms: list[MultiLineString] = []
    out_lengths: list[float] = []

    for geom in gdf.geometry:
        # The bundled input is LineString-only by construction; defensive
        # handling of a single-part MultiLineString is included so
        # downstream changes to the input format do not silently drop
        # data.
        if isinstance(geom, LineString):
            base_lines = [geom]
        elif isinstance(geom, MultiLineString):
            base_lines = list(geom.geoms)
        else:
            raise TypeError(f"unexpected geometry type: {type(geom).__name__}")

        all_parts_lonlat: list[list[tuple[float, float]]] = []
        for line in base_lines:
            all_parts_lonlat.extend(_split_at_antimeridian(line))

        projected_parts = _project_parts_to_fmg(all_parts_lonlat, transformer)
        multi = MultiLineString(projected_parts)
        out_geoms.append(multi)
        out_lengths.append(float(multi.length))

    out = gpd.GeoDataFrame(
        {
            "transect_id": gdf["transect_id"].values,
            "vessel": gdf["vessel"].values,
            "survey_date": gdf["survey_date"].values,
            "length_m": out_lengths,
        },
        geometry=out_geoms,
        crs="EPSG:3460",
    )

    out = out.sort_values("transect_id", kind="stable").reset_index(drop=True)

    if OUT.exists():
        OUT.unlink()
    out.to_file(OUT, driver="GeoJSON")
    print(f"Wrote {len(out)} transects to {OUT}")
    print(f"CRS: {out.crs.to_epsg()}")
    print(f"Geom types: {sorted(set(out.geometry.geom_type.unique()))}")
    print(
        "length_m: min={:.1f}, max={:.1f}, mean={:.1f}".format(
            out["length_m"].min(), out["length_m"].max(), out["length_m"].mean()
        )
    )


if __name__ == "__main__":
    main()
