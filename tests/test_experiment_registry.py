"""
Tests for experiment_registry.py — Phase 3.
"""
import os
import shutil
import pytest
from src.research.experiment_registry import (
    ExperimentRegistry,
    ExperimentRecord,
)


@pytest.fixture
def temp_registry(tmp_path):
    reg_dir = tmp_path / "experiment_registry"
    return ExperimentRegistry(registry_dir=str(reg_dir))


class TestExperimentRegistry:
    def test_register_creates_pending_record(self, temp_registry):
        rec = temp_registry.register(
            experiment_type="FILTER_ABLATION",
            description="Test ablation experiment",
            n_trades=100,
            assets=["BTC/USD", "XAU/USD"],
        )
        assert rec.status == "PENDING"
        assert rec.n_trades == 100
        assert len(rec.experiment_id) == 16
        assert len(temp_registry.list_all()) == 1

    def test_complete_updates_record_status_and_outputs(self, temp_registry):
        rec = temp_registry.register(
            experiment_type="FILTER_ABLATION",
            description="Complete test",
        )
        comp_rec = temp_registry.complete(
            rec.experiment_id,
            output_summary={"expectancy_delta": 0.08},
            output_paths=["data/reports/test.md"],
        )
        assert comp_rec is not None
        assert comp_rec.status == "COMPLETED"
        assert comp_rec.output_summary["expectancy_delta"] == 0.08
        assert comp_rec.output_paths == ["data/reports/test.md"]

    def test_fail_updates_error_message(self, temp_registry):
        rec = temp_registry.register(
            experiment_type="FILTER_ABLATION",
            description="Fail test",
        )
        failed_rec = temp_registry.fail(rec.experiment_id, "Division by zero")
        assert failed_rec is not None
        assert failed_rec.status == "FAILED"
        assert failed_rec.error_message == "Division by zero"

    def test_is_duplicate_detection(self, temp_registry):
        fp = "abc123fingerprint"
        rec = temp_registry.register(
            experiment_type="FILTER_ABLATION",
            description="Dup check",
            input_fingerprint=fp,
        )
        assert not temp_registry.is_duplicate("FILTER_ABLATION", fp)
        temp_registry.complete(rec.experiment_id)
        assert temp_registry.is_duplicate("FILTER_ABLATION", fp)
        assert not temp_registry.is_duplicate("DIFFERENT_TYPE", fp)

    def test_persistence_reloads_from_disk(self, tmp_path):
        reg_dir = tmp_path / "experiment_registry"
        reg1 = ExperimentRegistry(registry_dir=str(reg_dir))
        rec = reg1.register(
            experiment_type="PERSIST_TEST",
            description="Persistence check",
            n_trades=42,
        )
        reg1.complete(rec.experiment_id)

        # Create new instance on same dir
        reg2 = ExperimentRegistry(registry_dir=str(reg_dir))
        all_recs = reg2.list_all()
        assert len(all_recs) == 1
        assert all_recs[0].experiment_id == rec.experiment_id
        assert all_recs[0].status == "COMPLETED"
        assert all_recs[0].n_trades == 42

    def test_summary_md_generation(self, temp_registry):
        rec = temp_registry.register("TEST_TYPE", "Summary test")
        md = temp_registry.get_summary_md()
        assert "# Experiment Registry Summary" in md
        assert rec.experiment_id[:12] in md
