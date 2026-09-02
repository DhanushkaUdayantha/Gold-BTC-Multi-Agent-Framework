"""
Unit tests for ProjectAuditor.
"""
import pytest
from src.research.project_auditor import ProjectAuditor, CurrentProjectAuditReport


class TestProjectAuditor:
    def test_run_audit_passes(self):
        report = ProjectAuditor.run_audit()
        assert isinstance(report, CurrentProjectAuditReport)
        assert report.audit_status == "PASS"
        assert len(report.components) > 0
        assert len(report.production_critical_paths) > 0
        assert len(report.flows) == 3

    def test_generate_audit_reports(self):
        json_path, md_path = ProjectAuditor.generate_audit_reports()
        assert json_path.endswith("CURRENT_PROJECT_AUDIT.json")
        assert md_path.endswith("CURRENT_PROJECT_AUDIT.md")
