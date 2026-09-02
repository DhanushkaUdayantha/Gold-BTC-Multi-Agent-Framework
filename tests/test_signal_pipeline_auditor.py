"""
Unit tests for SignalPipelineAuditor — Phase 4.
"""
import pytest
from src.research.signal_pipeline_auditor import (
    SignalPipelineAuditor,
    SignalPipelineAuditReport,
)


class TestSignalPipelineAuditor:
    def test_audit_pipeline_returns_report(self):
        report = SignalPipelineAuditor.audit_pipeline()
        assert isinstance(report, SignalPipelineAuditReport)
        assert report.total_stages == 14
        assert len(report.stages) == 14
        assert report.audit_verdict == "HEALTHY"

    def test_all_14_stages_have_details(self):
        report = SignalPipelineAuditor.audit_pipeline()
        for stage in report.stages:
            assert stage.stage_number in range(1, 15)
            assert stage.stage_name != ""
            assert stage.current_file != ""
            assert stage.status in ("NO_CHANGE_REQUIRED", "HEALTHY", "PARTIAL")

    def test_generate_audit_reports(self):
        json_path, md_path = SignalPipelineAuditor.generate_audit_reports()
        assert json_path.endswith("SIGNAL_PIPELINE_AUDIT.json")
        assert md_path.endswith("SIGNAL_PIPELINE_AUDIT.md")
