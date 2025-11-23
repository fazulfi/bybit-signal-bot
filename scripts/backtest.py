# scripts/backtest.py
import sys
from pathlib import Path
import argparse
import json
import math
import pandas as pd
from datetime import datetime

# Make sure repo root is in path so "src.*" imports work when launching script direct.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Now imports from your codebase
from src.utils.indicators import compute_indicators
from src.workers.signal_engine import detect_signal

# -------------------------
# Helpers
# -------------------------
def load_historical_csv(path: str):
    df = pd.read_csv(path, parse_dates=["timestamp"])

    # Jika sudah timezone-aware, tidak perlu di-localize
    # Jika tidak aware (naive), jadikan UTC
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

def naive_pnl_from_signals(sig_df):
    """
    Very naive backtest:
    - For each symbol, iterate signals in time order.
    - On BUY: open long at price. On SELL: close long at price and record return.
    - Ignore NONE signals. No fees, no slippage, no sizing logic.
    """
    rows = []
    grouped = sig_df[sig_df.signal.isin(["BUY","SELL"])].groupby("symbol")
    for symbol, g in grouped:
        g = g.sort_values("timestamp")
        pos = None  # (entry_price, entry_time)
        for _, r in g.iterrows():
            if r["signal"] == "BUY":
                if pos is None:
                    pos = (r["price"], r["timestamp"])
            elif r["signal"] == "SELL":
                if pos is not None:
                    entry_price, entry_ts = pos
                    exit_price, exit_ts = r["price"], r["timestamp"]
                    ret = (exit_price / entry_price) - 1.0 if entry_price and entry_price>0 else None
                    rows.append({
                        "symbol": symbol,
                        "entry_ts": entry_ts,
                        "exit_ts": exit_ts,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return": ret,
                    })
                    pos = None
        # optionally ignore open positions at end
    return pd.DataFrame(rows)

# -------------------------
# Main backtest logic
# -------------------------
def backtest_single(csv_path, symbol, timeframe, ema_fast, ema_slow, rsi_period, window_min):
    print(f"[BACKTEST] symbol={symbol}, file={csv_path}, TF={timeframe}")
    df = load_historical_csv(csv_path)
    if len(df) < window_min:
        print(f"[WARN] Not enough bars ({len(df)}) < window_min ({window_min}), skipping.")
        return pd.DataFrame(), {}

    results = []
    # Walk-forward: compute indicators on windows to emulate streaming feed
    for i in range(window_min, len(df)):
        slice_df = df.iloc[: i+1].copy()
        slice_ind = compute_indicators(slice_df, ema_fast=ema_fast, ema_slow=ema_slow, rsi_period=rsi_period)
        signal = detect_signal(slice_ind, symbol, debounce_minutes=0)  # disable debounce for backtest
        ts = slice_ind["timestamp"].iloc[-1]
        price = float(slice_ind["close"].iloc[-1])
        results.append({"timestamp": ts, "symbol": symbol, "signal": signal, "price": price})

    res_df = pd.DataFrame(results)
    return res_df, {"n_bars": len(df)}

def main():
    parser = argparse.ArgumentParser(description="Backtest signal engine on historical CSV")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT"], help="Symbol names (no slash e.g. BTCUSDT) corresponding to csv files")
    parser.add_argument("--tf", default="15m", help="Timeframe (meta only)")
    parser.add_argument("--data-dir", default="data", help="Directory where historical_{SYMBOL}_{TF}.csv are stored")
    parser.add_argument("--ema-fast", type=int, default=9)
    parser.add_argument("--ema-slow", type=int, default=21)
    parser.add_argument("--rsi-period", type=int, default=14)
    parser.add_argument("--window-min", type=int, default=200)
    parser.add_argument("--out-csv", default="data/backtest_signals.csv")
    parser.add_argument("--out-summary", default="data/backtest_summary.json")
    parser.add_argument("--out-per-symbol", action="store_true", help="Also write per-symbol CSV to data/")
    args = parser.parse_args()

    all_signals = []
    summary = {"symbols": {}, "params": {
        "ema_fast": args.ema_fast, "ema_slow": args.ema_slow, "rsi_period": args.rsi_period, "tf": args.tf
    }}

    for sym in args.symbols:
        # expected csv filename format from fetcher: historical_{SYMBOL}_{TF}.csv (SYMBOL e.g. BTCUSDT)
        csv_name = f"historical_{sym}_{args.tf}.csv"
        csv_path = Path(args.data_dir) / csv_name
        if not csv_path.exists():
            print(f"[ERROR] missing CSV for {sym}: {csv_path} — skip.")
            continue

        res_df, meta = backtest_single(str(csv_path), sym.replace("", "/"), args.tf, args.ema_fast, args.ema_slow, args.rsi_period, args.window_min)
        # note: detect_signal expects symbol like "BTC/USDT" in some code; we pass sym.replace("", "/") above as placeholder; if your detect_signal expects "BTC/USDT" adjust accordingly.
        # We'll normalize symbol label in output to sym (no slash)
        if res_df.empty:
            print(f"[INFO] no result for {sym}")
            continue
        res_df["symbol"] = sym
        all_signals.append(res_df)

        # per-symbol summary
        counts = res_df["signal"].value_counts().to_dict()
        summary["symbols"][sym] = {"bars": meta.get("n_bars", None), "signal_counts": counts}

        if args.out_per_symbol:
            out_path = Path(args.data_dir) / f"backtest_signals_{sym}_{args.tf}.csv"
            res_df.to_csv(out_path, index=False)
            print(f"[SAVED] per-symbol signals -> {out_path}")

    if not all_signals:
        print("[DONE] No signals collected.")
        return

    all_df = pd.concat(all_signals, ignore_index=True)
    all_df = all_df.sort_values(["symbol","timestamp"]).reset_index(drop=True)

    # write combined CSV
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(out_csv, index=False)
    print(f"[SAVED] Combined backtest signals -> {out_csv}")

    # compute naive pnl
    pnl_df = naive_pnl_from_signals(all_df)
    summary["pnl_stats"] = {
        "trades": len(pnl_df),
        "mean_return": float(pnl_df["return"].mean()) if not pnl_df.empty else None,
        "median_return": float(pnl_df["return"].median()) if not pnl_df.empty else None,
    }
    # Save summary
    out_summary = Path(args.out_summary)
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    with open(out_summary, "w") as f:
        json.dump(summary, f, default=str, indent=2)
    print(f"[SAVED] Summary -> {out_summary}")

    # Also store simple trades file if exist
    if not pnl_df.empty:
        trades_path = out_csv.parent / f"backtest_trades_summary.csv"
        pnl_df.to_csv(trades_path, index=False)
        print(f"[SAVED] Trades -> {trades_path}")

if __name__ == "__main__":
    main()
