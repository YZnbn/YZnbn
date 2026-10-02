# data/cache.py — SQLite 缓存

import sqlite3
import os
import pandas as pd


class CacheDB:
    """SQLite 数据缓存"""

    def __init__(self, db_path="cache/stock_data.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_k (
                code TEXT, date TEXT, open REAL, high REAL, low REAL,
                close REAL, volume REAL, amount REAL, turnover REAL,
                PRIMARY KEY (code, date)
            );
            CREATE TABLE IF NOT EXISTS factors (
                code TEXT, date TEXT,
                mom_20d REAL, mom_60d REAL, mom_120d REAL,
                pe_inv REAL, pb_inv REAL,
                roe REAL, gross_margin REAL,
                vol_20d REAL, vol_60d REAL,
                turnover_20d REAL, volume_ratio REAL,
                rsi_14 REAL, pos_52w REAL,
                PRIMARY KEY (code, date)
            );
            CREATE TABLE IF NOT EXISTS causal_factors (
                month TEXT, factor_name TEXT, mci_val REAL,
                p_val REAL, is_significant INTEGER,
                PRIMARY KEY (month, factor_name)
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY, value TEXT
            );
        """)
        self.conn.commit()

    # ---- 日线 ----
    def save_daily(self, df):
        df.to_sql("daily_k", self.conn, if_exists="append", index=False)

    def load_daily(self, code=None, start=None, end=None):
        sql = "SELECT * FROM daily_k WHERE 1=1"
        params = []
        if code:
            sql += " AND code = ?"
            params.append(code)
        if start:
            sql += " AND date >= ?"
            params.append(start)
        if end:
            sql += " AND date <= ?"
            params.append(end)
        return pd.read_sql(sql, self.conn, params=params)

    def get_all_codes_with_data(self, min_days=60):
        sql = "SELECT code FROM daily_k GROUP BY code HAVING COUNT(*) >= ?"
        rows = self.conn.execute(sql, (min_days,)).fetchall()
        return [r[0] for r in rows]

    # ---- 因子 ----
    def save_factors(self, df):
        df.to_sql("factors", self.conn, if_exists="replace", index=False)

    def load_factors(self, date=None):
        if date:
            return pd.read_sql(
                "SELECT * FROM factors WHERE date = ?", self.conn, params=(date,))
        return pd.read_sql("SELECT * FROM factors", self.conn)

    # ---- PCMCI 结果 ----
    def save_causal(self, month, factor_results):
        rows = []
        for name, mci, pv, sig in factor_results:
            rows.append((month, name, mci, pv, int(sig)))
        self.conn.executemany(
            "INSERT OR REPLACE INTO causal_factors VALUES (?,?,?,?,?)", rows)
        self.conn.commit()

    def load_causal(self, month=None):
        if month:
            return pd.read_sql(
                "SELECT * FROM causal_factors WHERE month = ? AND is_significant=1",
                self.conn, params=(month,))
        return pd.read_sql(
            "SELECT * FROM causal_factors WHERE is_significant=1", self.conn)

    # ---- 元数据 ----
    def set_meta(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))
        self.conn.commit()

    def get_meta(self, key, default=None):
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def close(self):
        self.conn.close()
