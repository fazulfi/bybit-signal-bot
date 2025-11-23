#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import csv
import pandas as pd
from pathlib import Path

# --- sesuaikan parameter di sini jika mau ---
HIST_CSV = "data/historical_BTCUSDT_15m.csv"
OUT_CSV  = "data/signal_history.csv"
SYMBOL   = "BTCUSDT"
EMA_FAST = 3
EMA_SLOW = 6
RSI_PER  = 14
DEBOUNCE = 0        # menit (0 = nonaktif)
FIXED_RR = 1.0      # jika mau fixed RR
SL_PCT   = 0.005     # jika pakai percent-based SL
# ---------------------------------------------

# import engine/utils dari project (harus jalan dari repo root)
from src.utils.indicators import compute_indicators
from src.workers.signal_engine import detect_signal

# load historis
df = pd.read_csv(HIST_CSV, parse_dates=["timestamp"])
# pastikan kolom timestamp ada
if "timestamp" not in df.columns:
    # kalau filenya pakai index datetime, coba set index
    try:
        df.index = pd.to_datetime(df.iloc[:,0])
        df = df.reset_index().rename(columns={"index":"timestamp"})
    except Exception:
        raise SystemExit("Tidak menemukan kolom 'timestamp' di CSV. Periksa file historical CSV kamu.")

# output csv header
out_path = Path(OUT_CSV)
out_path.parent.mkdir(parents=True, exist_ok=True)

with out_path.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.writer(fh)
    writer.writerow(["symbol","entry_ts","entry_price","signal","stop_price","take_price","sl_pct","rr"])

    # loop incremental: ambil slice dari awal sampai bar i (mirip realtime kenapa engine butuh history)
    for i in range(len(df)):
        slice_df = df.iloc[: i+1].copy()
        # hitung indikator pada slice (sesuai fungsi compute_indicators di project)
        slice_ind = compute_indicators(slice_df, ema_fast=EMA_FAST, ema_slow=EMA_SLOW, rsi_period=RSI_PER)
        # panggil detect_signal pada slice (engine harus menerima arg2 ini)
        sig = detect_signal(slice_ind, SYMBOL, debounce_minutes=DEBOUNCE, fixed_rr=FIXED_RR, sl_pct=SL_PCT)
        # bila engine mengembalikan dict/obj sinyal -> simpan
        if sig and isinstance(sig, dict):
            # ambil fields umum (fall back ke None bila ga ada)
            entry_ts   = sig.get("entry_ts") or slice_ind["timestamp"].iloc[-1]
            entry_price= sig.get("entry_price")
            stop_price = sig.get("stop_price")
            take_price = sig.get("take_price")
            sl_pct_out = sig.get("sl_pct", SL_PCT)
            rr_out     = sig.get("rr", FIXED_RR)
            writer.writerow([SYMBOL, entry_ts, entry_price, sig.get("side"), stop_price, take_price, sl_pct_out, rr_out])

print(f"[DONE] saved signals -> {out_path}")
