"""
Unit tests for PhaseExitValidator.
"""
import pytest
from src.research.phase_exit_validator import (
    PhaseExitValidator,
    MasterPhaseExitReport,
    ExitState,
)


class TestPhaseExitValidator:
    def test_evaluate_all_phases(self):
        report = PhaseExitValidator.evaluate_all_phases({
            "lookahead_status": "PASSED",
            "calibration_ece": 0.0157,
            "governance_decision": "REJECT",
        })
        assert isinstance(report, MasterPhaseExitReport)
        assert report.total_phases_evaluated >= 10
        assert report.phases_passed >= 8
        assert report.production_decision_status == "UNCHANGED"
        assert report.production_gating_status == "DISABLED"
        assert "Production decision behavior unchanged" in report.safety_statement_1
        assert "Research results do not authorize production activation" in report.safety_statement_2

    def test_generate_exit_reports(self):
        json_path, md_path = PhaseExitValidator.generate_exit_reports({
            "lookahead_status": "PASSED",
            "governance_decision": "REJECT",
        })
        assert json_path.endswith("PHASE_EXIT_REPORT.json")
        assert md_path.endswith("PHASE_EXIT_REPORT.md")

    def test_format_terminal_summary_contains_safety_statements(self):
        phase_report = PhaseExitValidator.evaluate_all_phases()
        summary_str = PhaseExitValidator.format_terminal_summary({}, phase_report)
        assert "RESEARCH PLATFORM VALIDATION COMPLETE" in summary_str
        assert "PRODUCTION DECISION:\nUNCHANGED" in summary_str or "PRODUCTION DECISION: UNCHANGED" in summary_str
        assert "PRODUCTION GATING:   DISABLED" in summary_str or "PRODUCTION GATING:" in summary_str
        assert "Production decision behavior unchanged." in summary_str
        assert "Research results do not authorize production activation." in summary_str
