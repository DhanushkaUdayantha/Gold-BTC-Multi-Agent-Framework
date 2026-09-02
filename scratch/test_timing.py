import sys
import os
sys.path.insert(0, os.path.abspath("."))

import time
from src.services.market_service import get_market_service
from src.services.technical_service import get_technical_service
from src.services.ai_service import get_ai_service
from src.services.decision_service import get_decision_service
from src.models.market_data import Timeframe

print("Testing market service get_live_price...")
t0 = time.time()
ms = get_market_service()
p = ms.get_live_price("XAU-USD-SPOT")
print(f"Price: {p.price}, provider: {p.provider}, took: {time.time() - t0:.3f}s")

print("\nTesting market service get_candles (15m)...")
t0 = time.time()
c = ms.get_candles("XAU-USD-SPOT", Timeframe.M15, 120)
print(f"Candles count: {c.count}, provider: {c.provider}, took: {time.time() - t0:.3f}s")

print("\nTesting technical service analyze (15m)...")
t0 = time.time()
ts = get_technical_service()
tech = ts.analyze("XAU-USD-SPOT", Timeframe.M15)
print(f"Technical trend: {tech.trend.direction.value}, took: {time.time() - t0:.3f}s")

print("\nTesting decision service get_decision...")
t0 = time.time()
ds = get_decision_service()
d, b = ds.get_decision("XAU-USD-SPOT", force_refresh=True)
print(f"Decision: {d.decision.value}, confidence: {d.confidence}, took: {time.time() - t0:.3f}s")

print("\nTesting BTC price...")
t0 = time.time()
p_btc = ms.get_live_price("BTC-USD")
print(f"BTC Price: {p_btc.price}, provider: {p_btc.provider}, took: {time.time() - t0:.3f}s")

print("\nTesting BTC candles...")
t0 = time.time()
c_btc = ms.get_candles("BTC-USD", Timeframe.M15, 120)
print(f"BTC Candles count: {c_btc.count}, provider: {c_btc.provider}, took: {time.time() - t0:.3f}s")
