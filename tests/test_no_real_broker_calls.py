"""
Defense-in-Depth Static & Runtime Security Check: No Real Broker Execution.

Verifies:
1. Zero imports of live broker or exchange execution libraries (ccxt, binance, alpaca, ib_insync, oanda, metaapi, etc.).
2. Zero outbound live order routing calls anywhere in the source repository.
3. System remains strictly an advisory and mock paper-trading research platform.
"""
import os
import ast
import pytest

_FORBIDDEN_MODULES = {
    "ccxt",
    "binance",
    "binance.client",
    "alpaca",
    "alpaca_trade_api",
    "ib_insync",
    "interactive_brokers",
    "oandapyV20",
    "metaapi_cloud_sdk",
    "bybit",
    "coinbase_advanced_py",
}

_FORBIDDEN_EXECUTION_CALLS = {
    "create_order",
    "place_order",
    "send_order",
    "submit_order",
    "cancel_order",
    "execute_live_trade",
    "execute_broker_order",
}


def test_static_ast_scan_for_forbidden_broker_imports():
    """Scan all python files under src/ to ensure zero broker imports exist."""
    src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    violations = []

    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as file_content:
                    tree = ast.parse(file_content.read(), filename=path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name in _FORBIDDEN_MODULES:
                                    violations.append((path, alias.name))
                        elif isinstance(node, ast.ImportFrom):
                            if node.module in _FORBIDDEN_MODULES:
                                violations.append((path, node.module))

    assert len(violations) == 0, f"Found forbidden broker imports: {violations}"


def test_static_code_scan_for_live_order_execution():
    """Scan all python files under src/ to ensure zero broker execution keywords exist."""
    src_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    violations = []

    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8", errors="ignore") as file_content:
                    text = file_content.read()
                    for call_name in _FORBIDDEN_EXECUTION_CALLS:
                        if f"{call_name}(" in text:
                            violations.append((path, call_name))

    assert len(violations) == 0, f"Found forbidden broker execution calls: {violations}"
