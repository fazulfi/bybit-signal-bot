# src/workers/fetcher.py
import ccxt
import pandas as pd
from datetime import datetime
from src.config import BYBIT_API_KEY, BYBIT_API_SECRET, TIMEFRAME


# =========================================================
# CREATE EXCHANGE
# =========================================================
def create_exchange(default_type: str = "spot"):
    """
    Membuat instance ccxt.bybit dengan API key dari .env
    """
    opts = {
        "apiKey": BYBIT_API_KEY or None,
        "secret": BYBIT_API_SECRET or None,
        "enableRateLimit": True,
        "options": {
            "defaultType": default_type,
            "adjustForTimeDifference": True,
        }
    }

    ex = ccxt.bybit(opts)
    return ex


# =========================================================
# LIST USDT PAIRS
# =========================================================
def list_usdt_pairs(ex):
    """
    Ambil semua pasangan USDT dari Bybit.
    Mengambil dari market spot (defaultType=spot).
    """
    try:
        markets = ex.load_markets()
    except Exception as e:
        print("Failed to load markets:", e)
        return []

    usdt_pairs = [
        m for m in markets.keys()
        if m.endswith("/USDT")
    ]

    return usdt_pairs


# =========================================================
# FETCH OHLCV
# =========================================================
def fetch_ohlcv_df(ex, symbol: str, timeframe: str = TIMEFRAME, limit: int = 200):
    """
    Ambil dataframe OHLCV (Open-High-Low-Close-Volume)
    """
    try:
        ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception as e:
        print(f"Failed to fetch OHLCV {symbol}:", e)
        return None

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    return df
