"""Visualisation for fio-l2-cairo-mixedgeom-split.

Auto-loaded by the eval runner after grading. See
``benchmark/eval/eval/core/viz.py`` for the shared tippecanoe + reprojection
helper.
"""

from __future__ import annotations

from pathlib import Path

from eval.core.viz import make_layer


def visualize(outputs_dir: Path, out_dir: Path) -> list[dict]:
    return [
        make_layer(
            outputs_dir, out_dir,
            src_filename='heritage.gpkg',
            layer_name='points',
            geometry_type='Point',
            gpkg_layer='points',
            tooltip=['site_id'],
        ),
        make_layer(
            outputs_dir, out_dir,
            src_filename='heritage.gpkg',
            layer_name='lines',
            geometry_type='LineString',
            gpkg_layer='lines',
            tooltip=['site_id'],
        ),
        make_layer(
            outputs_dir, out_dir,
            src_filename='heritage.gpkg',
            layer_name='polygons',
            geometry_type='Polygon',
            gpkg_layer='polygons',
            tooltip=['site_id'],
        ),
    ]
