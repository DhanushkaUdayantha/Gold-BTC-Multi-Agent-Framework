"""
Phase 2 — ML Shadow Per-Asset Isolation Tests.

Verifies:
1. BTC query returns zero XAU rows (and vice versa).
2. normalize_ml_symbol handles every documented variant for BTC and XAU.
3. normalize_ml_symbol raises ValueError for unrecognized symbols.
4. MLShadowStore.get_all_observations() raises ValueError when symbol is None.
5. /observations API endpoint returns HTTP 422 when symbol is omitted.
"""
import pytest
import os
import tempfile

from fastapi.testclient import TestClient

from src.research.ml_shadow.symbol_utils import normalize_ml_symbol
from src.research.ml_shadow.shadow_store import MLShadowStore
from src.research.ml_shadow.models import MLShadowPrediction


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_store_with_both():
    """Temp SQLite DB seeded with one BTC/USD and one XAU/USD observation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = MLShadowStore(db_path=db_path)

    btc_pred = MLShadowPrediction.create(
        symbol="BTC/USD",
        timestamp_t0="2026-09-01T10:00:00Z",
        production_decision="BUY",
        confluence_score=65,
        technical_score=60,
        quality_gate_passed=True,
        ml_model_name="LogisticRegression",
        ml_model_version="v1.0.0-research",
        ml_probability=0.70,
        ml_predicted_class=1,
        entry_price=60000.0,
        stop_loss=59000.0,
        take_profit_1=61500.0,
        take_profit_2=63000.0,
        session="LONDON",
        market_regime="TRENDING_BULLISH",
        features_snapshot={"confluence_score": 65},
    )
    store.save_observation(btc_pred)

    xau_pred = MLShadowPrediction.create(
        symbol="XAU/USD",
        timestamp_t0="2026-09-01T10:00:00Z",
        production_decision="SELL",
        confluence_score=62,
        technical_score=58,
        quality_gate_passed=True,
        ml_model_name="RandomForestClassifier",
        ml_model_version="v1.0.0-research",
        ml_probability=0.68,
        ml_predicted_class=1,
        entry_price=2500.0,
        stop_loss=2520.0,
        take_profit_1=2470.0,
        take_profit_2=2450.0,
        session="LONDON",
        market_regime="TRENDING_BEARISH",
        features_snapshot={"confluence_score": 62},
    )
    store.save_observation(xau_pred)

    yield store

    if os.path.exists(db_path):
        os.remove(db_path)


# ─── Test 1: BTC query returns zero XAU rows ─────────────────────────────────

class TestCrossAssetLeakagePrevention:

    def test_btc_query_returns_zero_xau_rows(self, temp_store_with_both):
        """Querying BTC/USD must return ONLY BTC rows — no XAU leakage."""
        rows = temp_store_with_both.get_all_observations("BTC/USD")
        assert len(rows) == 1, f"Expected 1 BTC row, got {len(rows)}"
        assert rows[0]["symbol"] == "BTC/USD"
        xau_in_btc = [r for r in rows if "XAU" in r["symbol"]]
        assert len(xau_in_btc) == 0, "XAU observation leaked into BTC query"

    def test_xau_query_returns_zero_btc_rows(self, temp_store_with_both):
        """Querying XAU/USD must return ONLY XAU rows — no BTC leakage."""
        rows = temp_store_with_both.get_all_observations("XAU/USD")
        assert len(rows) == 1, f"Expected 1 XAU row, got {len(rows)}"
        assert rows[0]["symbol"] == "XAU/USD"
        btc_in_xau = [r for r in rows if "BTC" in r["symbol"]]
        assert len(btc_in_xau) == 0, "BTC observation leaked into XAU query"

    def test_btc_variant_query_normalizes_and_returns_btc(self, temp_store_with_both):
        """Querying with 'BTC-USD' must normalize to BTC/USD and return correct rows."""
        rows = temp_store_with_both.get_all_observations("BTC-USD")
        assert len(rows) == 1
        assert rows[0]["symbol"] == "BTC/USD"

    def test_xau_variant_query_normalizes_and_returns_xau(self, temp_store_with_both):
        """Querying with 'XAU-USD-SPOT' must normalize to XAU/USD and return correct rows."""
        rows = temp_store_with_both.get_all_observations("XAU-USD-SPOT")
        assert len(rows) == 1
        assert rows[0]["symbol"] == "XAU/USD"


# ─── Test 2 & 3: normalize_ml_symbol ─────────────────────────────────────────

class TestSymbolNormalization:

    @pytest.mark.parametrize("raw,expected", [
        ("BTC/USD",         "BTC/USD"),
        ("BTC-USD",         "BTC/USD"),
        ("BTC_USD",         "BTC/USD"),
        ("BTCUSD",          "BTC/USD"),
        ("btc/usd",         "BTC/USD"),
        ("btc-usd",         "BTC/USD"),
    ])
    def test_normalize_btc_variants(self, raw, expected):
        assert normalize_ml_symbol(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("XAU/USD",         "XAU/USD"),
        ("XAU-USD",         "XAU/USD"),
        ("XAU-USD-SPOT",    "XAU/USD"),
        ("XAU_USD",         "XAU/USD"),
        ("XAUUSD",          "XAU/USD"),
        ("GOLD",            "XAU/USD"),
        ("gold",            "XAU/USD"),
        ("xau/usd",         "XAU/USD"),
    ])
    def test_normalize_xau_variants(self, raw, expected):
        assert normalize_ml_symbol(raw) == expected

    @pytest.mark.parametrize("bad_symbol", [
        "ETH-USD",
        "EUR/USD",
        "SPX",
        "",
        "   ",
    ])
    def test_unrecognized_symbol_raises_value_error(self, bad_symbol):
        with pytest.raises((ValueError, TypeError)):
            normalize_ml_symbol(bad_symbol)


# ─── Test 4: Store rejects None symbol ───────────────────────────────────────

class TestStoreSymbolEnforcement:

    def test_store_rejects_none_symbol(self, temp_store_with_both):
        """get_all_observations(None) must raise ValueError — never return both assets."""
        with pytest.raises(ValueError, match="symbol is required"):
            temp_store_with_both.get_all_observations(None)

    def test_store_rejects_empty_string_symbol(self, temp_store_with_both):
        """get_all_observations('') must raise ValueError."""
        with pytest.raises(ValueError):
            temp_store_with_both.get_all_observations("")


# ─── Test 5: API endpoint requires symbol ────────────────────────────────────

class TestAPISymbolEnforcement:

    @pytest.fixture
    def client(self):
        """FastAPI TestClient for the main app."""
        from src.api.main import app
        return TestClient(app)

    def test_observations_without_symbol_returns_422(self, client):
        """GET /api/v1/ml/shadow/observations without symbol must return 422."""
        response = client.get("/api/v1/ml/shadow/observations")
        assert response.status_code == 422, (
            f"Expected 422 (missing required param), got {response.status_code}. "
            f"Body: {response.text[:200]}"
        )

    def test_metrics_without_symbol_returns_422(self, client):
        """GET /api/v1/ml/shadow/metrics without symbol must return 422."""
        response = client.get("/api/v1/ml/shadow/metrics")
        assert response.status_code == 422, (
            f"Expected 422 (missing required param), got {response.status_code}. "
            f"Body: {response.text[:200]}"
        )


# ─── Test 6: Strict Asset & Model Version Query Scoping ───────────────────────

class TestMLShadowQueryCrossAssetIsolation:
    """Proves BTC page queries cannot return XAU rows and vice versa, including model_version."""

    def test_btc_query_with_model_version_returns_only_btc_rows(self, temp_store_with_both):
        rows = temp_store_with_both.get_all_observations("BTC/USD", model_version="v1.0.0-research")
        assert len(rows) == 1
        assert rows[0]["symbol"] == "BTC/USD"
        assert rows[0]["ml_model_version"] == "v1.0.0-research"
        assert not any("XAU" in r["symbol"] for r in rows)

    def test_xau_query_with_model_version_returns_only_xau_rows(self, temp_store_with_both):
        rows = temp_store_with_both.get_all_observations("XAU/USD", model_version="v1.0.0-research")
        assert len(rows) == 1
        assert rows[0]["symbol"] == "XAU/USD"
        assert rows[0]["ml_model_version"] == "v1.0.0-research"
        assert not any("BTC" in r["symbol"] for r in rows)

    def test_nonexistent_model_version_returns_empty_without_leaking(self, temp_store_with_both):
        rows = temp_store_with_both.get_all_observations("BTC/USD", model_version="nonexistent-version")
        assert len(rows) == 0

    def test_api_observations_btc_query_never_returns_xau(self):
        from src.api.main import app
        client = TestClient(app)
        res = client.get("/api/v1/ml/shadow/observations?symbol=BTC/USD&limit=50")
        assert res.status_code == 200
        data = res.json()
        for item in data:
            assert item["symbol"] == "BTC/USD", f"Leakage: found {item['symbol']} in BTC query"
            assert "XAU" not in item["symbol"], "XAU row leaked into BTC observations"

    def test_api_observations_xau_query_never_returns_btc(self):
        from src.api.main import app
        client = TestClient(app)
        res = client.get("/api/v1/ml/shadow/observations?symbol=XAU/USD&limit=50")
        assert res.status_code == 200
        data = res.json()
        for item in data:
            assert item["symbol"] == "XAU/USD", f"Leakage: found {item['symbol']} in XAU query"
            assert "BTC" not in item["symbol"], "BTC row leaked into XAU observations"
