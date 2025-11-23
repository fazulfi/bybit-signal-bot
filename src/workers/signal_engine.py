# src/workers/signal_engine.py
"""
Signal Engine (RSI-based) — Step 14 replacement

Logika:
- Jika RSI < RSI_LOW  -> BUY
- Jika RSI > RSI_HIGH -> SELL

Fitur:
- return dict sinyal (symbol, side, entry_price, stop_price, take_price, sl_pct, rr)
- menerima fixed_rr atau sl_pct
- tidak otomatis menulis ke storage / telegram (tetap murni deteksi)
"""
from __future__ import annotations
from typing import Optional, Dict, Any
import pandas as pd
import logging
from datetime import datetime, timezone

from src import config
from src.storage import Storage

# RSI thresholds default
RSI_LOW = 20.0
RSI_HIGH = 80.0


def _safe_last(df: pd.DataFrame, col: str):
    """Ambil nilai terakhir kolom, fallback None jika tidak ada."""
    if col in df.columns and len(df) > 0:
        val = df[col].iloc[-1]
        # jika pandas Timestamp -> kembalikan str ISO
        if hasattr(val, "isoformat"):
            return val
        return val
    return None


def detect_signal(df: pd.DataFrame,
                  symbol: str,
                  debounce_minutes: int = 0,
                  fixed_rr: Optional[float] = None,
                  sl_pct: Optional[float] = None,
                  rsi_low: float = RSI_LOW,
                  rsi_high: float = RSI_HIGH) -> Optional[Dict[str, Any]]:
    """
    Deteksi sinyal berbasis RSI.

    Args:
      df: DataFrame yang sudah berisi kolom indikator (paling penting: 'rsi', 'close').
      symbol: string symbol (mis. "BTCUSDT")
      debounce_minutes: (opsional) tersedia untuk kompatibilitas (tidak dipakai di versi ini).
      fixed_rr: jika diberikan (float), gunakan rasio take-profit = entry + rr * (entry - stop)
      sl_pct: jika diberikan (float), gunakan persentase stoploss dari entry.
      rsi_low / rsi_high: ambang RSI untuk buy/sell.

    Return:
      None jika tidak ada sinyal.
      dict jika ada sinyal:
        {
          'symbol': ...,
          'side': 'BUY'|'SELL',
          'entry_price': float,
          'entry_ts': timestamp (jika tersedia di df),
          'stop_price': float,
          'take_price': float,
          'sl_pct': float or None,
          'rr': float or None
        }
    """
    # safety checks
    if df is None or len(df) < 1:
        return None

    # pastikan kolom rsi dan close ada
    if "rsi" not in df.columns or ("close" not in df.columns and "price" not in df.columns):
        return None

    # ambil nilai terakhir rsi & price & timestamp
    last_rsi = df["rsi"].iloc[-1]
    entry_price = None
    if "close" in df.columns:
        entry_price = float(df["close"].iloc[-1])
    elif "price" in df.columns:
        entry_price = float(df["price"].iloc[-1])

    entry_ts = None
    if "timestamp" in df.columns:
        entry_ts = df["timestamp"].iloc[-1]

    # jika rsi bukan number -> abort
    try:
        last_rsi_val = float(last_rsi)
    except Exception:
        return None

    side = None
    if last_rsi_val <= float(rsi_low):
        side = "BUY"
    elif last_rsi_val >= float(rsi_high):
        side = "SELL"
    else:
        # tidak melewati threshold -> tidak ada sinyal
        return None

    # default sl_pct jika user memberikan fixed_rr saja
    if sl_pct is None and fixed_rr is not None:
        sl_pct = 0.01  # default 1% jika user memakai fixed_rr tanpa sl_pct

    stop_price = None
    take_price = None
    rr_out = float(fixed_rr) if fixed_rr is not None else None
    sl_pct_out = float(sl_pct) if sl_pct is not None else None

    if sl_pct_out is not None:
        if side == "BUY":
            stop_price = entry_price * (1.0 - sl_pct_out)
        else:  # SELL
            stop_price = entry_price * (1.0 + sl_pct_out)

        if rr_out is not None:
            rr = rr_out
            if side == "BUY":
                risk = entry_price - stop_price
                take_price = entry_price + rr * risk
            else:
                risk = stop_price - entry_price
                take_price = entry_price - rr * risk
        else:
            # **Di sini perubahan utama**: default TP approx RR 1:3 when only sl_pct provided
            if side == "BUY":
                take_price = entry_price * (1.0 + sl_pct_out * 3.0)
            else:
                take_price = entry_price * (1.0 - sl_pct_out * 3.0)
    else:
        # cannot compute stop/take without sl_pct; return minimal info
        stop_price = None
        take_price = None

    result = {
        "symbol": symbol,
        "side": side,
        "entry_price": round(entry_price, 8) if entry_price is not None else None,
        "entry_ts": entry_ts if entry_ts is not None else None,
        "stop_price": round(stop_price, 8) if stop_price is not None else None,
        "take_price": round(take_price, 8) if take_price is not None else None,
        "sl_pct": sl_pct_out,
        "rr": rr_out,
        "rsi": round(last_rsi_val, 3),
    }

    return result
