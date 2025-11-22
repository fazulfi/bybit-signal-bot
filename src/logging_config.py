import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime, timezone

# -------- LOG DIRECTORY --------
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "bot.log"

# Default log level based on .env
DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# -------- FORMATTER WITH UTC TIMESTAMP --------
class UTCFormatter(logging.Formatter):
    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()


FORMAT = "%(asctime)sZ %(levelname)s [%(name)s] %(message)s"


# -------- MASKING SECRETS --------
def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    s = str(value)
    if len(s) <= 8:
        return "****"
    return f"{s[:4]}****{s[-4:]}"


# -------- SETUP LOGGING --------
def setup_logging():
    root = logging.getLogger()

    # Prevent double initialization
    if root.handlers:
        return

    root.setLevel(DEFAULT_LEVEL)

    # ----- Console Handler -----
    ch = logging.StreamHandler()
    ch.setLevel(DEFAULT_LEVEL)
    ch.setFormatter(UTCFormatter(FORMAT, datefmt="%Y-%m-%dT%H:%M:%S.%f"))
    root.addHandler(ch)

    # ----- Rotating File Handler -----
    fh = logging.handlers.RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=7,
        encoding="utf-8"
    )
    fh.setLevel(DEFAULT_LEVEL)
    fh.setFormatter(UTCFormatter(FORMAT, datefmt="%Y-%m-%dT%H:%M:%S.%f"))
    root.addHandler(fh)

    # ----- Daily WARNING Log -----
    wh = logging.handlers.TimedRotatingFileHandler(
        filename=str(LOG_DIR / "bot_warn.log"),
        when="midnight",
        backupCount=30,
        encoding="utf-8"
    )
    wh.setLevel(logging.WARNING)
    wh.setFormatter(UTCFormatter(FORMAT, datefmt="%Y-%m-%dT%H:%M:%S.%f"))
    root.addHandler(wh)

    # Reduce spam from external libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("ccxt").setLevel(logging.INFO)

    root.info("Logging initialized. Level=%s, file=%s", DEFAULT_LEVEL, LOG_FILE)
