# scripts/download_historical.py
import os
from datetime import datetime
from src.workers.fetcher import create_exchange   # file kamu ✔️
from src.utils.historical import fetch_full_ohlcv

# =============================================================
# CONFIG — bisa kamu ubah bebas
# =============================================================
SYMBOL = "BTC/USDT"
TIMEFRAME = "15m"
OUTPUT_DIR = "data"

# start fetch
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Creating Bybit exchange...")
    ex = create_exchange(default_type="spot")

    print(f"Fetching full OHLCV for {SYMBOL} {TIMEFRAME} ...")
    df = fetch_full_ohlcv(ex, SYMBOL, TIMEFRAME)

    out_path = f"{OUTPUT_DIR}/historical_{SYMBOL.replace('/', '')}_{TIMEFRAME}.csv"
    df.to_csv(out_path, index=False)

    print(f"\n[SAVED] {len(df)} rows → {out_path}\n")

if __name__ == "__main__":
    main()
