"""
Unit tests for chronological walk-forward validator.
"""
from src.research.walk_forward_validator import WalkForwardValidator


def test_walk_forward_window_partitioning():
    # Synthetic chronological sequence of 200 signals
    signals = []
    for i in range(200):
        # Even are wins (+1.0R), odd are losses (-1.0R)
        r = 1.0 if i % 2 == 0 else -1.0
        # Gating suppresses odd signals
        sh_dir = "SELL" if i % 2 == 0 else "WAIT"
        signals.append({
            "timestamp": f"2026-01-01T{i//60:02d}:{i%60:02d}:00Z",
            "outcome": "WIN" if r > 0 else "LOSS",
            "realized_r": r,
            "base_dir": "SELL",
            "shadow_dir": sh_dir,
            "action": "KEEP" if sh_dir == "SELL" else "REJECT",
        })

    wf_report = WalkForwardValidator.execute_walk_forward(signals, num_folds=4)
    assert wf_report.num_windows == 4
    assert wf_report.positive_windows_count == 4
    assert wf_report.is_walk_forward_stable is True
    assert wf_report.median_shadow_expectancy_r == 1.0
