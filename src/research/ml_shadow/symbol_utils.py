"""
Symbol normalization utilities for the ML Shadow layer.

Single source of truth for converting any incoming symbol variant
(BTC-USD, BTC_USD, XAU-USD-SPOT, ...) to the canonical form stored
in ml_shadow_observations (BTC/USD, XAU/USD).

Never duplicated inline. Every entry point (API routes, store,
decision service) imports from here.
"""

__all__ = ["normalize_ml_symbol"]

# Ordered: more-specific patterns first to avoid false matches.
_BTC_MARKERS = ("BTC",)
_XAU_MARKERS = ("XAU", "GOLD", "XAUUSD")

_CANONICAL_BTC = "BTC/USD"
_CANONICAL_XAU = "XAU/USD"


def normalize_ml_symbol(raw: str) -> str:
    """
    Normalize any incoming symbol string to `BTC/USD` or `XAU/USD`.

    Accepted BTC forms: `BTC/USD`, `BTC-USD`, `BTC_USD`, `BTCUSD`.
    Accepted XAU forms: `XAU/USD`, `XAU-USD`, `XAU-USD-SPOT`,
                        `XAU_USD`, `XAUUSD`, `GOLD`.

    Parameters
    ----------
    raw:
        Raw symbol string from an API parameter, query string, or
        internal caller.

    Returns
    -------
    str
        `"BTC/USD"` or `"XAU/USD"`.

    Raises
    ------
    ValueError
        If `raw` cannot be mapped to either canonical form.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError(
            f"normalize_ml_symbol: expected a non-empty string, got {raw!r}"
        )

    upper = raw.strip().upper()

    for marker in _BTC_MARKERS:
        if marker in upper:
            return _CANONICAL_BTC

    for marker in _XAU_MARKERS:
        if marker in upper:
            return _CANONICAL_XAU

    raise ValueError(
        f"normalize_ml_symbol: unrecognized symbol {raw!r}. "
        f"Expected a BTC or XAU/Gold variant (e.g. 'BTC/USD', 'BTC-USD', "
        f"'XAU/USD', 'XAU-USD-SPOT')."
    )
