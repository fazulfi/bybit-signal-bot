# src/utils/historical.py
import time
import pandas as pd

# =================================================================
# Convert timeframe to milliseconds
# =================================================================
def timeframe_to_ms(timeframe: str) -> int:
    unit = timeframe[-1]
    n = int(timeframe[:-1])
    if unit == "m":
        return n * 60 * 1000
    if unit == "h":
        return n * 60 * 60 * 1000
    if unit == "d":
        return n * 24 * 60 * 60 * 1000
    raise ValueError(f"Unsupported timeframe: {timeframe}")

# =================================================================
# FULL HISTORICAL FETCHER
# =================================================================
def fetch_full_ohlcv(
    exchange,
    symbol: str,
    timeframe: str = "15m",
    since: int = None,
    limit_per_call: int = 1000,
):
    """
    Download seluruh data historical OHLCV untuk 1 simbol dari Bybit via CCXT.
    Return: DataFrame OHLCV lengkap (timestamp UTC, open, high, low, close, volume)
    """

    ms_per_bar = timeframe_to_ms(timeframe)
    all_rows = []

    # Default start date jika tidak diberi
    if since is None:
        # mulai dari 2020, aman untuk semua coin baru-lama
        since = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)

    now_ms = exchange.milliseconds()
    fetch_since = since

    print(f"[START] Fetching {symbol} | TF={timeframe} | Start={pd.to_datetime(fetch_since, unit='ms')}")

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=fetch_since,
                limit=limit_per_call
            )
        except Exception as e:
            print("Error fetching:", e)
            time.sleep(2)
            continue

        if not ohlcv:
            print("No more data returned.")
            break

        all_rows.extend(ohlcv)

        oldest = ohlcv[0][0]
        newest = ohlcv[-1][0]

        print(
            f"Fetched {len(ohlcv)} rows | "
            f"From {pd.to_datetime(oldest, unit='ms')} "
            f"to {pd.to_datetime(newest, unit='ms')}"
        )

        # maju ke next page
        fetch_since = newest + 1

        # stop jika sudah mendekati sekarang
        if fetch_since >= now_ms:
            print("Reached current time. Stop.")
            break

        # rate limit
        time.sleep(0.35)  # aman untuk bybit (rateLimit auto)

    # convert → DataFrame
    df = pd.DataFrame(
        all_rows,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )

    # to datetime UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    # dedup + sort
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)

    print(f"[DONE] Total bars fetched: {len(df)}")
    return df
