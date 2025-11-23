# src/config.py
import os
from dotenv import load_dotenv

# Load .env dari project root
load_dotenv()

# API keys
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")

# Settings lainnya
TIMEFRAME = os.getenv("TIMEFRAME", "15m")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
TOP_N_PAIRS = int(os.getenv("TOP_N_PAIRS", "50"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///signals.db")
EMA_FAST = int(os.getenv("EMA_FAST", "9"))
EMA_SLOW = int(os.getenv("EMA_SLOW", "21"))
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
DEBOUNCE_MINUTES = int(os.getenv("DEBOUNCE_MINUTES", "15"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
LANG = os.getenv("LANG", "id")

# ================================
# Default Strategy Parameters
# ================================

# Default Stop-Loss (fractional) -> 0.01 = 1%
SL = float(os.getenv("SL", "0.01"))

# Default Risk/Reward Ratio (e.g. 2.0 = TP 2× SL)
RR = float(os.getenv("RR", "2.0"))

# Default Take-Profit (if you prefer explicit TP)
# If not set, engine will compute TP = SL * RR
TP = SL * RR
