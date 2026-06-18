"""Shared grading primitives for the geospatial agent benchmark.

Per-task graders (`tasks/<slug>/grade.py`) import from this module to
compare an agent's output artifacts against a committed reference.

The library is intentionally minimal: five comparison primitives + a
structured `ScoreReport` dataclass. Task agents may extend this module
when they need a new primitive; extensions must ship with a unit test in
`tests/test_geo_grading.py` so regressions surface on the next run.
"""

from geo_grading.comparisons import (
    CrsGradeResult,
    attribute_match,
    check_and_normalize_crs,
    count_within_tolerance,
    feature_set_equality_by_id,
    grade_crs_soft,
    iou_with_tolerance,
    is_wgs84,
    is_wgs84_fc,
    jaccard_similarity_set,
    read_geoparquet_lenient,
    topology_equal_within_epsilon,
)
from geo_grading.scoring import (
    Gate,
    ScoreReport,
    Subcheck,
)

__all__ = [
    "CrsGradeResult",
    "attribute_match",
    "check_and_normalize_crs",
    "count_within_tolerance",
    "feature_set_equality_by_id",
    "grade_crs_soft",
    "iou_with_tolerance",
    "is_wgs84",
    "is_wgs84_fc",
    "jaccard_similarity_set",
    "read_geoparquet_lenient",
    "topology_equal_within_epsilon",
    "Gate",
    "ScoreReport",
    "Subcheck",
]
