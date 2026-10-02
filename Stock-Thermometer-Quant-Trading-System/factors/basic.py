# factors/basic.py — 12 候选因子计算（groupby + numpy）

import pandas as pd
import numpy as np


class FactorComputer:
    """12 个候选因子计算器 — groupby 迭代 + numpy 内核"""

    def __init__(self, config):
        self.cfg = config["factors"]
        self.skip = self.cfg["momentum"]["skip"]

    def compute_all(self, daily_df, spot_df):
        """计算所有候选因子（groupby 一次分组，numpy 逐只算，秒级）"""
        results = []

        for code, group in daily_df.groupby("code"):
            stock = group.sort_values("date")
            if len(stock) < 120:
                continue
            factors = self._compute_stock(
                stock["close"].values,
                stock["volume"].values,
                stock["turnover"].values,
            )
            if factors is None:
                continue
            factors["code"] = code
            results.append(factors)

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # === 财务因子从 spot 拼接 ===
        if spot_df is not None and "code" in spot_df.columns:
            spot_indexed = spot_df.set_index("code")
            pe_vals, pb_vals = [], []
            for c in df["code"]:
                pe = float(spot_indexed.loc[c, "pe"] if c in spot_indexed.index else 0) if c in spot_indexed.index else 0
                pb = float(spot_indexed.loc[c, "pb"] if c in spot_indexed.index else 0) if c in spot_indexed.index else 0
                pe_vals.append(1.0 / pe if pe > 0 else 0)
                pb_vals.append(1.0 / pb if pb > 0 else 0)
            df["pe_inv"] = pe_vals
            df["pb_inv"] = pb_vals
        else:
            df["pe_inv"] = 0
            df["pb_inv"] = 0

        return df

    def _compute_stock(self, close, volume, turnover):
        """纯 numpy 算单只股票的技术因子"""
        n = len(close)
        if n < 120:
            return None

        ret = np.diff(close) / close[:-1]

        # 动量
        mom_20d = close[-1] / close[-21] - 1 if n >= 21 else 0
        mom_60d = close[-1 - self.skip] / close[-61] - 1 if n >= 61 + self.skip else 0
        mom_120d = close[-1 - self.skip] / close[-121] - 1 if n >= 121 + self.skip else 0

        # 波动率
        vol_20d = float(np.std(ret[-20:])) if len(ret) >= 20 else 0
        vol_60d = float(np.std(ret[-60:])) if len(ret) >= 60 else 0

        # 流动性
        turnover_20d = float(np.mean(turnover[-20:])) if len(turnover) >= 20 else 0
        vol_short = float(np.mean(volume[-5:])) if len(volume) >= 5 else 0
        vol_long = float(np.mean(volume[-20:])) if len(volume) >= 20 else 0
        volume_ratio = vol_short / vol_long if vol_long > 0 else 0

        # RSI-14
        gain = np.where(ret > 0, ret, 0)
        loss = np.where(ret < 0, -ret, 0)
        avg_g = float(np.mean(gain[-14:])) if len(gain) >= 14 else 0
        avg_l = float(np.mean(loss[-14:])) if len(loss) >= 14 else 0
        if avg_l > 0:
            rs = avg_g / avg_l
            rsi_14 = 100 - 100 / (1 + rs)
        else:
            rsi_14 = 100 if avg_g > 0 else 50

        # 52周位置
        if n >= 252:
            high_52w = float(np.max(close[-252:]))
            low_52w = float(np.min(close[-252:]))
        else:
            high_52w = float(np.max(close))
            low_52w = float(np.min(close))
        pos_52w = (close[-1] - low_52w) / (high_52w - low_52w) if high_52w > low_52w else 0.5

        return {
            "mom_20d": mom_20d,
            "mom_60d": mom_60d,
            "mom_120d": mom_120d,
            "vol_20d": vol_20d,
            "vol_60d": vol_60d,
            "turnover_20d": turnover_20d,
            "volume_ratio": volume_ratio,
            "rsi_14": rsi_14,
            "pos_52w": pos_52w,
        }
