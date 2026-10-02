# factors/causal.py — PCMCI 因果因子筛选（★ 核心）

import numpy as np
import pandas as pd
from datetime import datetime


class CausalSelector:
    """PCMCI 因果因子选择器（优先 PCMCI，兜底 Rank IC）"""

    def __init__(self, config):
        self.pcmci_cfg = config["pcmci"]
        self.factor_names = [
            "mom_20d", "mom_60d", "mom_120d",
            "pe_inv", "pb_inv",
            "roe", "gross_margin",
            "vol_20d", "vol_60d",
            "turnover_20d", "volume_ratio",
            "rsi_14"
        ]
        self.target_name = "fwd_ret"

    def select(self, daily_df, factor_df, spot_df):
        """
        PCMCI 因果筛选。优先 tigramite PCMCI，失败则用 Rank IC。
        """
        # 1. 先跑 Rank IC（快，始终可用）
        ic_factors = self._fallback_correlation(factor_df, daily_df)

        # 2. 尝试 PCMCI
        try:
            from tigramite import data_processing as pp
            from tigramite.pcmci import PCMCI
            from tigramite.independence_tests.parcorr import ParCorr

            lookback = self.pcmci_cfg["lookback_days"]
            sample_codes = self._sample_stocks(daily_df, factor_df, n=20)

            all_mci = {name: [] for name in self.factor_names}

            for code in sample_codes:
                stock = daily_df[daily_df["code"] == code].sort_values("date")
                if len(stock) < lookback + 20:
                    continue

                stock = stock.tail(lookback + 20)
                close = stock["close"].values

                features = self._build_features(stock, factor_df, code)
                target = self._build_target(close)

                if features is None or target is None:
                    continue
                if features.shape[0] != len(target):
                    continue

                data = np.column_stack([features, target])
                var_names = self.factor_names + [self.target_name]

                dataframe = pp.DataFrame(data, var_names=var_names)
                pcmci = PCMCI(dataframe=dataframe, cond_ind_test=ParCorr())
                results = pcmci.run_pcmci(
                    tau_max=self.pcmci_cfg["tau_max"],
                    pc_alpha=self.pcmci_cfg["pc_alpha"],
                )

                target_idx = len(var_names) - 1
                val_matrix = results["val_matrix"]

                for i, name in enumerate(self.factor_names):
                    mci = np.max(np.abs(val_matrix[i, target_idx, :]))
                    if not np.isnan(mci):
                        all_mci[name].append(mci)

            # 汇总
            summary = {}
            for name in self.factor_names:
                vals = all_mci[name]
                summary[name] = np.mean(vals) if vals else 0.0

            sorted_factors = sorted(summary.items(), key=lambda x: x[1], reverse=True)
            min_factors = self.pcmci_cfg.get("min_causal_factors", 3)
            threshold = np.percentile([v for _, v in sorted_factors], 50)

            causal_factors = []
            for name, mci in sorted_factors:
                if mci > threshold or len(causal_factors) < min_factors:
                    causal_factors.append((name, round(mci, 4)))

            if len(causal_factors) >= 3:
                print(f"[CausalSelector] PCMCI → {len(causal_factors)} 个因果因子")
                return causal_factors

        except ImportError:
            print("[CausalSelector] tigramite 未安装，回退到相关性筛选")
        except Exception as e:
            print(f"[CausalSelector] PCMCI 出错: {e}，回退到相关性筛选")

        print(f"[CausalSelector] Rank IC → {len(ic_factors)} 个因子")
        return ic_factors

    def _sample_stocks(self, daily_df, factor_df, n=500):
        if factor_df is None or len(factor_df) == 0:
            return []
        if "volume_ratio" in factor_df.columns:
            sample = factor_df.nlargest(n, "volume_ratio")
        else:
            sample = factor_df.sample(min(n, len(factor_df)))
        return sample["code"].tolist() if "code" in sample.columns else []

    def _build_features(self, stock, factor_df, code):
        close = stock["close"].values
        volume = stock["volume"].values
        n = len(close)
        if n < 60:
            return None

        ret = np.diff(close) / close[:-1]
        features = []
        for t in range(20, n - 20):
            win = ret[max(0, t - 60):t]
            if len(win) < 10:
                continue
            mom_20 = close[t] / close[max(0, t - 20)] - 1 if t >= 20 else 0
            mom_60 = close[t] / close[max(0, t - 60)] - 1 if t >= 60 else 0
            vol_20 = np.std(win[-20:]) if len(win) >= 20 else 0
            vol_60 = np.std(win[-60:]) if len(win) >= 60 else 0
            rsi = self._calc_rsi(win[-14:])
            vol_ratio = (np.mean(volume[max(0, t - 5):t]) /
                         max(np.mean(volume[max(0, t - 20):t]), 1))
            features.append([
                mom_20, mom_60, mom_20,
                0, 0, 0, 0, vol_20, vol_60, 0, vol_ratio, rsi,
            ])
        if len(features) < 30:
            return None
        return np.array(features)

    def _build_target(self, close, forward=20):
        n = len(close)
        targets = [close[t + forward] / close[t] - 1 for t in range(20, n - forward)]
        return np.array(targets) if len(targets) >= 30 else None

    def _calc_rsi(self, rets, period=14):
        if len(rets) < period:
            return 50
        gains = np.mean([r for r in rets if r > 0]) if any(r > 0 for r in rets) else 0
        losses = abs(np.mean([r for r in rets if r < 0])) if any(r < 0 for r in rets) else 0.001
        rs = gains / losses if losses > 0 else 100
        return 100 - 100 / (1 + rs)

    def _fallback_correlation(self, factor_df, daily_df):
        """Rank IC 筛选（向量化：pivot 一次算完所有前向收益）"""
        if factor_df is None or len(factor_df) == 0:
            return [(n, 0.0) for n in self.factor_names[:5]]

        # 一次性 pivot：code × date → close，取每只的最后两天
        piv = daily_df.pivot_table(
            index="date", columns="code", values="close", aggfunc="last")
        piv = piv.sort_index()
        if len(piv) < 22:
            return [(n, 0.0) for n in self.factor_names[:5]]

        # 前向 20 日收益：close[-1] / close[-21] - 1
        fwd = (piv.iloc[-1] / piv.iloc[-22] - 1)
        fwd = fwd.dropna()

        from scipy.stats import spearmanr
        scores = {}
        for name in self.factor_names:
            if name not in factor_df.columns:
                continue
            factor = factor_df.set_index("code")[name].dropna()
            common = factor.index.intersection(fwd.index)
            if len(common) < 5:
                scores[name] = 0.0
                continue
            try:
                ic, _ = spearmanr(factor[common], fwd[common])
                scores[name] = abs(ic) if not np.isnan(ic) else 0.0
            except Exception:
                scores[name] = 0.0

        sorted_factors = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(n, round(v, 4)) for n, v in sorted_factors[:6]]
