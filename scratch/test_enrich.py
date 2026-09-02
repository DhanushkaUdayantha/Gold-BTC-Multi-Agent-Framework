import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import requests

t0 = time.time()
res = requests.get("https://api.gold-api.com/price/XAU", timeout=5.0)
print(f"Gold-API took: {time.time() - t0:.3f}s, status: {res.status_code}")

t0 = time.time()
url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
res2 = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, params={"interval": "1m", "range": "1d"}, timeout=5.0)
print(f"Yahoo chart took: {time.time() - t0:.3f}s, status: {res2.status_code}")
