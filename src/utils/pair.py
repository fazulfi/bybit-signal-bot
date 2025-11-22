import re

# common quote currencies or stablecoins often used on exchanges
COMMON_QUOTES = [
    "USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "BNB", "SOL", "ADA", "DOT", "XRP"
]

def normalize_pair(raw: str) -> str | None:
    """
    Normalize user-provided pair strings into FORM: BASE/QUOTE, e.g. BTC/USDT.
    Returns normalized string or None if not parseable.
    Examples:
      'btcusdt' -> 'BTC/USDT'
      'BTC-USDT' -> 'BTC/USDT'
      'eth/usd' -> 'ETH/USD'
      'BTC/USDC' -> 'BTC/USDC'
    """
    if not raw or not isinstance(raw, str):
        return None

    s = raw.strip().upper()
    # replace separators with '/'
    s = re.sub(r"[\s\-_:]+", "/", s)

    # if already contains '/', validate and return
    if "/" in s:
        parts = s.split("/")
        if len(parts) != 2:
            return None
        base, quote = parts[0].strip(), parts[1].strip()
        if not base or not quote:
            return None
        return f"{base}/{quote}"

    # try match known quote suffixes (USDT, USDC, BTC, etc.)
    for q in COMMON_QUOTES:
        if s.endswith(q):
            base = s[:-len(q)]
            if base:
                return f"{base}/{q}"

    # fallback: try split in middle if length even-ish (best-effort)
    if len(s) >= 6:
        # try to find a split point where right part is one of common quotes
        for q in COMMON_QUOTES:
            if s.endswith(q):
                base = s[: -len(q)]
                return f"{base}/{q}"
        # naive split: half-half
        mid = len(s) // 2
        base, quote = s[:mid], s[mid:]
        if base and quote:
            return f"{base}/{quote}"

    return None


if __name__ == "__main__":
    # quick interactive tests
    tests = [
        "BTCUSDT", "btc-usdt", "ETH/USDC", "SOLUSDT", "ADAUSD", "XRPBTC", "LTC-USD", "invalidpair"
    ]
    for t in tests:
        print(f"{t} -> {normalize_pair(t)}")

