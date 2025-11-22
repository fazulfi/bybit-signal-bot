from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env file from project root
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    load_dotenv(env_path)

def _int(key, default=None):
    v = os.getenv(key)
    return int(v) if v is not None and v != "" else default

def _float(key, default=None):
    v = os.getenv(key)
    return float(v) if v is not None and v != "" else default

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Bybit API keys
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")

# Bot settings
TIMEFRAME = os.getenv("TIMEFRAME", "15m")
POLL_INTERVAL_SECONDS = _int("POLL_INTERVAL_SECONDS", 60)
TOP_N_PAIRS = _int("TOP_N_PAIRS", 50)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///signals.db")

# Indicators
EMA_FAST = _int("EMA_FAST", 9)
EMA_SLOW = _int("EMA_SLOW", 21)
RSI_PERIOD = _int("RSI_PERIOD", 14)
DEBOUNCE_MINUTES = _int("DEBOUNCE_MINUTES", 15)

# Localization
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
LANG = os.getenv("LANG", "id")

# Debugging
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

