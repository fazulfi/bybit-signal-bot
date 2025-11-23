import sqlite3
from datetime import datetime

DB_PATH = "signals.db"


class Storage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            price REAL NOT NULL,
            timestamp TEXT NOT NULL
        );
        """)

        conn.commit()
        conn.close()

    def save_signal(self, symbol: str, side: str, price: float):
        conn = self._connect()
        cur = conn.cursor()

        # gunakan timestamp UTC timezone-aware
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()  # ex: 2025-01-03T02:30:00+00:00

        cur.execute("""
            INSERT INTO signals (symbol, side, price, timestamp)
            VALUES (?, ?, ?, ?)
        """, (symbol, side, price, ts))

        conn.commit()
        conn.close()

    def get_last_signal(self, symbol: str):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT symbol, side, price, timestamp
            FROM signals
            WHERE symbol = ?
            ORDER BY id DESC LIMIT 1
        """, (symbol,))

        row = cur.fetchone()
        conn.close()

        if row:
            return {
                "symbol": row[0],
                "side": row[1],
                "price": row[2],
                "timestamp": row[3]
            }
        return None

