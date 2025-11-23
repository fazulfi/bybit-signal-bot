#!/usr/bin/env python3
"""
Run backtest using a prepared signal CSV (with entry_ts, entry_price, stop_price, take_price).
Outputs:
 - trades.csv
 - summary.json
 - equity_curve.csv
"""
import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import timezone

def load_ohlcv(path):
    df = pd.read_csv(path, parse_dates=["timestamp"], infer_datetime_format=True)
    # ensure tz-aware UTC if possible
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    return df.set_index("timestamp")

def find_exit(ohlcv_idxed, entry_ts, side, stop_price, take_price):
    """
    Starting from entry_ts (inclusive), iterate forward to find first bar where high/low hit TP or SL.
    Return exit_ts, exit_price, exit_reason ('tp'/'sl'/'timeout').
    If neither hit until end, use last close as exit (timeout).
    """
    # slice from entry time
    window = ohlcv_idxed.loc[entry_ts:]
    if window.empty:
        return None, None, "no-data"

    for ts, row in window.iterrows():
        high = row["high"]
        low = row["low"]
        # BUY: TP = take_price higher, SL = stop_price lower
        if side == "BUY":
            if low <= stop_price:
                return ts, stop_price, "sl"
            if high >= take_price:
                return ts, take_price, "tp"
        else:  # SELL: TP lower, SL higher
            if high >= stop_price:
                return ts, stop_price, "sl"
            if low <= take_price:
                return ts, take_price, "tp"
    # no hit -> timeout: use last close
    last_ts = window.index[-1]
    return last_ts, window.iloc[-1]["close"], "timeout"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--signal-csv", required=True)
    p.add_argument("--data-csv", required=True)
    p.add_argument("--out-dir", default="data/backtest_from_signals")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sig_df = pd.read_csv(args.signal_csv, parse_dates=["entry_ts"], infer_datetime_format=True)
    # ensure tz-aware
    if sig_df["entry_ts"].dt.tz is None:
        sig_df["entry_ts"] = sig_df["entry_ts"].dt.tz_localize("UTC")

    ohlcv = load_ohlcv(args.data_csv)

    trades = []
    balance = 10000.0
    equity = []
    for i, r in sig_df.iterrows():
        sym = r["symbol"]
        entry_ts = r["entry_ts"]
        entry_price = float(r["entry_price"])
        side = r.get("signal", "").upper()  # 'BUY' or 'SELL'
        stop_price = float(r["stop_price"])
        take_price = float(r["take_price"])
        sl_pct = float(r.get("sl_pct", 0.01))
        rr = float(r.get("rr", 1.0))

        exit_ts, exit_price, reason = find_exit(ohlcv, entry_ts, side, stop_price, take_price)
        if exit_ts is None:
            continue

        # compute return (simple)
        if side == "BUY":
            ret = (exit_price / entry_price) - 1.0
        else:
            ret = (entry_price / exit_price) - 1.0

        # assume fixed position sizing (e.g. 1 contract) -> compute pnl in %
        trades.append({
            "symbol": sym,
            "entry_ts": entry_ts.isoformat(),
            "exit_ts": getattr(exit_ts, "isoformat", lambda: str(exit_ts))(),
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "return": ret,
            "reason": reason
        })

        # update simple equity (apply return on balance)
        balance = balance * (1.0 + ret)
        equity.append({"timestamp": exit_ts.isoformat(), "equity": balance})

    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(out_dir / "trades.csv", index=False)

    # summary
    if not trades_df.empty:
        net = trades_df["return"].sum()
        win_rate = (trades_df["return"] > 0).mean()
        profit_factor = trades_df[trades_df["return"]>0]["return"].sum() / (abs(trades_df[trades_df["return"]<=0]["return"].sum()) + 1e-12)
        summary = {
            "n_trades": len(trades_df),
            "net_return": float(net),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "final_equity": float(balance)
        }
    else:
        summary = {"n_trades": 0}

    with open(out_dir / "summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    eq_df = pd.DataFrame(equity)
    if not eq_df.empty:
        eq_df.to_csv(out_dir / "equity_curve.csv", index=False)

    print("[SAVED]", "trades ->", out_dir / "trades.csv")
    print("[SAVED]", "summary ->", out_dir / "summary.json")
    print("[SAVED]", "equity ->", out_dir / "equity_curve.csv")

if __name__ == "__main__":
    main()
