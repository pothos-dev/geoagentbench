"""Unit tests for geo_grading.comparisons.

The brief is "free-edit" — task agents may refactor primitives. These
tests are the seatbelt that catches accidental signature / behaviour
regressions across runs.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from geo_grading.comparisons import (
    attribute_match,
    check_and_normalize_crs,
    count_within_tolerance,
    feature_set_equality_by_id,
    iou_with_tolerance,
    jaccard_similarity_set,
    read_geoparquet_lenient,
    topology_equal_within_epsilon,
)


def square(xmin: float, ymin: float, side: float) -> Polygon:
    return Polygon(
        [
            (xmin, ymin),
            (xmin + side, ymin),
            (xmin + side, ymin + side),
            (xmin, ymin + side),
        ]
    )


class TestIoU:
    def test_identical(self):
        a = square(0, 0, 10)
        assert iou_with_tolerance(a, a) == pytest.approx(1.0, abs=1e-3)

    def test_disjoint(self):
        a = square(0, 0, 10)
        b = square(100, 100, 10)
        assert iou_with_tolerance(a, b) == 0.0

    def test_half_overlap(self):
        a = square(0, 0, 10)
        b = square(5, 0, 10)
        # union = 150, intersection = 50, IoU = 1/3
        assert iou_with_tolerance(a, b) == pytest.approx(1 / 3, abs=1e-3)

    def test_both_empty(self):
        empty = Polygon()
        assert iou_with_tolerance(empty, empty) == 1.0

    def test_one_empty(self):
        empty = Polygon()
        a = square(0, 0, 10)
        assert iou_with_tolerance(a, empty) == 0.0

    def test_geodataframe_input(self):
        gdf_a = gpd.GeoDataFrame(geometry=[square(0, 0, 10)], crs="EPSG:4326")
        gdf_b = gpd.GeoDataFrame(geometry=[square(0, 0, 10)], crs="EPSG:4326")
        assert iou_with_tolerance(gdf_a, gdf_b) == pytest.approx(1.0, abs=1e-3)


class TestFeatureSetEqualityById:
    def test_identical(self):
        a = pd.DataFrame({"id": [1, 2, 3]})
        b = pd.DataFrame({"id": [1, 2, 3]})
        assert feature_set_equality_by_id(a, b, "id") == 1.0

    def test_disjoint(self):
        a = pd.DataFrame({"id": [1, 2, 3]})
        b = pd.DataFrame({"id": [4, 5, 6]})
        assert feature_set_equality_by_id(a, b, "id") == 0.0

    def test_half_overlap(self):
        a = pd.DataFrame({"id": [1, 2]})
        b = pd.DataFrame({"id": [2, 3]})
        # intersection = {2}, union = {1, 2, 3}, jaccard = 1/3
        assert feature_set_equality_by_id(a, b, "id") == pytest.approx(1 / 3)

    def test_handles_string_keys(self):
        a = pd.DataFrame({"id": ["a", "b"]})
        b = pd.DataFrame({"id": ["b", "c"]})
        assert feature_set_equality_by_id(a, b, "id") == pytest.approx(1 / 3)


class TestAttributeMatch:
    def test_all_match(self):
        a = pd.DataFrame({"id": [1, 2], "name": ["foo", "bar"], "n": [10, 20]})
        b = pd.DataFrame({"id": [1, 2], "name": ["foo", "bar"], "n": [10, 20]})
        result = attribute_match(a, b, ["name", "n"], key="id")
        assert result["name"] == 1.0
        assert result["n"] == 1.0
        assert result["_overall"] == 1.0

    def test_numeric_tolerance(self):
        a = pd.DataFrame({"id": [1, 2], "v": [100.0, 200.0]})
        b = pd.DataFrame({"id": [1, 2], "v": [101.0, 202.0]})
        result = attribute_match(a, b, ["v"], key="id", tolerance=0.05)
        assert result["v"] == 1.0
        result_strict = attribute_match(a, b, ["v"], key="id", tolerance=0.0)
        assert result_strict["v"] == 0.0

    def test_partial_overlap_keys(self):
        a = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        b = pd.DataFrame({"id": [2, 3, 4], "name": ["b", "X", "d"]})
        # Common keys: 2, 3. Match rate on name: 1/2.
        result = attribute_match(a, b, ["name"], key="id")
        assert result["name"] == pytest.approx(0.5)


class TestTopologyEqual:
    def test_identical(self):
        a = square(0, 0, 10)
        assert topology_equal_within_epsilon(a, a)

    def test_disjoint(self):
        a = square(0, 0, 10)
        b = square(100, 100, 10)
        assert not topology_equal_within_epsilon(a, b)

    def test_jitter_within_eps(self):
        a = square(0, 0, 10)
        b = Polygon(
            [(0, 0), (10.0001, 0), (10.0001, 10.0001), (0, 10.0001)]
        )
        assert topology_equal_within_epsilon(a, b, eps=0.01)

    def test_jitter_outside_eps(self):
        a = square(0, 0, 10)
        b = square(0, 0, 11)
        assert not topology_equal_within_epsilon(a, b, eps=0.01)


class TestCountWithinTolerance:
    def test_exact_match(self):
        assert count_within_tolerance(100, 100)

    def test_within_5pct(self):
        assert count_within_tolerance(100, 104, pct=0.05)
        assert count_within_tolerance(100, 96, pct=0.05)

    def test_outside_5pct(self):
        assert not count_within_tolerance(100, 110, pct=0.05)

    def test_dataframe_input(self):
        a = pd.DataFrame({"x": list(range(100))})
        b = pd.DataFrame({"x": list(range(102))})
        assert count_within_tolerance(a, b, pct=0.05)

    def test_both_zero(self):
        assert count_within_tolerance(0, 0)

    def test_one_zero(self):
        assert not count_within_tolerance(0, 1)


class TestCheckAndNormalizeCRS:
    def _gdf(self, epsg: int | None) -> gpd.GeoDataFrame:
        # Use a single point so reprojection is meaningful but cheap.
        return gpd.GeoDataFrame(
            geometry=[Point(2.35, 48.85)],
            crs=f"EPSG:{epsg}" if epsg is not None else None,
        )

    def test_already_in_target(self):
        gdf = self._gdf(2154)
        ok, reason, out, orig = check_and_normalize_crs(gdf, {2154, 32631}, 2154)
        assert ok and reason == ""
        assert orig == 2154
        # Same object returned when no reprojection needed.
        assert out is gdf

    def test_accepted_but_not_target_is_reprojected(self):
        gdf = self._gdf(32631)
        ok, reason, out, orig = check_and_normalize_crs(gdf, {2154, 32631}, 2154)
        assert ok and reason == ""
        assert orig == 32631
        assert out is not gdf
        assert out.crs.to_epsg() == 2154

    def test_rejected_crs_returns_original(self):
        gdf = self._gdf(3857)
        ok, reason, out, orig = check_and_normalize_crs(gdf, {2154, 32631}, 2154)
        assert not ok
        assert "3857" in reason
        assert orig == 3857
        assert out is gdf  # original handed back, not reprojected

    def test_missing_crs(self):
        gdf = self._gdf(None)
        ok, reason, out, orig = check_and_normalize_crs(gdf, {2154}, 2154)
        assert not ok
        assert "no CRS" in reason
        assert orig is None

    def test_none_input(self):
        ok, reason, out, orig = check_and_normalize_crs(None, {2154}, 2154)
        assert not ok
        assert out is None
        assert orig is None

    def test_target_not_in_accept_list_raises(self):
        gdf = self._gdf(2154)
        with pytest.raises(ValueError):
            check_and_normalize_crs(gdf, {32631}, 2154)


class TestJaccard:
    def test_identical(self):
        assert jaccard_similarity_set([1, 2, 3], [1, 2, 3]) == 1.0

    def test_disjoint(self):
        assert jaccard_similarity_set([1, 2], [3, 4]) == 0.0

    def test_partial(self):
        assert jaccard_similarity_set([1, 2, 3], [2, 3, 4]) == pytest.approx(0.5)

    def test_both_empty(self):
        assert jaccard_similarity_set([], []) == 1.0


class TestReadGeoparquetLenient:
    def test_compliant_roundtrip(self, tmp_path):
        gdf = gpd.GeoDataFrame(
            {"id": ["a", "b"]},
            geometry=[Point(0, 0), Point(1, 1)],
            crs="EPSG:4326",
        )
        p = tmp_path / "compliant.parquet"
        gdf.to_parquet(p)
        out, compliant = read_geoparquet_lenient(p)
        assert compliant is True
        assert out is not None and len(out) == 2
        assert out.crs.to_epsg() == 4326

    def _write_noncompliant(self, path, crs_obj):
        """Hand-roll a GeoParquet with an arbitrary `crs` metadata value,
        mimicking an agent that wrote the file with pyarrow directly."""
        import json

        import pyarrow as pa
        import pyarrow.parquet as pq
        from shapely import to_wkb
        from shapely.geometry import Point

        geoms = [Point(0, 0), Point(1, 1)]
        table = pa.table(
            {"id": ["a", "b"], "geometry": [to_wkb(g) for g in geoms]}
        )
        geo = {
            "version": "1.1.0",
            "primary_column": "geometry",
            "columns": {
                "geometry": {
                    "encoding": "WKB",
                    "geometry_types": ["Point"],
                    "crs": crs_obj,
                }
            },
        }
        table = table.replace_schema_metadata(
            {b"geo": json.dumps(geo).encode("utf-8")}
        )
        pq.write_table(table, path)

    def test_name_only_crs_recovered(self, tmp_path):
        # The underspecified PROJJSON PROJ 9 rejects ("Missing datum_ensemble").
        p = tmp_path / "nameonly.parquet"
        self._write_noncompliant(
            p, {"type": "GeographicCRS", "properties": {"name": "EPSG:4326"}}
        )
        # Standard reader chokes...
        with pytest.raises(Exception):
            gpd.read_parquet(p)
        # ...lenient reader recovers geometry + CRS, flagged non-compliant.
        out, compliant = read_geoparquet_lenient(p)
        assert compliant is False
        assert out is not None and len(out) == 2
        assert out.crs is not None and out.crs.to_epsg() == 4326

    def test_unreadable_file(self, tmp_path):
        p = tmp_path / "garbage.parquet"
        p.write_bytes(b"not a parquet file")
        out, compliant = read_geoparquet_lenient(p)
        assert out is None
