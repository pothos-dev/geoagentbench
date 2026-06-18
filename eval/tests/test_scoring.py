"""Unit tests for geo_grading.scoring."""

from __future__ import annotations

from geo_grading.scoring import Gate, ScoreReport, Subcheck


class TestScoreReport:
    def test_all_pass(self):
        report = ScoreReport(
            task_id="t",
            gates=[Gate("format_schema_valid", True)],
            subchecks=[Subcheck("a", True), Subcheck("b", True)],
        )
        assert report.gates_passed
        assert report.score == 1.0
        assert report.passed_count == 2
        assert report.total_count == 2

    def test_gate_fail_zeros_score(self):
        report = ScoreReport(
            task_id="t",
            gates=[Gate("format_schema_valid", False, "missing CRS")],
            subchecks=[Subcheck("a", True), Subcheck("b", True)],
        )
        assert not report.gates_passed
        assert report.score == 0.0

    def test_partial_subchecks(self):
        report = ScoreReport(
            task_id="t",
            gates=[Gate("format_schema_valid", True)],
            subchecks=[
                Subcheck("a", True),
                Subcheck("b", False),
                Subcheck("c", True),
                Subcheck("d", False),
            ],
        )
        assert report.score == 0.5
        assert report.passed_count == 2
        assert report.total_count == 4

    def test_no_subchecks(self):
        report = ScoreReport(
            task_id="t",
            gates=[Gate("format_schema_valid", True)],
        )
        assert report.score == 1.0

    def test_to_dict_round_trip(self):
        report = ScoreReport(
            task_id="t",
            gates=[Gate("format_schema_valid", True)],
            subchecks=[Subcheck("a", True, detail="ok")],
        )
        d = report.to_dict()
        assert d["task_id"] == "t"
        assert d["score"] == 1.0
        assert d["gates"][0]["name"] == "format_schema_valid"
        assert d["subchecks"][0]["detail"] == "ok"
