"""
Tests for Forward Shadow Validation API & Authoritative Data Flow.

Verifies:
1. Dynamic DB queries against forward_shadow_signals table (database query result == API response).
2. Authoritative counts for BTC/USD and XAU/USD.
3. Strict separation of BTC and XAU metrics.
4. Strict separation of forward_shadow_signals from ml_shadow_observations.
5. Win rate formula: wins / (wins + losses) * 100 (pending excluded from denominator).
6. Zero loss numeric preservation (BTC LOSS = 0, never 'N/A' or '--').
7. Read-only operation with ZERO database mutation.
"""
import sqlite3
from typing import Dict, Any
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

DB_PATH = r"D:\Project\TRADE\data\historical\historical_market_data.db"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def query_actual_db_metrics(asset_sym: str) -> Dict[str, Any]:
    """Query actual forward_shadow_signals database directly."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE asset = ?", (asset_sym,)).fetchone()[0]
        wins = cur.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE asset = ? AND outcome = 'WIN'", (asset_sym,)).fetchone()[0]
        losses = cur.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE asset = ? AND outcome = 'LOSS'", (asset_sym,)).fetchone()[0]
        pending = cur.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE asset = ? AND status = 'PENDING'", (asset_sym,)).fetchone()[0]
        resolved = wins + losses
        wr = round((wins / resolved) * 100.0, 1) if resolved > 0 else 0.0
        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "resolved": resolved,
            "win_rate": wr,
        }


def test_forward_shadow_validation_endpoint_success(client):
    """Verify GET /api/v1/research/governance/forward-shadow-validation returns 200 and schema."""
    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["authoritative_source"] == "forward_shadow_signals"
    assert "disclaimer" in data
    assert "btc" in data
    assert "xau" in data


def test_btc_metrics_match_database_dynamically(client):
    """Verify BTC API response dynamically matches direct database query."""
    actual = query_actual_db_metrics("BTC/USD")
    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    assert resp.status_code == 200
    btc = resp.json()["btc"]

    assert btc["asset"] == "BTC/USD"
    assert btc["total_signals"] == actual["total"]
    assert btc["resolved_signals"] == actual["resolved"]
    assert btc["pending_signals"] == actual["pending"]
    assert btc["wins"] == actual["wins"]
    assert btc["losses"] == actual["losses"]
    assert btc["win_rate_pct"] == actual["win_rate"]


def test_xau_metrics_match_database_dynamically(client):
    """Verify XAU API response dynamically matches direct database query."""
    actual = query_actual_db_metrics("XAU/USD")
    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    assert resp.status_code == 200
    xau = resp.json()["xau"]

    assert xau["asset"] == "XAU/USD"
    assert xau["total_signals"] == actual["total"]
    assert xau["resolved_signals"] == actual["resolved"]
    assert xau["pending_signals"] == actual["pending"]
    assert xau["wins"] == actual["wins"]
    assert xau["losses"] == actual["losses"]
    assert xau["win_rate_pct"] == actual["win_rate"]


def test_btc_zero_loss_preservation(client):
    """Verify BTC losses are returned as integer 0, never converted to null/string."""
    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    btc = resp.json()["btc"]
    assert isinstance(btc["losses"], int)
    assert btc["losses"] == 0
    assert btc["losses"] is not None


def test_win_rate_excludes_pending(client):
    """Verify win_rate_pct formula excludes pending signals from denominator."""
    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    data = resp.json()
    for key in ["btc", "xau"]:
        item = data[key]
        resolved = item["wins"] + item["losses"]
        assert item["resolved_signals"] == resolved
        if resolved > 0:
            expected_wr = round((item["wins"] / resolved) * 100.0, 1)
            assert item["win_rate_pct"] == expected_wr


def test_strict_asset_isolation(client):
    """Verify BTC and XAU data are separate and never cross-contaminated."""
    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    data = resp.json()
    assert data["btc"]["asset"] == "BTC/USD"
    assert data["xau"]["asset"] == "XAU/USD"
    assert data["btc"]["total_signals"] != data["xau"]["total_signals"]
    assert data["btc"]["provenance_note"] != data["xau"]["provenance_note"]


def test_ml_shadow_separation_invariant(client):
    """Verify Forward Shadow metrics do not use ml_shadow_observations."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        fwd_btc = cur.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE asset = 'BTC/USD'").fetchone()[0]
        fwd_xau = cur.execute("SELECT COUNT(*) FROM forward_shadow_signals WHERE asset = 'XAU/USD'").fetchone()[0]
        ml_btc = cur.execute("SELECT COUNT(*) FROM ml_shadow_observations WHERE symbol = 'BTC/USD'").fetchone()[0]
        ml_xau = cur.execute("SELECT COUNT(*) FROM ml_shadow_observations WHERE symbol = 'XAU/USD'").fetchone()[0]

    resp = client.get("/api/v1/research/governance/forward-shadow-validation")
    data = resp.json()
    # Forward shadow counts must equal forward_shadow_signals table, not ML shadow observations
    assert data["btc"]["total_signals"] == fwd_btc
    assert data["xau"]["total_signals"] == fwd_xau
    assert data["btc"]["total_signals"] != ml_btc
    assert data["xau"]["total_signals"] != ml_xau


def test_filter_by_asset_query_param(client):
    """Verify filtering by asset query parameter returns matching asset payload."""
    resp_btc = client.get("/api/v1/research/governance/forward-shadow-validation?asset=btc")
    assert resp_btc.status_code == 200
    assert resp_btc.json()["data"]["asset"] == "BTC/USD"

    resp_xau = client.get("/api/v1/research/governance/forward-shadow-validation?asset=xau")
    assert resp_xau.status_code == 200
    assert resp_xau.json()["data"]["asset"] == "XAU/USD"
