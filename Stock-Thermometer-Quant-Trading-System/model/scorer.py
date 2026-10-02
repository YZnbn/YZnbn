# model/scorer.py — 综合打分

import numpy as np
import pandas as pd


class Scorer:
    """PCMCI 有效因子 × 体温系数 → 综合得分"""

    def __init__(self, config):
        self.cfg = config
        self.factor_cats = config["factor_categories"]

    def score(self, factor_df, causal_factors, regime):
        """
        参数:
            factor_df: 全市场因子截面 (code, 12因子_z)
            causal_factors: PCMCI 输出的有效因子 [(name, mci), ...]
            regime: 判市结果 {"regime": 1/0/-1}

        返回:
            DataFrame: code + score + direction
        """
        if len(causal_factors) == 0:
            return pd.DataFrame(columns=["code", "score", "direction"])

        df = factor_df.copy()
        df["score"] = 0.0

        # 体温系数
        regime_type = regime["regime"]
        if regime_type == 1:  # 牛
            mom_boost = self.cfg["regime"]["bull"]["momentum_boost"]
            val_boost = self.cfg["regime"]["bull"]["value_penalty"]
        elif regime_type == -1:  # 熊
            mom_boost = self.cfg["regime"]["bear"]["momentum_boost"]
            val_boost = self.cfg["regime"]["bear"]["value_penalty"]
        else:  # 震荡
            mom_boost = 1.0
            val_boost = 1.0

        short_factors = self.factor_cats["short_term"]
        long_factors = self.factor_cats["long_term"]

        # MCI 加权求和
        for name, mci in causal_factors:
            if np.isnan(mci) or mci == 0:
                continue
            z_col = name + "_z"
            if z_col not in df.columns:
                continue

            # 体温调整
            if name in short_factors:
                boost = mom_boost
            elif name in long_factors:
                boost = val_boost
            else:
                boost = 1.0

            df["score"] += df[z_col].fillna(0) * mci * boost

        # 短线/长线分类
        df = self._classify(df, causal_factors)

        # 预测回报率：WLS 截面回归模型
        df["pred_ret"] = 0.0
        hold_days = getattr(self, "_hold_days", 10)
        try:
            from model.predictor import ReturnPredictor
            if not hasattr(self, "_predictor"):
                self._predictor = ReturnPredictor()
            preds = self._predictor.predict(df, hold_days=hold_days)
            df["pred_ret"] = preds.values if hasattr(preds, "values") else preds
            df["pred_ret"] = df["pred_ret"].clip(-10, 10).round(1)
        except Exception:
            if "mom_20d" in df.columns:
                df["pred_ret"] = df["mom_20d"].fillna(0).clip(-10, 10).round(1)

        # 持仓天数：IC 衰减分析最优值
        df["hold_days"] = hold_days

        # 排序
        df = df.sort_values("score", ascending=False)
        return df

    def _classify(self, df, causal_factors):
        """根据有效因子的类别分布确定短线/长线"""
        short_names = self.factor_cats["short_term"]
        long_names = self.factor_cats["long_term"]

        short_mci = sum(mci for n, mci in causal_factors if n in short_names)
        long_mci = sum(mci for n, mci in causal_factors if n in long_names)
        total = short_mci + long_mci

        if total == 0:
            df["direction"] = "观望"
            return df

        short_ratio = short_mci / total

        if short_ratio > 0.6:
            df["direction"] = "短线"
        elif short_ratio < 0.4:
            df["direction"] = "长线"
        else:
            df["direction"] = "混合"

        return df
