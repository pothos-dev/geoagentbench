"""Visualisation for geo-l2-nyc-park-symdiff.

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
            src_filename='parks_disagreement.geojson',
            layer_name='disagreement',
            geometry_type='MultiPolygon',
            tooltip=['cluster_id', 'source'],
        ),
        make_layer(
            outputs_dir, out_dir,
            src_filename='park_label_anchors.geojson',
            layer_name='label_anchors',
            geometry_type='Point',
            tooltip=['cluster_id'],
        ),
    ]
