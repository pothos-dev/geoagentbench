"""Shared helpers used by per-task ``visualize.py`` modules.

Each task that produces a vector geometry output writes a tiny
``visualize.py`` that calls :func:`make_layer` once per layer it wants to
expose to the UI map. The helper reprojects to EPSG:4326, runs
``tippecanoe`` to produce a ``.pmtiles`` file, and returns the layer
spec the runner serialises into ``layers.json``.

Tippecanoe is a hard system dependency for visualisation. Install with
``pacman -S tippecanoe`` (or the AUR equivalent). The runner catches
missing-tippecanoe errors per task and records them in
``layers.json``'s ``error`` field; they do not affect scoring.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Any

import geopandas as gpd


def generate_layers(visualize_py: Path, outputs_dir: Path, out_dir: Path) -> dict[str, Any]:
    """Run a task's ``visualize.py`` and write ``layers.json`` to ``out_dir``.

    Returns the manifest dict that was written. Errors are captured into the
    manifest's ``error`` field — they never raise."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        spec = importlib.util.spec_from_file_location(
            f"_viz_{visualize_py.parent.name.replace('-', '_')}", visualize_py
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        layers = mod.visualize(outputs_dir, out_dir)
        manifest = {"layers": layers, "error": None}
    except Exception:
        manifest = {"layers": [], "error": traceback.format_exc()}
    (out_dir / "layers.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest

_DEFAULT_COLOR = "#1a4480"


def make_layer(
    outputs_dir: Path,
    out_dir: Path,
    src_filename: str,
    layer_name: str,
    geometry_type: str,
    *,
    gpkg_layer: str | None = None,
    style: dict[str, Any] | None = None,
    tooltip: list[str] | None = None,
    max_zoom: int = 14,
) -> dict[str, Any]:
    """Produce one pmtiles layer from a single output file.

    ``geometry_type`` is the human label exposed to the UI for picking a
    default style ("Polygon" / "LineString" / "Point" / "MultiPolygon"
    etc). ``gpkg_layer`` selects a specific layer when ``src_filename``
    is a multi-layer container (GPKG)."""
    src = outputs_dir / src_filename
    if not src.is_file():
        raise FileNotFoundError(f"output not found: {src}")
    if shutil.which("tippecanoe") is None:
        raise RuntimeError(
            "tippecanoe not found on PATH — install with `pacman -S tippecanoe`"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_geojson = out_dir / f"_{layer_name}.geojson"
    pmtiles = out_dir / f"{layer_name}.pmtiles"

    _to_wgs84_geojson(src, tmp_geojson, gpkg_layer=gpkg_layer)
    _run_tippecanoe(tmp_geojson, pmtiles, layer_name, max_zoom=max_zoom)
    tmp_geojson.unlink(missing_ok=True)

    return {
        "name": layer_name,
        "pmtiles": pmtiles.name,
        "source_layer": layer_name,
        "geometry_type": geometry_type,
        "style": style or _default_style(geometry_type),
        "tooltip": tooltip or [],
    }


def _to_wgs84_geojson(
    src: Path,
    dst: Path,
    *,
    gpkg_layer: str | None = None,
) -> None:
    suffix = src.suffix.lower()
    if suffix in (".geoparquet", ".parquet"):
        gdf = gpd.read_parquet(src)
    elif gpkg_layer is not None:
        gdf = gpd.read_file(src, layer=gpkg_layer)
    else:
        gdf = gpd.read_file(src)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    if dst.exists():
        dst.unlink()
    gdf.to_file(dst, driver="GeoJSON")


def _run_tippecanoe(
    geojson: Path,
    pmtiles: Path,
    layer_name: str,
    *,
    max_zoom: int,
) -> None:
    cmd = [
        "tippecanoe",
        "-o", str(pmtiles),
        "-l", layer_name,
        "-z", str(max_zoom),
        "--drop-densest-as-needed",
        "--read-parallel",
        "--force",
        str(geojson),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"tippecanoe failed for {layer_name!r}: "
            f"{proc.stderr.strip()[:500]}"
        )


def _default_style(geometry_type: str) -> dict[str, Any]:
    g = geometry_type.lower()
    if "polygon" in g:
        return {
            "fill-color": _DEFAULT_COLOR,
            "fill-opacity": 0.45,
            "fill-outline-color": _DEFAULT_COLOR,
        }
    if "line" in g:
        return {"line-color": _DEFAULT_COLOR, "line-width": 2}
    if "point" in g:
        return {
            "circle-color": _DEFAULT_COLOR,
            "circle-radius": 4,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1,
        }
    return {}
