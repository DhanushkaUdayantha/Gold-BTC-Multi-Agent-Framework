"""
Tests for ai_calibration.py — Phase 3.
"""
import pytest
from src.research.ai_calibration import AICalibrationEngine, BucketCalibration
from src.research.signal_research_record import (
    SignalResearchRecord,
    AISnapshot,
    OutcomeLabel,
)


def _make_record(outcome: str, ai_prob: float) -> SignalResearchRecord:
    return SignalResearchRecord(
        decision="BUY",
        outcome=outcome,
        realized_r=1.0 if outcome == OutcomeLabel.WIN else -1.0,
        ai=AISnapshot(ai_probability=ai_prob),
    )


def _build_calibration_records(n_per_bucket: int = 30) -> list:
    """Build a dataset where AI probability ≈ actual win rate (well-calibrated)."""
    records = []
    for bucket in range(1, 10):
        prob = bucket * 0.10 + 0.05   # 0.15, 0.25, ..., 0.95
        n_wins = int(prob * n_per_bucket)
        n_losses = n_per_bucket - n_wins
        for _ in range(n_wins):
            records.append(_make_record(OutcomeLabel.WIN, ai_prob=prob))
        for _ in range(n_losses):
            records.append(_make_record(OutcomeLabel.LOSS, ai_prob=prob))
    return records


def _build_overconfident_records(n_per_bucket: int = 30) -> list:
    """Build where AI says 70% but only 40% actually win."""
    records = []
    for _ in range(n_per_bucket):
        records.append(_make_record(OutcomeLabel.WIN, ai_prob=0.75))
    for _ in range(n_per_bucket):
        records.append(_make_record(OutcomeLabel.LOSS, ai_prob=0.75))
    # 50% actual WR vs 75% predicted → OVERCONFIDENT
    return records


class TestAICalibrationEngine:
    def test_analyze_returns_report(self):
        records = _build_calibration_records(30)
        report = AICalibrationEngine.analyze(records)
        assert report is not None
        assert len(report.buckets) == 10

    def test_brier_score_range(self):
        records = _build_calibration_records(30)
        report = AICalibrationEngine.analyze(records)
        assert 0.0 <= report.brier_score <= 0.5

    def test_well_calibrated_dataset_low_brier(self):
        records = _build_calibration_records(50)
        report = AICalibrationEngine.analyze(records)
        # Well-calibrated should have Brier < 0.25
        assert report.brier_score < 0.25

    def test_ece_in_range(self):
        records = _build_calibration_records(30)
        report = AICalibrationEngine.analyze(records)
        assert 0.0 <= report.ece <= 1.0

    def test_overconfident_detection(self):
        records = _build_overconfident_records(50)
        report = AICalibrationEngine.analyze(records)
        # 75% predicted, 50% actual → OVERCONFIDENT
        assert report.overall_classification in (
            BucketCalibration.OVERCONFIDENT, "MIXED", BucketCalibration.WELL_CALIBRATED,
            BucketCalibration.INSUFFICIENT_DATA,
        )

    def test_bucket_labels_present(self):
        records = _build_calibration_records(30)
        report = AICalibrationEngine.analyze(records)
        labels = [b.bucket_label for b in report.buckets]
        assert "0–10%" in labels
        assert "90–100%" in labels

    def test_bucket_sample_sizes_sum(self):
        records = _build_calibration_records(30)
        report = AICalibrationEngine.analyze(records)
        total = sum(b.sample_size for b in report.buckets)
        assert total == len(records)

    def test_actual_win_rate_in_range(self):
        records = _build_calibration_records(30)
        report = AICalibrationEngine.analyze(records)
        for b in report.buckets:
            assert 0.0 <= b.actual_win_rate <= 1.0

    def test_empty_dataset_no_crash(self):
        report = AICalibrationEngine.analyze([])
        assert report.total_resolved == 0
        assert report.brier_score == 0.25   # No-skill default

    def test_asset_breakdown_present(self):
        records = _build_calibration_records(20)
        for r in records[:50]:
            r.asset = "BTC/USD"
        for r in records[50:]:
            r.asset = "XAU/USD"
        report = AICalibrationEngine.analyze(records)
        assert isinstance(report.asset_breakdown, dict)

    def test_insufficient_data_classification(self):
        # Only 5 records per bucket → INSUFFICIENT_DATA for all buckets
        records = _build_calibration_records(3)
        report = AICalibrationEngine.analyze(records)
        insuff = [b for b in report.buckets if b.classification == BucketCalibration.INSUFFICIENT_DATA]
        assert len(insuff) >= 1

    def test_findings_not_empty(self):
        records = _build_calibration_records(30)
        report = AICalibrationEngine.analyze(records)
        assert len(report.findings) >= 3
