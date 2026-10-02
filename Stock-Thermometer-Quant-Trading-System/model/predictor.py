# model/predictor.py — 收益预测 & 最优持仓周期（向量化版）
# 文献: Gu-Kelly-Xiu (2020), Grinold (1989), Fama-MacBeth (1973)

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from scipy.optimize import curve_fit


class ReturnPredictor:
    """WLS 截面回归：因子 → 预期收益（向量化）"""

    def __init__(self):
        self.weights = {}
        self.r2 = 0.0
        self.last_update = None

    def fit(self, factor_df, daily_df, causal_factors, hold_days=10):
        if daily_df is None or factor_df is None:
            return
        import datetime
        self.last_update = datetime.datetime.now()

        # 1. 一次性 pivot：code × date → close
        piv = daily_df.pivot(index="date", columns="code", values="close")
        piv = piv.sort_index()
        if len(piv) < hold_days + 5:
            return

        # 2. 前向收益 = close[T] / close[T-hold_days] - 1，一次性算
        fwd = (piv.iloc[-1] / piv.iloc[-(hold_days + 1)] - 1) * 100
        fwd = fwd.dropna()

        # 3. 对齐因子截面
        factor_names = [n for n, _ in causal_factors if n + "_z" in factor_df.columns]
        if len(factor_names) < 2:
            return

        codes_common = set(fwd.index) & set(factor_df["code"].values)
        X_rows, y_vals, w_list = [], [], []
        for code in codes_common:
            row = factor_df[factor_df["code"] == code]
            vals = [row[n + "_z"].values[0] for n in factor_names]
            if any(np.isnan(v) for v in vals):
                continue
            X_rows.append(vals)
            y_vals.append(fwd[code])
            w_mci = sum(abs(mci) for n, mci in causal_factors if n in factor_names)
            w_list.append(max(w_mci, 1.0))

        if len(X_rows) < 10:
            return

        X, y, W_vec = np.array(X_rows), np.array(y_vals), np.array(w_list)

        # WLS: w = (X^T W X)^{-1} X^T W y
        try:
            W_sqrt = np.sqrt(W_vec)
            X_w = X * W_sqrt[:, None]
            y_w = y * W_sqrt
            XtX = X_w.T @ X_w
            XtX += np.eye(len(factor_names)) * 1e-4
            w_hat = np.linalg.solve(XtX, X_w.T @ y_w)
        except np.linalg.LinAlgError:
            return

        self.weights = {name: round(float(w_hat[i]), 4) for i, name in enumerate(factor_names)}
        y_pred = X @ w_hat
        ss_tot = np.sum((y - y.mean()) ** 2)
        self.r2 = round(float(1 - np.sum((y - y_pred) ** 2) / ss_tot), 4) if ss_tot > 0 else 0.0

    def predict(self, factor_df, hold_days=10):
        if not self.weights:
            if "mom_20d" in factor_df.columns:
                return factor_df["mom_20d"].fillna(0).clip(-10, 10)
            return pd.Series(0.0, index=factor_df.index)

        pred = pd.Series(0.0, index=factor_df.index)
        for name, w in self.weights.items():
            z_col = name + "_z"
            if z_col in factor_df.columns:
                pred += factor_df[z_col].fillna(0) * w

        if pred.std() > 0:
            daily_vol = 0.35 / np.sqrt(252)
            target_std = daily_vol * np.sqrt(hold_days) * 100
            pred = pred * (target_std / pred.std())

        return pred.clip(-10, 10)


class ICDecayAnalyzer:
    """IC 衰减分析 → 最优持仓周期（向量化，极速版）"""

    def __init__(self, max_horizon=60):
        self.max_horizon = max_horizon
        self.ic_curve = None
        self.half_life = None
        self.optimal_hold = None
        self.last_update = None

    def fit(self, factor_df, daily_df, causal_factors):
        if daily_df is None or factor_df is None:
            return
        import datetime
        self.last_update = datetime.datetime.now()

        if "mom_20d_z" not in factor_df.columns:
            return

        # 1. pivot: date × code → close，一次性
        piv = daily_df.pivot(index="date", columns="code", values="close")
        piv = piv.sort_index()
        dates = piv.index
        if len(dates) < self.max_horizon + 30:
            self._set_defaults()
            return

        # 2. 每 5 个交易日取一个截面的评分：直接用最后 N 个截面
        step = 5
        n_slices = min(50, len(dates) // step)  # 最多 50 个截面
        slice_indices = list(range(0, len(dates), step))[-n_slices:]

        # 3. 评分代理：取每个截面日期的 mom_20d_z（用最近的因子截面近似）
        #    更准确：用日线截面算当日收益率作为评分
        if len(dates) >= step * n_slices:
            # 用收益率作为瞬时评分
            score_piv = piv.pct_change().shift(-1).dropna(how="all")
        else:
            self._set_defaults()
            return

        # 4. 向量化计算每个 horizon 的 IC
        ic_curve = np.zeros(self.max_horizon)
        close_arr = piv.values  # shape: (T, N)
        rets = np.diff(np.log(close_arr), axis=0)  # shape: (T-1, N) — 对数日收益

        for h in range(1, self.max_horizon + 1):
            ic_vals = []
            for t_idx in slice_indices:
                if t_idx + h >= len(rets):
                    continue
                # 评分 = 前一日收益
                scores = rets[t_idx - 1] if t_idx > 0 else rets[t_idx]
                # 前向 h 日累计收益（不含当日）
                fwd = np.sum(rets[t_idx + 1:t_idx + 1 + h], axis=0)
                # 取共有有效值
                mask = ~np.isnan(scores) & ~np.isnan(fwd)
                if mask.sum() < 10:
                    continue
                try:
                    ic, _ = spearmanr(scores[mask], fwd[mask])
                    if not np.isnan(ic):
                        ic_vals.append(ic)
                except Exception:
                    pass
            ic_curve[h - 1] = np.mean(ic_vals) if ic_vals else 0.0

        self.ic_curve = ic_curve

        # 5. 指数衰减拟合
        try:
            popt, _ = curve_fit(
                lambda T, a, b, c: a * np.exp(-b * T) + c,
                np.arange(1, self.max_horizon + 1),
                ic_curve,
                p0=[0.1, 0.1, 0.0], maxfev=5000,
            )
            a, b, c = popt
            self.half_life = int(np.log(2) / b) if b > 0 else 5
        except Exception:
            nonzero = np.where(ic_curve > ic_curve.max() * 0.5)[0]
            self.half_life = nonzero[-1] + 1 if len(nonzero) > 0 else 5

        # Grinold: argmax IC(T)^2 / T
        ic_sq_over_t = ic_curve ** 2 / np.arange(1, self.max_horizon + 1)
        self.optimal_hold = int(np.argmax(ic_sq_over_t) + 1)
        self.optimal_hold = max(3, min(self.optimal_hold, 30))
        self.half_life = max(2, min(self.half_life, 30))

    def _set_defaults(self):
        self.ic_curve = np.exp(-0.1 * np.arange(1, self.max_horizon + 1))
        self.half_life = 7
        self.optimal_hold = 10

    def get_optimal_hold(self):
        return self.optimal_hold or 10

    def get_ic_curve(self):
        return self.ic_curve
