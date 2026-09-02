"""
Unit tests for ThresholdSpecification & ThresholdEvaluator.
"""
import pytest
from src.research.threshold_specification import (
    ThresholdEvaluator,
    DEFINED_THRESHOLDS,
    RESEARCH_POLICY_VERSION,
    THRESHOLD_SPEC_VERSION,
)


class TestThresholdSpecification:
    def test_versioning_constants_present(self):
        assert RESEARCH_POLICY_VERSION == "1.0"
        assert THRESHOLD_SPEC_VERSION == "1.0"

    def test_all_catalog_thresholds_have_metadata(self):
        assert len(DEFINED_THRESHOLDS) >= 15
        for name, defn in DEFINED_THRESHOLDS.items():
            assert defn.threshold_name == name
            assert defn.calculation_method != ""
            assert defn.denominator != ""
            assert defn.boundary_operator in (">=", "<=", ">", "<", "==")
            assert defn.minimum_sample > 0

    def test_expectancy_threshold_evaluation_pass(self):
        res = ThresholdEvaluator.evaluate("EXPECTANCY_MINIMUM", observed_value=0.18, sample_size=600)
        assert res.passed is True
        assert res.status == "PASS"

    def test_expectancy_threshold_evaluation_fail(self):
        res = ThresholdEvaluator.evaluate("EXPECTANCY_MINIMUM", observed_value=0.12, sample_size=600)
        assert res.passed is False
        assert res.status == "FAIL"

    def test_insufficient_sample_fails_evaluation(self):
        res = ThresholdEvaluator.evaluate("EXPECTANCY_MINIMUM", observed_value=0.25, sample_size=100)
        assert res.passed is False
        assert res.status == "INSUFFICIENT_DATA"

    def test_unrounded_boundary_operator_precision(self):
        # 0.1499999 should FAIL >= 0.15
        res_fail = ThresholdEvaluator.evaluate("EXPECTANCY_MINIMUM", observed_value=0.149999, sample_size=600)
        assert res_fail.passed is False

        # 0.1500000 should PASS >= 0.15
        res_pass = ThresholdEvaluator.evaluate("EXPECTANCY_MINIMUM", observed_value=0.150000, sample_size=600)
        assert res_pass.passed is True

    def test_generate_threshold_register_report(self):
        json_path, md_path = ThresholdEvaluator.generate_threshold_register_report()
        assert json_path.endswith("THRESHOLD_REGISTER.json")
        assert md_path.endswith("THRESHOLD_REGISTER.md")
