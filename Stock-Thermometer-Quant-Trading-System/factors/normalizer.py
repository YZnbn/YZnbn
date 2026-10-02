# factors/normalizer.py — 截面 z-score 标准化

import numpy as np
import pandas as pd


class Normalizer:
    """因子截面标准化：z-score + 截断±3σ"""

    def __init__(self, clip=3.0):
        self.clip = clip

    def normalize(self, factor_df, factor_columns):
        """
        factor_df: DataFrame, 每行一只股票, columns 含 factor_columns
        返回：在 factor_columns 上做截面 z-score
        """
        df = factor_df.copy()
        for col in factor_columns:
            if col not in df.columns:
                continue
            vals = df[col].values.astype(float)
            vals = np.where(np.isinf(vals), np.nan, vals)

            mu = np.nanmean(vals)
            sigma = np.nanstd(vals)
            if sigma == 0 or np.isnan(sigma):
                df[col + "_z"] = 0
            else:
                z = (vals - mu) / sigma
                z = np.clip(z, -self.clip, self.clip)
                df[col + "_z"] = z
        return df
