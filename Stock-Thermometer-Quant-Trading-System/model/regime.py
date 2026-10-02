# model/regime.py — MA60 市场体温判市

import numpy as np
import pandas as pd


class RegimeDetector:
    """市场体温计：MA60 + 波动率"""

    def __init__(self, config):
        self.cfg = config["market"]
        self.regime_cfg = config["regime"]

    def detect(self, index_df):
        """
        判断当前市场状态。

        参数:
            index_df: 沪深300 日线 DataFrame (date, close, ...)

        返回:
            dict: {regime: 1/0/-1, label: "牛/震荡/熊", temperature: 0-100}
        """
        close = index_df["close"].values
        n = len(close)

        if n < self.cfg["ma_period"]:
            return {"regime": 0, "label": "震荡", "temperature": 50}

        ma60 = np.mean(close[-self.cfg["ma_period"]:])
        current = close[-1]

        # 波动率
        ret = np.diff(close) / close[:-1]
        vol_20d = np.std(ret[-20:]) if len(ret) >= 20 else 0
        vol_60d = np.std(ret[-60:]) if len(ret) >= 60 else vol_20d

        # 判市
        above_ma = current > ma60
        vol_rising = vol_20d > vol_60d

        if above_ma and not vol_rising:
            regime = 1
            label = "牛市"
        elif not above_ma and vol_rising:
            regime = -1
            label = "熊市"
        else:
            regime = 0
            label = "震荡"

        # 体温 0-100
        # 基于价格偏离 MA 的程度 + 波动率变化
        ma_dev = (current - ma60) / ma60 * 100  # 偏离百分比
        vol_change = (vol_20d - vol_60d) / max(vol_60d, 0.0001) * 100

        temperature = 50 + ma_dev * 2 - vol_change * 0.5
        temperature = int(np.clip(temperature, 0, 100))

        return {
            "regime": regime,
            "label": label,
            "temperature": temperature,
            "ma60": round(ma60, 2),
            "current": round(current, 2),
            "vol_20d": round(vol_20d, 4),
        }
