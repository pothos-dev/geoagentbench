"""Visualisation for fio-l1-paris-kml-pois.

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
            src_filename='paris_pois.geojson',
            layer_name='pois',
            geometry_type='Point',
            tooltip=['name', 'category'],
        ),
    ]
