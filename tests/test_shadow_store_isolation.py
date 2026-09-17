"""
Deterministic Regression Test Suite: Strict Shadow Store Isolation.
Tests A through F verifying physical and logical decoupling between:
- Manual Paper Trades (paper_trading.json)
- Forward Shadow Signals (forward_shadow_signals)
- ML Shadow Observations (ml_shadow_observations)
- Asset boundaries (BTC vs XAU)
"""
import os
import json
import sqlite3
import pytest
from pathlib import Path

from src.services.paper_trading_service import PaperTradingService
from src.research.governance.forward_shadow import ForwardShadowEngine
from src.research.ml_shadow.shadow_store import MLShadowStore
from src.research.ml_shadow.models import MLShadowPrediction

@pytest.fixture
def isolated_shadow_env(tmp_path, monkeypatch):
    """Provides fully isolated temporary stores for paper trading and shadow databases."""
    pt_file = str(tmp_path / "paper_trading.json")
    db_file = str(tmp_path / "test_market_data.db")
    
    monkeypatch.setattr("src.services.paper_trading_service._PT_FILE_PATH", pt_file)
    
    engine = ForwardShadowEngine(db_path=db_file)
    ml_store = MLShadowStore(db_path=db_file)
    pt_service = PaperTradingService()
    
    return {
        "pt_service": pt_service,
        "engine": engine,
        "ml_store": ml_store,
        "pt_file": pt_file,
        "db_file": db_file,
    }

def test_a_manual_reset_preserves_forward_shadow(isolated_shadow_env):
    """Test A: Resetting manual trades MUST NOT delete forward shadow signals."""
    pt = isolated_shadow_env["pt_service"]
    engine = isolated_shadow_env["engine"]
    db_file = isolated_shadow_env["db_file"]
    
    # 1. Create manual trade
    order = pt.open_manual_trade(direction="BUY", entry_price=75000.0)
    assert order is not None
    records = [t for t in pt._load_from_file() if t["status"] == "OPEN"]
    assert len(records) == 1
    
    # 2. Record forward shadow signal
    snap = engine.capture_forward_signal(
        asset="BTC/USD",
        direction="BUY",
        entry_price=75000.0,
        stop_loss=74000.0,
        take_profit_1=76500.0,
        take_profit_2=77500.0,
        confluence_score=68.0,
        confidence_score=70.0,
        signal_strength=68.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ai_bias="BULLISH",
        ai_confidence=75,
        ml_raw_probability=0.62,
        ml_calibrated_probability=0.61,
        strategy_version="v2.1",
        features_dict={"factor": "test"}
    )
    assert snap is not None
    
    # 3. Reset manual trades
    pt.reset_account()
    
    # 4. Verify manual trades reset, forward shadow strictly preserved
    records_after = [t for t in pt._load_from_file() if t["status"] == "OPEN"]
    assert len(records_after) == 0
    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT signal_id, asset, direction FROM forward_shadow_signals WHERE signal_id=?", (snap.signal_id,)).fetchone()
    assert row is not None
    assert row[0] == snap.signal_id
    assert row[1] == "BTC/USD"
    assert row[2] == "BUY"

def test_b_manual_reset_preserves_ml_shadow(isolated_shadow_env):
    """Test B: Resetting manual trades MUST NOT delete ML shadow observations."""
    pt = isolated_shadow_env["pt_service"]
    ml_store = isolated_shadow_env["ml_store"]
    
    # 1. Create manual trade
    pt.open_manual_trade(direction="SELL", entry_price=2700.0)
    records = [t for t in pt._load_from_file() if t["status"] == "OPEN"]
    assert len(records) == 1
    
    # 2. Record ML shadow observation
    pred = MLShadowPrediction(
        observation_id="ML-OBS-TEST-001",
        symbol="XAU/USD",
        timestamp_t0="2026-09-03T12:00:00Z",
        production_decision="SELL",
        confluence_score=64,
        technical_score=65,
        quality_gate_passed=True,
        ml_model_name="RandomForest",
        ml_model_version="v1.0.0-research",
        ml_probability=0.56,
        ml_predicted_class=1,
        entry_price=2700.0,
        stop_loss=2710.0,
        take_profit_1=2685.0,
        take_profit_2=2675.0,
        session="NY",
        market_regime="Bear Trend",
        features_snapshot={"factor": "test"}
    )
    assert ml_store.save_observation(pred) is True
    assert ml_store.get_observation("ML-OBS-TEST-001") is not None
    
    # 3. Reset manual trades
    pt.reset_account()
    
    # 4. Verify manual trades reset, ML shadow strictly preserved
    records_after = [t for t in pt._load_from_file() if t["status"] == "OPEN"]
    assert len(records_after) == 0
    saved_obs = ml_store.get_observation("ML-OBS-TEST-001")
    assert saved_obs is not None
    assert saved_obs["observation_id"] == "ML-OBS-TEST-001"
    assert saved_obs["symbol"] == "XAU/USD"

def test_c_clear_forward_shadow_preserves_manual_and_ml(isolated_shadow_env):
    """Test C: Clearing forward shadow signals preserves manual trades and ML shadow."""
    pt = isolated_shadow_env["pt_service"]
    engine = isolated_shadow_env["engine"]
    ml_store = isolated_shadow_env["ml_store"]
    db_file = isolated_shadow_env["db_file"]
    
    pt.open_manual_trade(direction="BUY", entry_price=76000.0)
    
    snap = engine.capture_forward_signal(
        asset="BTC/USD",
        direction="BUY",
        entry_price=76000.0,
        stop_loss=75000.0,
        take_profit_1=77500.0,
        take_profit_2=78500.0,
        confluence_score=70.0,
        confidence_score=72.0,
        signal_strength=70.0,
        market_regime="Bull Trend",
        session="London",
        mtf_aligned=True,
        ai_bias="BULLISH",
        ai_confidence=80,
        ml_raw_probability=0.65,
        ml_calibrated_probability=0.64,
        strategy_version="v2.1",
        features_dict={"factor": "test"}
    )
    
    pred = MLShadowPrediction(
        observation_id="ML-OBS-TEST-002",
        symbol="BTC/USD",
        timestamp_t0="2026-09-03T12:00:00Z",
        production_decision="BUY",
        confluence_score=70,
        technical_score=70,
        quality_gate_passed=True,
        ml_model_name="LogisticRegression",
        ml_model_version="v1.0.0-research",
        ml_probability=0.59,
        ml_predicted_class=1,
        entry_price=76000.0,
        stop_loss=75000.0,
        take_profit_1=77500.0,
        take_profit_2=78500.0,
        session="London",
        market_regime="Bull Trend",
        features_snapshot={"factor": "test"}
    )
    ml_store.save_observation(pred)
    
    # Clear forward shadow table in isolated test DB
    with sqlite3.connect(db_file) as conn:
        conn.execute("DELETE FROM forward_shadow_signals")
        conn.commit()
        
    with sqlite3.connect(db_file) as conn:
        count = conn.execute("SELECT COUNT(*) FROM forward_shadow_signals").fetchone()[0]
    assert count == 0
    
    # Verify manual trades and ML shadow are completely preserved
    records = [t for t in pt._load_from_file() if t["status"] == "OPEN"]
    assert len(records) == 1
    
    saved_obs = ml_store.get_observation("ML-OBS-TEST-002")
    assert saved_obs is not None
    assert saved_obs["observation_id"] == "ML-OBS-TEST-002"

def test_d_clear_ml_shadow_preserves_manual_and_forward(isolated_shadow_env):
    """Test D: Clearing ML shadow observations preserves manual trades and forward shadow."""
    pt = isolated_shadow_env["pt_service"]
    engine = isolated_shadow_env["engine"]
    ml_store = isolated_shadow_env["ml_store"]
    db_file = isolated_shadow_env["db_file"]
    
    pt.open_manual_trade(direction="BUY", entry_price=2710.0)
    
    snap = engine.capture_forward_signal(
        asset="XAU/USD",
        direction="BUY",
        entry_price=2710.0,
        stop_loss=2700.0,
        take_profit_1=2725.0,
        take_profit_2=2735.0,
        confluence_score=66.0,
        confidence_score=68.0,
        signal_strength=66.0,
        market_regime="Bull Trend",
        session="NY",
        mtf_aligned=True,
        ai_bias="BULLISH",
        ai_confidence=70,
        ml_raw_probability=0.60,
        ml_calibrated_probability=0.58,
        strategy_version="v2.1",
        features_dict={"factor": "test"}
    )
    
    pred = MLShadowPrediction(
        observation_id="ML-OBS-TEST-003",
        symbol="XAU/USD",
        timestamp_t0="2026-09-03T12:00:00Z",
        production_decision="BUY",
        confluence_score=66,
        technical_score=66,
        quality_gate_passed=True,
        ml_model_name="RandomForest",
        ml_model_version="v1.0.0-research",
        ml_probability=0.54,
        ml_predicted_class=1,
        entry_price=2710.0,
        stop_loss=2700.0,
        take_profit_1=2725.0,
        take_profit_2=2735.0,
        session="NY",
        market_regime="Bull Trend",
        features_snapshot={"factor": "test"}
    )
    ml_store.save_observation(pred)
    
    # Clear ML shadow table in isolated test DB
    with sqlite3.connect(db_file) as conn:
        conn.execute("DELETE FROM ml_shadow_observations")
        conn.commit()
        
    assert ml_store.get_observation("ML-OBS-TEST-003") is None
    records = [t for t in pt._load_from_file() if t["status"] == "OPEN"]
    assert len(records) == 1
    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT signal_id FROM forward_shadow_signals WHERE signal_id=?", (snap.signal_id,)).fetchone()
    assert row is not None
    assert row[0] == snap.signal_id

def test_e_btc_operations_do_not_affect_xau(isolated_shadow_env):
    """Test E: Operations on BTC must NOT modify XAU records."""
    engine = isolated_shadow_env["engine"]
    db_file = isolated_shadow_env["db_file"]
    
    snap_xau = engine.capture_forward_signal(
        asset="XAU/USD",
        direction="BUY",
        entry_price=2700.0,
        stop_loss=2690.0,
        take_profit_1=2715.0,
        take_profit_2=2725.0,
        confluence_score=65.0,
        confidence_score=67.0,
        signal_strength=65.0,
        market_regime="Bull Trend",
        session="NY",
        mtf_aligned=True,
        ai_bias="BULLISH",
        ai_confidence=72,
        ml_raw_probability=0.58,
        ml_calibrated_probability=0.57,
        strategy_version="v2.1",
        features_dict={"asset": "XAU"}
    )
    
    snap_btc = engine.capture_forward_signal(
        asset="BTC/USD",
        direction="SELL",
        entry_price=78000.0,
        stop_loss=79000.0,
        take_profit_1=76500.0,
        take_profit_2=75500.0,
        confluence_score=72.0,
        confidence_score=75.0,
        signal_strength=72.0,
        market_regime="Bear Trend",
        session="London",
        mtf_aligned=True,
        ai_bias="BEARISH",
        ai_confidence=80,
        ml_raw_probability=0.67,
        ml_calibrated_probability=0.66,
        strategy_version="v2.1",
        features_dict={"asset": "BTC"}
    )
    
    # Update BTC signal only
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE forward_shadow_signals SET status='RESOLVED', outcome='WIN', realized_r=1.5 WHERE signal_id=?", (snap_btc.signal_id,))
        conn.commit()
        
    # Check XAU signal: must remain PENDING and outcome None
    with sqlite3.connect(db_file) as conn:
        xau_row = conn.execute("SELECT status, outcome, realized_r FROM forward_shadow_signals WHERE signal_id=?", (snap_xau.signal_id,)).fetchone()
    assert xau_row[0] == "PENDING"
    assert xau_row[1] is None
    assert xau_row[2] is None

def test_f_xau_operations_do_not_affect_btc(isolated_shadow_env):
    """Test F: Operations on XAU must NOT modify BTC records."""
    ml_store = isolated_shadow_env["ml_store"]
    
    pred_btc = MLShadowPrediction(
        observation_id="ML-BTC-001",
        symbol="BTC/USD",
        timestamp_t0="2026-09-03T12:00:00Z",
        production_decision="BUY",
        confluence_score=65,
        technical_score=65,
        quality_gate_passed=True,
        ml_model_name="LogisticRegression",
        ml_model_version="v1.0.0-research",
        ml_probability=0.59,
        ml_predicted_class=1,
        entry_price=77000.0,
        stop_loss=76000.0,
        take_profit_1=78500.0,
        take_profit_2=79500.0,
        session="London",
        market_regime="Bull Trend",
        features_snapshot={"factor": "test"}
    )
    ml_store.save_observation(pred_btc)
    
    pred_xau = MLShadowPrediction(
        observation_id="ML-XAU-001",
        symbol="XAU/USD",
        timestamp_t0="2026-09-03T12:00:00Z",
        production_decision="SELL",
        confluence_score=68,
        technical_score=68,
        quality_gate_passed=True,
        ml_model_name="RandomForest",
        ml_model_version="v1.0.0-research",
        ml_probability=0.52,
        ml_predicted_class=0,
        entry_price=2705.0,
        stop_loss=2715.0,
        take_profit_1=2690.0,
        take_profit_2=2680.0,
        session="NY",
        market_regime="Bear Trend",
        features_snapshot={"factor": "test"}
    )
    ml_store.save_observation(pred_xau)
    ml_store.resolve_observation_outcome("ML-XAU-001", outcome="WIN", exit_price=2690.0, realized_r=1.5, outcome_timestamp="2026-09-03T13:00:00Z", duration_minutes=60.0)
    
    saved_btc = ml_store.get_observation("ML-BTC-001")
    assert saved_btc["outcome"] == "PENDING"
    assert saved_btc["realized_r"] is None
    
    btc_obs = ml_store.get_all_observations(symbol="BTC/USD")
    xau_obs = ml_store.get_all_observations(symbol="XAU/USD")
    assert len(btc_obs) == 1
    assert len(xau_obs) == 1
    assert btc_obs[0]["observation_id"] == "ML-BTC-001"
    assert xau_obs[0]["observation_id"] == "ML-XAU-001"
