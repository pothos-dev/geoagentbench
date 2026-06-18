"""Visualisation for crs-l3-tokyo-jgd-crossings.

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
            src_filename='tokyo_crossings.gpkg',
            layer_name='wards_jgd',
            geometry_type='Polygon',
            gpkg_layer='wards_jgd',
            tooltip=['ward_id'],
        ),
        make_layer(
            outputs_dir, out_dir,
            src_filename='tokyo_crossings.gpkg',
            layer_name='crossing_points',
            geometry_type='Point',
            gpkg_layer='crossing_points',
        ),
        make_layer(
            outputs_dir, out_dir,
            src_filename='tokyo_crossings.gpkg',
            layer_name='crossing_buffers_50m',
            geometry_type='Polygon',
            gpkg_layer='crossing_buffers_50m',
        ),
        make_layer(
            outputs_dir, out_dir,
            src_filename='tokyo_crossings.gpkg',
            layer_name='buffer_ward_intersection',
            geometry_type='Polygon',
            gpkg_layer='buffer_ward_intersection',
        ),
        make_layer(
            outputs_dir, out_dir,
            src_filename='tokyo_crossings.gpkg',
            layer_name='ward_crossing_density',
            geometry_type='Polygon',
            gpkg_layer='ward_crossing_density_wgs84',
            tooltip=['ward_id', 'crossing_count', 'crossings_per_km2'],
        ),
    ]
