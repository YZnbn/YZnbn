# data/cleaner.py — 数据清洗与过滤

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class Cleaner:
    """数据清洗器：排除 ST/新股/停牌/异常"""

    def __init__(self, config):
        self.cfg = config

    def filter_stocks(self, spot_df):
        """过滤不可交易股票"""
        df = spot_df.copy()

        # 排除 ST
        if self.cfg["data"].get("exclude_st", True):
            df = df[~df["name"].str.contains("ST|\\*ST", na=False)]

        # 排除低价股
        min_price = self.cfg["data"].get("min_price", 1.0)
        df = df[df["price"] >= min_price]

        # 排除 PE/PB 异常（仅当数据有有效值时过滤）
        if "pe" in df.columns and df["pe"].notna().sum() > 100:
            df = df[df["pe"] > 0]
        if "pb" in df.columns and df["pb"].notna().sum() > 100:
            df = df[df["pb"] > 0]

        # 排除价格为 NaN
        df = df.dropna(subset=["price"])

        return df

    def filter_by_history(self, daily_data, min_days=120):
        """过滤历史数据不足的股票"""
        counts = daily_data.groupby("code").size()
        valid_codes = counts[counts >= min_days].index
        return daily_data[daily_data["code"].isin(valid_codes)]
