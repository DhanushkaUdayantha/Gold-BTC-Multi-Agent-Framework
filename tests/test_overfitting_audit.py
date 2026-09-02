"""
Tests for overfitting_audit.py — Phase 3.
"""
import pytest
from src.research.overfitting_audit import (
    OverfittingAuditor,
    FAMILY_ALPHA,
)


class TestOverfittingAuditor:
    def test_empty_auditor_low_risk(self):
        auditor = OverfittingAuditor()
        report = auditor.compute_report()
        assert report.total_experiments == 0
        assert report.total_comparisons == 1  # max(0, 1) safeguard
        assert report.multiple_testing_risk == "LOW"

    def test_single_experiment_bonferroni(self):
        auditor = OverfittingAuditor()
        auditor.register("EXP_1", "FILTER_ABLATION", "Test filter 1", n_comparisons=1, p_value=0.03)
        report = auditor.compute_report()
        assert report.total_experiments == 1
        assert report.total_comparisons == 1
        assert report.bonferroni_threshold == pytest.approx(FAMILY_ALPHA, abs=1e-5)
        assert report.significant_at_bonferroni == 1
        assert report.significant_at_nominal == 1

    def test_multiple_comparisons_adjusts_threshold(self):
        auditor = OverfittingAuditor()
        # 10 comparisons
        for i in range(10):
            auditor.register(f"EXP_{i}", "FILTER_ABLATION", f"Test filter {i}", n_comparisons=1, p_value=0.02)
        report = auditor.compute_report()
        assert report.total_comparisons == 10
        assert report.bonferroni_threshold == pytest.approx(0.05 / 10, abs=1e-5)
        # p=0.02 < 0.05 (nominal pass), but p=0.02 > 0.005 (bonferroni fail)
        assert report.significant_at_nominal == 10
        assert report.significant_at_bonferroni == 0

    def test_risk_levels(self):
        auditor = OverfittingAuditor()
        for i in range(25):
            auditor.register(f"EXP_{i}", "FILTER_ABLATION", f"Test {i}", n_comparisons=1)
        assert auditor.compute_report().multiple_testing_risk == "MODERATE"

        for i in range(30):
            auditor.register(f"EXP_H_{i}", "FILTER_ABLATION", f"Test H {i}", n_comparisons=1)
        # 55 total comparisons -> HIGH
        assert auditor.compute_report().multiple_testing_risk == "HIGH"

        for i in range(50):
            auditor.register(f"EXP_C_{i}", "FILTER_ABLATION", f"Test C {i}", n_comparisons=1)
        # 105 total comparisons -> CRITICAL
        assert auditor.compute_report().multiple_testing_risk == "CRITICAL"

    def test_findings_and_recommendations_generated(self):
        auditor = OverfittingAuditor()
        for i in range(30):
            auditor.register(f"EXP_{i}", "FILTER_ABLATION", f"Filter {i}", n_comparisons=1, p_value=0.04)
        report = auditor.compute_report()
        assert len(report.findings) > 0
        assert len(report.recommendations) > 0
