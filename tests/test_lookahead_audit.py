"""
Tests for lookahead_audit.py — Phase 3.
"""
import pytest
from src.research.lookahead_audit import (
    LookaheadAuditor,
    LookaheadAuditReport,
    LookaheadViolation,
)
from src.research.signal_research_record import SignalResearchRecord, OutcomeLabel


def _make_clean_record(
    signal_id: str = "SIG001",
    signal_ts: str = "2024-01-10T10:00:00Z",
    outcome_ts: str = "2024-01-10T14:00:00Z",
    asset: str = "XAU/USD",
    lookahead_violation: bool = False,
) -> SignalResearchRecord:
    return SignalResearchRecord(
        signal_id=signal_id,
        asset=asset,
        signal_timestamp=signal_ts,
        outcome_timestamp=outcome_ts,
        lookahead_violation=lookahead_violation,
        outcome=OutcomeLabel.WIN,
        realized_r=1.0,
    )


class TestLookaheadAuditor:
    def test_clean_dataset_passes(self):
        records = [
            _make_clean_record("A", "2024-01-01T10:00:00Z", "2024-01-01T14:00:00Z"),
            _make_clean_record("B", "2024-01-02T10:00:00Z", "2024-01-02T14:00:00Z"),
            _make_clean_record("C", "2024-01-03T10:00:00Z", "2024-01-03T14:00:00Z"),
        ]
        report = LookaheadAuditor.audit(records)
        assert report.audit_passed is True
        assert report.status == "PASSED"
        assert report.total_violations == 0

    def test_outcome_before_signal_detected(self):
        # outcome_timestamp <= signal_timestamp → OUTCOME_LEAKAGE
        records = [
            _make_clean_record("BAD", "2024-01-10T10:00:00Z", "2024-01-10T09:00:00Z"),
        ]
        report = LookaheadAuditor.audit(records, raise_on_violation=False)
        assert report.audit_passed is False
        assert "OUTCOME_LEAKAGE" in report.violation_types

    def test_raises_on_hard_violation(self):
        records = [
            _make_clean_record("BAD", "2024-01-10T10:00:00Z", "2024-01-10T09:00:00Z"),
        ]
        with pytest.raises(LookaheadViolation):
            LookaheadAuditor.audit(records, raise_on_violation=True)

    def test_flagged_record_detected(self):
        records = [
            _make_clean_record("FLAG", lookahead_violation=True),
        ]
        report = LookaheadAuditor.audit(records, raise_on_violation=False)
        assert "FUTURE_TIMESTAMP" in report.violation_types

    def test_chronological_ordering_violation(self):
        # Out-of-order timestamps
        records = [
            _make_clean_record("B", "2024-01-10T10:00:00Z", "2024-01-10T14:00:00Z"),
            _make_clean_record("A", "2024-01-01T10:00:00Z", "2024-01-01T14:00:00Z"),
        ]
        report = LookaheadAuditor.audit(records, raise_on_violation=False)
        assert report.chronological_ordering_valid is False
        assert "CHRONOLOGICAL_ORDER" in report.violation_types

    def test_calibration_period_overlap_detected(self):
        records = [_make_clean_record("A")]
        report = LookaheadAuditor.audit(
            records,
            calibration_train_end="2024-06-01T00:00:00Z",
            evaluation_start="2024-05-01T00:00:00Z",  # Before train_end
            raise_on_violation=False,
        )
        assert report.calibration_period_valid is False
        assert "CALIBRATION_LEAKAGE" in report.violation_types

    def test_calibration_period_valid(self):
        records = [_make_clean_record("A")]
        report = LookaheadAuditor.audit(
            records,
            calibration_train_end="2024-04-01T00:00:00Z",
            evaluation_start="2024-06-01T00:00:00Z",  # After train_end
            raise_on_violation=False,
        )
        assert report.calibration_period_valid is True

    def test_duplicate_timestamp_detected(self):
        records = [
            _make_clean_record("A", "2024-01-10T10:00:00Z", "2024-01-10T14:00:00Z", "XAU/USD"),
            _make_clean_record("B", "2024-01-10T10:00:00Z", "2024-01-10T14:00:00Z", "XAU/USD"),
        ]
        report = LookaheadAuditor.audit(records, raise_on_violation=False)
        assert "DUPLICATE_TIMESTAMP" in report.violation_types

    def test_total_records_counted(self):
        records = [_make_clean_record(str(i), f"2024-01-{i+1:02d}T10:00:00Z")
                   for i in range(10)]
        report = LookaheadAuditor.audit(records)
        assert report.total_records_audited == 10

    def test_empty_dataset_passes(self):
        report = LookaheadAuditor.audit([])
        assert report.audit_passed is True
        assert report.total_records_audited == 0

    def test_lookahead_violation_exception_has_violations(self):
        records = [
            _make_clean_record("BAD", "2024-01-10T10:00:00Z", "2024-01-10T08:00:00Z"),
        ]
        try:
            LookaheadAuditor.audit(records, raise_on_violation=True)
        except LookaheadViolation as exc:
            assert len(exc.violations) > 0
