# scripts/backtest_rr.py
"""
Backtester simple untuk SL/TP fixed RR.
- Membaca historical CSV (ohlcv) di folder data/
- Memakai fungsi detect_signal() dari src.workers.signal_engine
- Simulasi trade intrabar: jika SL/TP terkena di bar, exit dengan tipe SL/TP.
- Jika reverse signal muncul, close by reverse at close price.
- Output: data/backtest_trades_summary.csv + data/backtest_signals_rr.csv + data/backtest_summary_rr.json
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import argparse
from pathlib import Path
import pandas as pd
import json
from src.workers.signal_engine import detect_signal  # engine full
from src import config

def load_ohlcv_csv(path: Path):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    # ensure tz-aware UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")
    return df

def run_backtest(data_csv: Path, out_dir: Path, sl_pct: float = None, rr: float = None, debounce_minutes: int = 0):
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_ohlcv_csv(data_csv)

    # defaults from config
    if sl_pct is None:
        sl_pct = getattr(config, "SL", 0.01)
    if rr is None:
        rr = getattr(config, "RR", 2.0)

    trades = []
    signals = []

    i = 0
    while i < len(df):
        slice_df = df.iloc[:i+1]  # all bars up to current
        sig = detect_signal(slice_df, symbol="BTCUSDT", debounce_minutes=debounce_minutes, sl_pct=sl_pct, rr=rr)
        if sig:
            # we have entry at current bar close
            entry_price = sig["entry_price"]
            stop_price = sig["stop_price"]
            take_price = sig["take_price"]
            entry_ts = pd.to_datetime(sig["entry_ts"])
            side = sig["side"]

            # record signal
            signals.append({**sig, "bar_index": i, "timestamp": df.index[i].isoformat()})

            # now scan forward from next bar to find exit
            j = i+1
            exited = False
            while j < len(df):
                high = float(df["high"].iloc[j])
                low = float(df["low"].iloc[j])
                close = float(df["close"].iloc[j])
                exit_price = None
                exit_reason = None
                exit_ts = None

                # check intrabar SL/TP by using high/low: assume SL worse-case order: if both hit same bar, choose SL (conservative)
                if side == "BUY":
                    if low <= stop_price:
                        exit_price = stop_price
                        exit_reason = "SL"
                        exit_ts = df.index[j]
                    elif high >= take_price:
                        exit_price = take_price
                        exit_reason = "TP"
                        exit_ts = df.index[j]
                else:  # SELL
                    if high >= stop_price:
                        exit_price = stop_price
                        exit_reason = "SL"
                        exit_ts = df.index[j]
                    elif low <= take_price:
                        exit_price = take_price
                        exit_reason = "TP"
                        exit_ts = df.index[j]

                # if no SL/TP hit, check if reverse signal occurred at bar j (use slice to j)
                if exit_price is None:
                    slice_j = df.iloc[:j+1]
                    rev = detect_signal(slice_j, symbol="BTCUSDT", debounce_minutes=0, sl_pct=sl_pct, rr=rr)
                    # if reverse exists and opposite side -> close at close price
                    if rev and rev.get("side") != side:
                        exit_price = close
                        exit_reason = "Reverse"
                        exit_ts = df.index[j]

                if exit_price is not None:
                    # record trade
                    ret = (exit_price / entry_price - 1) if side == "BUY" else (entry_price / exit_price - 1)
                    trades.append({
                        "symbol": "BTCUSDT",
                        "entry_ts": entry_ts.isoformat(),
                        "exit_ts": exit_ts.isoformat(),
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "side": side,
                        "exit_reason": exit_reason,
                        "return": ret
                    })
                    exited = True
                    break
                j += 1

            # if not exited until end, close at last close
            if not exited:
                last_close = float(df["close"].iloc[-1])
                exit_price = last_close
                exit_reason = "EOD"
                exit_ts = df.index[-1]
                ret = (exit_price / entry_price - 1) if side == "BUY" else (entry_price / exit_price - 1)
                trades.append({
                    "symbol": "BTCUSDT",
                    "entry_ts": entry_ts.isoformat(),
                    "exit_ts": exit_ts.isoformat(),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "side": side,
                    "exit_reason": exit_reason,
                    "return": ret
                })

            # skip forward to j (next bar after exit) to avoid re-entering same bar multiple times
            i = j
            continue

        # else no signal at this bar -> advance
        i += 1

    # outputs
    trades_df = pd.DataFrame(trades)
    signals_df = pd.DataFrame(signals)
    trades_df.to_csv(out_dir / "backtest_trades_summary_rr.csv", index=False)
    signals_df.to_csv(out_dir / "backtest_signals_rr.csv", index=False)

    # compute summary
    if len(trades_df) > 0:
        wins = trades_df[trades_df["return"] > 0]
        losses = trades_df[trades_df["return"] <= 0]
        summary = {
            "n_trades": int(len(trades_df)),
            "win_rate": float(len(wins) / len(trades_df)),
            "avg_win": float(wins["return"].mean()) if len(wins)>0 else 0.0,
            "avg_loss": float(losses["return"].mean()) if len(losses)>0 else 0.0,
            "profit_factor": float(wins["return"].sum() / -losses["return"].sum()) if len(losses)>0 else None,
            "total_return": float((trades_df["return"] + 1.0).prod() - 1.0)
        }
    else:
        summary = {"n_trades": 0}

    with open(out_dir / "backtest_summary_rr.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    return {"trades": trades_df, "signals": signals_df, "summary": summary}

# CLI
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-csv", default="data/historical_BTCUSDT_15m.csv")
    p.add_argument("--out-dir", default="data/backtest_rr_out")
    p.add_argument("--sl-pct", type=float, default=None)
    p.add_argument("--rr", type=float, default=None)
    p.add_argument("--debounce-minutes", type=int, default=0)
    args = p.parse_args()

    out = run_backtest(Path(args.data_csv), Path(args.out_dir), sl_pct=args.sl_pct, rr=args.rr, debounce_minutes=args.debounce_minutes)
    print("Done. summary:", out["summary"])
