# data/preloader.py — 全市场日线预加载到 SQLite（一次性）
"""
首次运行：下载全部 A 股日线 → cache.db
之后每次：check_and_update() 增量拉最新几天
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "cache", "stock_data.db")


def _prefix(code: str) -> str:
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    elif code.startswith(("0", "3")):
        return f"sz{code}"
    return f"bj{code}"


def get_all_codes():
    """获取全 A 股代码列表（排除 ST/北交所）"""
    df = ak.stock_zh_a_spot()
    df = df[~df["名称"].str.contains("ST|\\*ST", na=False)]
    # 排除北交所 (bj) 和仅有数字的不匹配格式
    df = df[~df["代码"].str.startswith("bj")]
    return df["代码"].tolist()


def download_one(code, start="20240101"):
    """下载单只股票日线 → DataFrame"""
    try:
        df = ak.stock_zh_a_daily(
            symbol=_prefix(code),
            start_date=start,
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq",
        )
        if df is None or len(df) == 0:
            return None
        df = df.rename(columns={
            "date": "date", "open": "open", "high": "high",
            "low": "low", "close": "close", "volume": "volume",
            "amount": "amount", "turnover": "turnover",
        })
        df["date"] = pd.to_datetime(df["date"])
        df["code"] = code
        return df[["code", "date", "open", "high", "low",
                    "close", "volume", "amount", "turnover"]]
    except Exception as e:
        print(f"  [{code}] 失败: {e}")
        return None


def preload_all(workers=20, start="20240101"):
    """全市场下载 → SQLite，可断点续传"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    # 确保表存在
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_k (
            code TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume REAL, amount REAL, turnover REAL,
            PRIMARY KEY (code, date)
        );
    """)
    conn.commit()

    all_codes = get_all_codes()
    print(f"全 A 股: {len(all_codes)} 只（不含 ST/北交所）")

    # 断点续传：跳过已有数据的
    existing = set()
    rows = conn.execute(
        "SELECT DISTINCT code FROM daily_k WHERE date >= ?", (start,)
    ).fetchall()
    existing = {r[0] for r in rows}
    todo = [c for c in all_codes if c not in existing]
    print(f"已缓存: {len(existing)} 只 | 待下载: {len(todo)} 只")

    if not todo:
        print("全部已缓存 ✓")
        conn.close()
        return

    done = 0
    total = len(todo)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, code, start): code for code in todo}
        for fut in as_completed(futures):
            code = futures[fut]
            done += 1
            try:
                df = fut.result()
                if df is not None and len(df) > 0:
                    df.to_sql("daily_k", conn, if_exists="append", index=False)
                    conn.commit()
            except Exception as e:
                print(f"  [{code}] 写入失败: {e}")

            elapsed = time.time() - start_time
            eta = (elapsed / done) * (total - done) if done > 0 else 0
            print(f"\r进度: {done}/{total} ({done*100//total}%) | "
                  f"耗时 {elapsed/60:.1f}min | 预计剩余 {eta/60:.1f}min", end="")

    print(f"\n完成！总计 {done} 只，耗时 {elapsed/60:.1f} 分钟")
    conn.close()


def update_today():
    """增量更新：拉取今日数据（收盘后跑）"""
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    existing = conn.execute(
        "SELECT COUNT(*) FROM daily_k WHERE date = ?", (today,)
    ).fetchone()[0]
    if existing > 0:
        print(f"今日 ({today}) 已更新，共 {existing} 条")
        conn.close()
        return

    codes = [r[0] for r in conn.execute(
        "SELECT DISTINCT code FROM daily_k"
    ).fetchall()]
    print(f"增量更新 {today}: {len(codes)} 只")

    done = 0
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(download_one, code, today.replace("-", "")): code
                   for code in codes}
        for fut in as_completed(futures):
            code = futures[fut]
            done += 1
            try:
                df = fut.result()
                if df is not None and len(df) > 0:
                    df.to_sql("daily_k", conn, if_exists="append", index=False)
                    conn.commit()
            except Exception:
                pass
            if done % 200 == 0:
                print(f"\r  更新中: {done}/{len(codes)}", end="")
    print(f"\r  更新完成: {done}/{len(codes)}")
    conn.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="仅增量更新今日")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--start", default="20240101")
    args = ap.parse_args()

    if args.update:
        update_today()
    else:
        preload_all(workers=args.workers, start=args.start)
