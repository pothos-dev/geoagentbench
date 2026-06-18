"""Visualisation for crs-l2-fiji-antimeridian.

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
            src_filename='fiji_transects_fmg.geojson',
            layer_name='transects',
            geometry_type='MultiLineString',
            tooltip=['transect_id'],
        ),
    ]
