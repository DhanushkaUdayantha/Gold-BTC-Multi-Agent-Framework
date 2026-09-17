"""
Unit tests for HistoricalEvidenceService canonical run scoping and empirical evidence.

Validates:
1. Canonical run isolation excludes duplicate signals from earlier backtest runs.
2. BTC and XAU strict asset isolation (no cross-asset leakage).
3. Sample size N < 10 suppression guard (win rate, expectancy, and calibrated prob set to None).
4. Sample size N >= 10 calculation (computes valid win rate, expectancy, and quality tier).
5. Correct handling of WIN, LOSS, BREAKEVEN, and EXPIRED outcomes.
6. Test A: Current BTC pin (RUN-BTC-USD-20260831-173607) resolves exact run.
7. Test B: Current XAU pin (RUN-XAU-USD-20260831-174452) resolves exact run.
8. Test C: Future exploratory run cannot replace canonical baseline.
9. Test D: Wrong-symbol pin fails closed (no fallback).
10. Test E: Missing run fails closed (no fallback).
11. Test F: Incomplete run (RUNNING/FAILED) fails closed.
12. Test G: Missing report in backtest_reports fails closed.
"""
import sqlite3
import pytest
from typing import Dict, Any

from config.settings import get_settings
from src.services.historical_evidence_service import HistoricalEvidenceService


def _init_test_db(db_path: str):
    """Initialize schema for backtest_runs, backtest_reports, and historical_signals."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_runs (
                run_id TEXT PRIMARY KEY,
                dataset_id TEXT,
                dataset_version TEXT,
                engine_version TEXT,
                symbol TEXT,
                config_json TEXT,
                status TEXT,
                progress_pct REAL,
                current_step TEXT,
                error TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                execution_time_seconds REAL,
                total_signals_evaluated INTEGER,
                total_trades_generated INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_reports (
                run_id TEXT PRIMARY KEY,
                report_json TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historical_signals (
                signal_id TEXT PRIMARY KEY,
                run_id TEXT,
                dataset_id TEXT,
                symbol TEXT,
                source_symbol TEXT,
                signal_timestamp TEXT,
                snapshot_id TEXT,
                entry_price REAL,
                direction TEXT,
                confluence_score INTEGER,
                technical_score INTEGER,
                gemini_score INTEGER,
                contributor_scores_json TEXT,
                contributor_directions_json TEXT,
                data_quality TEXT,
                gate_direction TEXT,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                market_regime TEXT,
                session TEXT,
                outcome TEXT,
                realized_r REAL,
                mfe REAL,
                mae REAL,
                time_to_outcome_minutes INTEGER,
                is_in_sample INTEGER,
                success_reason TEXT,
                failure_reason TEXT
            )
        """)


def test_canonical_run_isolation_excludes_duplicate_runs(tmp_path):
    """Signals from earlier backtest runs must NOT inflate empirical sample size."""
    db_file = str(tmp_path / 'historical_test.db')
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        # Run A: Old test run with 10 signals
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at)
            VALUES ('RUN-BTC-OLD-1', 'BTC/USD', 'COMPLETED', '2026-08-30T10:00:00Z')
        """)
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES ('RUN-BTC-OLD-1', '{}', '2026-08-30T10:05:00Z')
        """)
        for i in range(10):
            conn.execute("""
                INSERT INTO historical_signals (
                    signal_id, run_id, symbol, signal_timestamp, direction,
                    confluence_score, technical_score, gemini_score,
                    market_regime, outcome, realized_r
                ) VALUES (?, 'RUN-BTC-OLD-1', 'BTC/USD', ?, 'BUY', 65, 55, 10, 'Trending', 'WIN', 1.5)
            """, (f'SIG-OLD-{i}', f'2024-01-{i+1:02d}T10:00:00Z'))

        # Run B: Intermediate test run with same 10 signals
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at)
            VALUES ('RUN-BTC-OLD-2', 'BTC/USD', 'COMPLETED', '2026-08-30T12:00:00Z')
        """)
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES ('RUN-BTC-OLD-2', '{}', '2026-08-30T12:05:00Z')
        """)
        for i in range(10):
            conn.execute("""
                INSERT INTO historical_signals (
                    signal_id, run_id, symbol, signal_timestamp, direction,
                    confluence_score, technical_score, gemini_score,
                    market_regime, outcome, realized_r
                ) VALUES (?, 'RUN-BTC-OLD-2', 'BTC/USD', ?, 'BUY', 65, 55, 10, 'Trending', 'WIN', 1.5)
            """, (f'SIG-OLD2-{i}', f'2024-01-{i+1:02d}T10:00:00Z'))

        # Run C: Canonical full run with 25 distinct signals (15 WIN, 10 LOSS)
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at)
            VALUES ('RUN-BTC-CANONICAL', 'BTC/USD', 'COMPLETED', '2026-08-31T18:00:00Z')
        """)
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES ('RUN-BTC-CANONICAL', '{"full": true}', '2026-08-31T18:10:00Z')
        """)
        for i in range(25):
            outcome = 'WIN' if i < 15 else 'LOSS'
            realized_r = 1.6 if outcome == 'WIN' else -1.0
            conn.execute("""
                INSERT INTO historical_signals (
                    signal_id, run_id, symbol, signal_timestamp, direction,
                    confluence_score, technical_score, gemini_score,
                    market_regime, outcome, realized_r
                ) VALUES (?, 'RUN-BTC-CANONICAL', 'BTC/USD', ?, 'BUY', 65, 55, 10, 'Trending', ?, ?)
            """, (f'SIG-CANON-{i}', f'2024-02-{i+1:02d}T10:00:00Z', outcome, realized_r))

    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-BTC-CANONICAL',
    )
    fp = {
        'symbol': 'BTC/USD',
        'direction': 'BUY',
        'confluence_score': 65,
        'score_band': '60-69',
        'market_regime': 'Trending',
        'contributors': {},
    }
    pkg = service._query_empirical_evidence(fp)

    # Sample size must be exactly 25 (the canonical run), NOT 10 + 10 + 25 = 45!
    assert pkg.sample_size == 25
    assert pkg.win_rate == 60.0
    assert pkg.status in ('AVAILABLE', 'STALE')
    assert pkg.evidence_quality == 'EXPLORATORY'


def test_cross_asset_isolation(tmp_path):
    """BTC signals must never leak into XAU analysis and vice versa."""
    db_file = str(tmp_path / 'asset_isolation_test.db')
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("INSERT INTO backtest_runs (run_id, symbol, status, created_at) VALUES ('RUN-BTC', 'BTC/USD', 'COMPLETED', '2026-08-31T12:00:00Z')")
        conn.execute("INSERT INTO backtest_reports (run_id, report_json, created_at) VALUES ('RUN-BTC', '{}', '2026-08-31T12:05:00Z')")
        for i in range(30):
            conn.execute("""
                INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r)
                VALUES (?, 'RUN-BTC', 'BTC/USD', ?, 'BUY', 65, 'Trending', 'WIN', 1.5)
            """, (f'BTC-SIG-{i}', f'2024-01-{i+1:02d}T00:00:00Z'))

        conn.execute("INSERT INTO backtest_runs (run_id, symbol, status, created_at) VALUES ('RUN-XAU', 'XAU/USD', 'COMPLETED', '2026-08-31T12:00:00Z')")
        conn.execute("INSERT INTO backtest_reports (run_id, report_json, created_at) VALUES ('RUN-XAU', '{}', '2026-08-31T12:05:00Z')")
        for i in range(20):
            conn.execute("""
                INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r)
                VALUES (?, 'RUN-XAU', 'XAU/USD', ?, 'SELL', 65, 'Trending', 'LOSS', -1.0)
            """, (f'XAU-SIG-{i}', f'2024-02-{i+1:02d}T00:00:00Z'))

    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-BTC',
        canonical_run_xau='RUN-XAU',
    )

    btc_pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })
    assert btc_pkg.sample_size == 30
    assert btc_pkg.win_rate == 100.0

    xau_pkg = service._query_empirical_evidence({
        'symbol': 'XAU/USD', 'direction': 'SELL', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })
    assert xau_pkg.sample_size == 20
    assert xau_pkg.win_rate == 0.0


def test_n_under_10_suppression_rule(tmp_path):
    """Small sample size (N < 10) must suppress win rate, calibrated probability, and expectancy."""
    db_file = str(tmp_path / 'small_sample_test.db')
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("INSERT INTO backtest_runs (run_id, symbol, status, created_at) VALUES ('RUN-1', 'BTC/USD', 'COMPLETED', '2026-08-31T12:00:00Z')")
        conn.execute("INSERT INTO backtest_reports (run_id, report_json, created_at) VALUES ('RUN-1', '{}', '2026-08-31T12:05:00Z')")
        for i in range(7):
            conn.execute("""
                INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r)
                VALUES (?, 'RUN-1', 'BTC/USD', ?, 'BUY', 65, 'Trending', 'WIN', 1.5)
            """, (f'SIG-{i}', f'2024-01-{i+1:02d}T00:00:00Z'))

    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-1',
    )
    pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })

    assert pkg.sample_size == 7
    assert pkg.win_rate is None
    assert pkg.calibrated_probability is None
    assert pkg.expectancy is None
    assert pkg.evidence_quality == 'INSUFFICIENT'


def test_outcome_handling_with_expired(tmp_path):
    """WIN, LOSS, and EXPIRED outcomes must be handled accurately without crash."""
    db_file = str(tmp_path / 'outcomes_test.db')
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("INSERT INTO backtest_runs (run_id, symbol, status, created_at) VALUES ('RUN-1', 'BTC/USD', 'COMPLETED', '2026-08-31T12:00:00Z')")
        conn.execute("INSERT INTO backtest_reports (run_id, report_json, created_at) VALUES ('RUN-1', '{}', '2026-08-31T12:05:00Z')")
        for i in range(10):
            conn.execute("INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r) VALUES (?, 'RUN-1', 'BTC/USD', ?, 'BUY', 65, 'Trending', 'WIN', 1.6)", (f'W-{i}', f'2024-01-{i+1:02d}T00:00:00Z'))
        for i in range(5):
            conn.execute("INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r) VALUES (?, 'RUN-1', 'BTC/USD', ?, 'BUY', 65, 'Trending', 'LOSS', -1.0)", (f'L-{i}', f'2024-02-{i+1:02d}T00:00:00Z'))
        for i in range(2):
            conn.execute("INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r) VALUES (?, 'RUN-1', 'BTC/USD', ?, 'BUY', 65, 'Trending', 'EXPIRED', 0.0)", (f'E-{i}', f'2024-03-{i+1:02d}T00:00:00Z'))

    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-1',
    )
    pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })

    assert pkg.sample_size == 17
    assert pkg.win_rate == 66.7
    assert pkg.expectancy is not None


# ---------------------------------------------------------------------------
# Mandatory Canonical Run Pinning Tests (Tests A through G)
# ---------------------------------------------------------------------------

def test_canonical_pin_a_btc_current():
    """Test A: Current BTC pin resolves RUN-BTC-USD-20260831-173607 on production DB."""
    service = HistoricalEvidenceService()
    expected_btc_pin = get_settings().HISTORICAL_CANONICAL_RUN_BTC
    assert expected_btc_pin == "RUN-BTC-USD-20260831-173607"

    resolved = service.resolve_canonical_run("BTC/USD")
    assert resolved == expected_btc_pin


def test_canonical_pin_b_xau_current():
    """Test B: Current XAU pin resolves RUN-XAU-USD-20260831-174452 on production DB."""
    service = HistoricalEvidenceService()
    expected_xau_pin = get_settings().HISTORICAL_CANONICAL_RUN_XAU
    assert expected_xau_pin == "RUN-XAU-USD-20260831-174452"

    resolved = service.resolve_canonical_run("XAU/USD")
    assert resolved == expected_xau_pin


def test_canonical_c_future_exploratory_run_blocked(tmp_path):
    """
    Test C: Newer exploratory completed backtest run (N=20) created LATER must NOT
    replace or promote over the configured canonical run (N=1032).
    """
    db_file = str(tmp_path / "exploratory_test.db")
    _init_test_db(db_file)

    canonical_id = "RUN-BTC-USD-20260831-173607"
    exploratory_id = "RUN-BTC-USD-20260915-999999"

    with sqlite3.connect(db_file) as conn:
        # 1. Insert Canonical Run (created earlier, N=1032 trades)
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at, total_trades_generated)
            VALUES (?, 'BTC/USD', 'COMPLETED', '2026-08-31T17:36:07Z', 1032)
        """, (canonical_id,))
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES (?, '{"type": "canonical"}', '2026-08-31T17:40:00Z')
        """, (canonical_id,))
        for i in range(1032):
            conn.execute("""
                INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r)
                VALUES (?, ?, 'BTC/USD', ?, 'BUY', 65, 'Trending', 'WIN', 1.5)
            """, (f"CANON-{i}", canonical_id, f"2024-01-01T{i%24:02d}:00:00Z"))

        # 2. Insert Newer Exploratory Run (created later, N=20 trades, status=COMPLETED, has report)
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at, total_trades_generated)
            VALUES (?, 'BTC/USD', 'COMPLETED', '2026-09-15T12:00:00Z', 20)
        """, (exploratory_id,))
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES (?, '{"type": "exploratory"}', '2026-09-15T12:05:00Z')
        """, (exploratory_id,))
        for i in range(20):
            conn.execute("""
                INSERT INTO historical_signals (signal_id, run_id, symbol, signal_timestamp, direction, confluence_score, market_regime, outcome, realized_r)
                VALUES (?, ?, 'BTC/USD', ?, 'BUY', 65, 'Trending', 'LOSS', -1.0)
            """, (f"EXPLORE-{i}", exploratory_id, f"2024-06-01T{i%24:02d}:00:00Z"))

    # Service with default canonical pin
    service = HistoricalEvidenceService(db_path=db_file, auto_start_learning=False)

    # Resolution must resolve the canonical run, NOT the newer exploratory run
    resolved_run = service.resolve_canonical_run("BTC/USD")
    assert resolved_run == canonical_id
    assert resolved_run != exploratory_id

    # Querying evidence must draw from canonical N=1032, NOT exploratory N=20
    pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })
    assert pkg.sample_size == 1032
    assert pkg.backtest_run_id == canonical_id
    assert pkg.win_rate == 100.0


def test_canonical_d_wrong_symbol_pin_fails_closed(tmp_path):
    """Test D: If BTC canonical pin accidentally points to an XAU run, fail closed."""
    db_file = str(tmp_path / "wrong_symbol.db")
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at)
            VALUES ('RUN-XAU-PIN', 'XAU/USD', 'COMPLETED', '2026-08-31T12:00:00Z')
        """)
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES ('RUN-XAU-PIN', '{}', '2026-08-31T12:05:00Z')
        """)

    # Configure BTC to point to XAU run
    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-XAU-PIN',
    )

    resolved = service.resolve_canonical_run("BTC/USD")
    assert resolved is None  # Must fail closed

    pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })
    assert pkg.status == "NOT_AVAILABLE"
    assert pkg.evidence_quality == "INSUFFICIENT"
    assert pkg.sample_size == 0


def test_canonical_e_missing_run_fails_closed(tmp_path):
    """Test E: If configured canonical run does not exist in DB, fail closed (no newest-run substitution)."""
    db_file = str(tmp_path / "missing_run.db")
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        # A completed run exists, but it is NOT the configured one
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at)
            VALUES ('RUN-RANDOM-OTHER', 'BTC/USD', 'COMPLETED', '2026-08-31T12:00:00Z')
        """)
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES ('RUN-RANDOM-OTHER', '{}', '2026-08-31T12:05:00Z')
        """)

    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-NONEXISTENT',
    )

    resolved = service.resolve_canonical_run("BTC/USD")
    assert resolved is None  # Must NOT substitute RUN-RANDOM-OTHER

    pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })
    assert pkg.status == "NOT_AVAILABLE"
    assert pkg.evidence_quality == "INSUFFICIENT"
    assert pkg.sample_size == 0


def test_canonical_f_incomplete_run_fails_closed(tmp_path):
    """Test F: If configured run is RUNNING or FAILED, fail closed."""
    db_file = str(tmp_path / "incomplete_run.db")
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at)
            VALUES ('RUN-INCOMPLETE', 'BTC/USD', 'RUNNING', '2026-08-31T12:00:00Z')
        """)
        conn.execute("""
            INSERT INTO backtest_reports (run_id, report_json, created_at)
            VALUES ('RUN-INCOMPLETE', '{}', '2026-08-31T12:05:00Z')
        """)

    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-INCOMPLETE',
    )

    resolved = service.resolve_canonical_run("BTC/USD")
    assert resolved is None  # Incomplete status must fail closed

    pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })
    assert pkg.status == "NOT_AVAILABLE"
    assert pkg.evidence_quality == "INSUFFICIENT"
    assert pkg.sample_size == 0


def test_canonical_g_missing_report_fails_closed(tmp_path):
    """Test G: If configured run is COMPLETED but missing from backtest_reports, fail closed."""
    db_file = str(tmp_path / "missing_report.db")
    _init_test_db(db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            INSERT INTO backtest_runs (run_id, symbol, status, created_at)
            VALUES ('RUN-NO-REPORT', 'BTC/USD', 'COMPLETED', '2026-08-31T12:00:00Z')
        """)
        # Notice: NO backtest_reports entry inserted!

    service = HistoricalEvidenceService(
        db_path=db_file,
        auto_start_learning=False,
        canonical_run_btc='RUN-NO-REPORT',
    )

    resolved = service.resolve_canonical_run("BTC/USD")
    assert resolved is None  # Missing report must fail closed

    pkg = service._query_empirical_evidence({
        'symbol': 'BTC/USD', 'direction': 'BUY', 'confluence_score': 65,
        'score_band': '60-69', 'market_regime': 'Trending', 'contributors': {}
    })
    assert pkg.status == "NOT_AVAILABLE"
    assert pkg.evidence_quality == "INSUFFICIENT"
    assert pkg.sample_size == 0
