# /// script
# requires-python = ">=3.12"
# dependencies = ["geopandas", "shapely", "pyproj", "pyogrio", "pyarrow"]
# ///

import geopandas as gpd
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────────
TASK_DIR = Path(__file__).parent
INPUT     = TASK_DIR / "inputs" / "tokyo_connectors.geojson"
OUTPUT    = TASK_DIR / "tokyo_stop_catchments.geoparquet"

TARGET_CRS = "EPSG:6677"   # JGD2011 / Japan Plane Rectangular CS IX  (unit: metres)
BUFFER_M   = 400.0

# ── load ───────────────────────────────────────────────────────────────────────
connectors = gpd.read_file(INPUT)
print(f"Loaded {len(connectors):,} connectors  |  source CRS: {connectors.crs}")

# ── reproject to the metric grid (if not already there) ────────────────────────
if connectors.crs is None:
    raise ValueError("Input has no CRS — cannot reproject safely.")

connectors = connectors.to_crs(TARGET_CRS)
print(f"Reprojected to {connectors.crs}  |  units: {connectors.crs.axis_info[0].unit_name}")

# ── buffer in metres ───────────────────────────────────────────────────────────
catchments = connectors.copy()
catchments["geometry"] = connectors.geometry.buffer(BUFFER_M)

# sanity-check: make sure we got Polygons and the area is plausible
import math
expected_area = math.pi * BUFFER_M**2          # ≈ 502 654 m²
actual_area   = catchments.geometry.area.mean()
print(f"Mean catchment area: {actual_area:,.1f} m²  (ideal circle: {expected_area:,.1f} m²)")
assert 0.99 * expected_area <= actual_area <= 1.01 * expected_area, \
    f"Area out of tolerance — CRS or buffer units may be wrong: {actual_area}"

# ── write GeoParquet ───────────────────────────────────────────────────────────
catchments.to_parquet(OUTPUT, index=False)
print(f"Written → {OUTPUT}  ({len(catchments):,} rows, CRS: {catchments.crs})")
