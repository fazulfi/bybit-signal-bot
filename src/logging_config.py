# src/logging_config.py
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime, timezone

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "bot.log"

DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ISO-like timestamp with ms and Z
class UTCFormatter(logging.Formatter):
    converter = datetime.fromtimestamp
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

FORMAT = "%(asctime)sZ %(levelname)s [%(name)s] %(message)s"

def mask_secret(s: str | None) -> str:
    if not s:
        return ""
    s = str(s)
    if len(s) <= 8:
        return "****"
    return f"{s[:4]}****{s[-4:]}"

def setup_logging():
    root = logging.getLogger()
    if root.handlers:
        # already configured
        return

    root.setLevel(DEFAULT_LEVEL)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(DEFAULT_LEVEL)
    ch.setFormatter(UTCFormatter(FORMAT, datefmt="%Y-%m-%dT%H:%M:%S.%f"))
    root.addHandler(ch)

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=7,
        encoding="utf-8"
    )
    fh.setLevel(DEFAULT_LEVEL)
    fh.setFormatter(UTCFormatter(FORMAT, datefmt="%Y-%m-%dT%H:%M:%S.%f"))
    root.addHandler(fh)

    # Optional: separate warning file
    wh = logging.handlers.TimedRotatingFileHandler(
        filename=str(LOG_DIR / "bot_warn.log"),
        when="midnight",
        backupCount=30,
        encoding="utf-8"
    )
    wh.setLevel(logging.WARNING)
    wh.setFormatter(UTCFormatter(FORMAT, datefmt="%Y-%m-%dT%H:%M:%S.%f"))
    root.addHandler(wh)

    # Reduce verbosity of noisy libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("ccxt").setLevel(logging.INFO)

    root.info("Logging initialized. Level=%s, log_file=%s", DEFAULT_LEVEL, LOG_FILE)

