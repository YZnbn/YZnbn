# data/fetcher.py — akshare 数据下载（非东方财富源）
# Eastmoney (_em) 函数全部不可用，改用 Sina/Tencent/THS 源

import akshare as ak
import pandas as pd
import requests
from datetime import datetime


def _prefix(code: str) -> str:
    """给股票代码加交易所前缀: 6开头→sh, 0/3→sz, 8/4→bj。已有前缀则直接返回。"""
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith("6"):
        return f"sh{code}"
    elif code.startswith(("0", "3")):
        return f"sz{code}"
    else:
        return f"bj{code}"


class Fetcher:
    """A 股数据下载器"""

    def __init__(self, config):
        self.cfg = config

    def get_all_stocks(self):
        """获取全 A 股列表"""
        df = ak.stock_zh_a_spot()
        df = df[["代码", "名称"]].copy()
        df.columns = ["code", "name"]
        return df

    def get_index_daily(self, code="000300", start="20100101"):
        """获取指数日线（默认沪深300），首次拉全量缓存，后续秒读"""
        import pickle, os, time
        cache_dir = self.cfg.get("data", {}).get("cache_dir", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"index_{code}.pkl")

        if os.path.exists(cache_path):
            age = time.time() - os.path.getmtime(cache_path)
            if age < 86400:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)

        df = ak.stock_zh_index_daily(symbol=f"sh{code}")
        df = df.rename(columns={
            "date": "date", "open": "open", "high": "high",
            "low": "low", "close": "close", "volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        with open(cache_path, "wb") as f:
            pickle.dump(df, f)
        return df

    def get_stock_daily(self, code, start="20200101", end=None):
        """获取单只股票日线（Sina源）"""
        if end is None:
            end = datetime.now().strftime("%Y%m%d")
        try:
            df = ak.stock_zh_a_daily(
                symbol=_prefix(code),
                start_date=start,
                end_date=end,
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
            print(f"[Fetcher] {code} 下载失败: {e}")
            return None

    def get_financials(self, code):
        """获取单只股票最新财务数据"""
        try:
            df = ak.stock_financial_abstract(symbol=code)
            if df is None or len(df) == 0:
                return {}
            date_cols = [c for c in df.columns if isinstance(c, str) and c.isdigit() and len(c) == 8]
            if not date_cols:
                return {}
            latest = date_cols[0]
            df = df.set_index("指标")

            def _get(key):
                try:
                    val = df.loc[key, latest]
                    return float(val.iloc[0]) if hasattr(val, 'iloc') else float(val)
                except (KeyError, ValueError, TypeError):
                    return 0.0

            return {
                "roe": _get("净资产收益率(ROE)"),
                "gross_margin": _get("毛利率"),
                "pe": 0.0,
                "pb": 0.0,
            }
        except Exception:
            return {}

    def get_spot(self):
        """获取全 A 股实时行情（Sina源）+ PE/PB（腾讯源补充）"""
        df = ak.stock_zh_a_spot()
        df = df.rename(columns={
            "代码": "code", "名称": "name", "最新价": "price",
            "涨跌幅": "pct_chg", "换手率": "turnover",
            "成交量": "volume", "成交额": "amount",
        })
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["pe"] = float("nan")
        df["pb"] = float("nan")

        # 用腾讯接口补充 PE/PB（批量，每批 50 只）
        codes = df["code"].tolist()
        batch_size = 50
        pe_map, pb_map = {}, {}

        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            prefixed = [_prefix(c) for c in batch]
            try:
                url = "http://qt.gtimg.cn/q=" + ",".join(prefixed)
                resp = requests.get(url, timeout=10)
                resp.encoding = "gbk"
                for line in resp.text.strip().split("\n"):
                    if not line.strip() or "=" not in line:
                        continue
                    content = line.split('"')[1] if '"' in line else ""
                    fields = content.split("~")
                    if len(fields) < 50:
                        continue
                    raw_code = fields[2] if len(fields) > 2 else ""
                    try:
                        pe = float(fields[39]) if fields[39].replace(".", "").replace("-", "").isdigit() else float("nan")
                        pb = float(fields[46]) if fields[46].replace(".", "").replace("-", "").isdigit() else float("nan")
                    except (ValueError, IndexError):
                        pe, pb = float("nan"), float("nan")

                    if pe > 0 and not pd.isna(pe):
                        pe_map[raw_code] = pe
                    if pb > 0 and not pd.isna(pb):
                        pb_map[raw_code] = pb

            except Exception as e:
                print(f"[Fetcher] PE/PB 批量 {i} 失败: {e}")

        # 回填 — df["code"] 带前缀(sh/sz/bj)，腾讯无前缀，需去前缀映射
        def _strip_prefix(c):
            if isinstance(c, str) and len(c) > 2 and c[:2] in ("sh", "sz", "bj"):
                return c[2:]
            return c

        df["pe"] = df["code"].apply(_strip_prefix).map(pe_map)
        df["pb"] = df["code"].apply(_strip_prefix).map(pb_map)

        ok = (df["pe"] > 0).sum()
        print(f"[Fetcher] PE/PB 覆盖: {ok}/{len(df)}")

        return df
