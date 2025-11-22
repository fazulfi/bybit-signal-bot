# src/utils/indicators.py
"""
Simple indicator helpers (pandas-only).
Functions:
 - ema(series, span) -> pd.Series
 - sma(series, window) -> pd.Series
 - rsi(series, period) -> pd.Series
 - compute_indicators(df, close_col='close', ema_fast=9, ema_slow=21, rsi_period=14)
    -> returns df copy with columns: ema_fast, ema_slow, rsi
Notes:
 - Expects a pandas.DataFrame with a 'close' column (or name supplied).
 - No TA-Lib dependency.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def ema(series: pd.Series, span: int) -> pd.Series:
    """
    Exponential moving average. Uses pandas ewm.
    Returns a series aligned with the input index.
    """
    if series is None or len(series) == 0:
        return pd.Series(dtype="float64", index=series.index if series is not None else None)
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """
    Simple moving average.
    """
    if series is None or len(series) == 0:
        return pd.Series(dtype="float64", index=series.index if series is not None else None)
    return series.rolling(window=window, min_periods=1).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI) using Wilder's smoothing (EMA-like).
    Returns a series aligned with the input index. Produces values in [0,100].
    """
    if series is None or len(series) == 0:
        return pd.Series(dtype="float64", index=series.index if series is not None else None)

    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -1 * delta.clip(upper=0.0)

    # Wilder's smoothing: use exponential weighted moving average with alpha = 1/period
    roll_up = up.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()
    roll_down = down.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()

    rs = roll_up / roll_down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(0.0)
    return rsi


def compute_indicators(
    df: pd.DataFrame,
    close_col: str = "close",
    ema_fast: int = 9,
    ema_slow: int = 21,
    rsi_period: int = 14,
) -> pd.DataFrame:
    """
    Compute indicators on dataframe clone and return it.
    Adds columns:
      - ema_fast
      - ema_slow
      - rsi
    The function will not modify the input df in-place.
    """
    if close_col not in df.columns:
        raise ValueError(f"Close column '{close_col}' not found in DataFrame")

    out = df.copy()
    close = out[close_col].astype(float)

    out["ema_fast"] = ema(close, span=ema_fast)
    out["ema_slow"] = ema(close, span=ema_slow)
    out["rsi"] = rsi(close, period=rsi_period)

    return out


# Quick smoke test when module run directly
if __name__ == "__main__":
    import pandas as pd
    # small synthetic example
    prices = pd.Series(
        [100, 101, 102, 101, 103, 105, 107, 106, 108, 110, 111, 112],
        index=pd.date_range("2025-01-01", periods=12, freq="D"),
    )
    df = pd.DataFrame({"close": prices})
    res = compute_indicators(df, ema_fast=3, ema_slow=5, rsi_period=5)
    print(res.tail(6))

