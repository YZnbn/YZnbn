# gui/charts.py — v4 结果分层展示（图表 > 指标 > 表格）

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import pandas as pd
from datetime import datetime
import json
import os
import sys

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

WINDOW_DAYS = 90


def _get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


HISTORY_FILE = os.path.join(_get_app_dir(), "factor_history.json")


class HistoryChart(ttk.Frame):
    """历史有效因子变化图 — 持久化折线图"""

    def __init__(self, parent):
        super().__init__(parent)
        self.fig, self.ax = plt.subplots(figsize=(6, 1.8), dpi=80)
        self.fig.set_facecolor("#f5f5f5")
        self.ax.set_facecolor("#f5f5f5")
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._history = self._load()
        if not self._history:
            self.ax.text(0.5, 0.5, "暂无历史 — 分析后自动记录",
                         ha="center", va="center", transform=self.ax.transAxes,
                         fontsize=11, color="gray")
        else:
            self._draw()
        self.canvas.draw()

    def _load(self):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def update(self, causal_factors):
        n = len([f for f in causal_factors if f[1] > 0])
        self._history.append({
            "date": datetime.now().strftime("%m-%d %H:%M"),
            "n_factors": n,
        })
        if len(self._history) > 90:
            self._history = self._history[-90:]
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._history, f, ensure_ascii=False, indent=2)
        self._draw()

    def _draw(self):
        self.ax.clear()
        if not self._history:
            return
        dates = [r["date"] for r in self._history]
        counts = [r["n_factors"] for r in self._history]
        x = range(len(dates))
        self.ax.plot(x, counts, color="#4ecdc4", lw=2, marker="o", ms=4)
        self.ax.fill_between(x, 0, counts, alpha=0.12, color="#4ecdc4")
        self.ax.set_ylim(0, max(12, max(counts) + 2))
        self.ax.set_title(f"有效因子变化（当前 {counts[-1]} 个）", fontsize=10)
        # tick labels
        step = max(1, len(dates) // 8)
        self.ax.set_xticks(range(0, len(dates), step))
        self.ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)],
                                rotation=30, ha="right", fontsize=7)
        self.fig.tight_layout()
        self.canvas.draw()


class ReturnChart(ttk.Frame):
    """收益曲线大图 — 结果页第一层（最大、最显眼）"""

    def __init__(self, parent):
        super().__init__(parent)
        self.fig, self.ax = plt.subplots(figsize=(8, 3.2), dpi=100)
        self.fig.set_facecolor("#f5f5f5")
        self.ax.set_facecolor("#f5f5f5")
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update(self, daily_df, index_df, top_codes, bt_result=None):
        self.ax.clear()

        # 沪深300 基准
        if index_df is not None and len(index_df) > 0:
            idx = index_df.sort_values("date").copy()
            idx["ret"] = idx["close"].pct_change()
            idx["cum"] = (1 + idx["ret"].fillna(0)).cumprod()
            idx_pct = (idx["cum"] - 1) * 100
            self.ax.plot(pd.to_datetime(idx["date"]), idx_pct.values,
                         label="沪深300", color="#999", lw=2.5, alpha=0.8)

        # 策略组合
        if top_codes and daily_df is not None and len(daily_df) > 0:
            try:
                rets = []
                for code in top_codes:
                    s = daily_df[daily_df["code"] == code].sort_values("date")
                    if len(s) < 20:
                        continue
                    rets.append(s.set_index("date")["close"].pct_change().fillna(0))
                if rets:
                    all_dates = sorted(set().union(*[set(r.index) for r in rets]))
                    eq = np.zeros(len(all_dates))
                    n = len(rets)
                    for r in rets:
                        eq += r.reindex(all_dates).fillna(0).values / n
                    pf_pct = ((1 + eq).cumprod() - 1) * 100
                    self.ax.plot(pd.to_datetime(all_dates), pf_pct,
                                 label=f"策略 ({n}只等权)", color="#00b894", lw=3, alpha=0.9)

                    # 填充正收益区域
                    self.ax.fill_between(pd.to_datetime(all_dates), 0, pf_pct,
                                         where=np.array(pf_pct) >= 0,
                                         color="#00b894", alpha=0.08)
                    self.ax.fill_between(pd.to_datetime(all_dates), 0, pf_pct,
                                         where=np.array(pf_pct) < 0,
                                         color="#e74c3c", alpha=0.08)
            except Exception:
                pass

        self.ax.set_title("回测收益曲线", fontsize=12, fontweight="bold")
        self.ax.axhline(y=0, color="#333", lw=0.8)
        self.ax.legend(fontsize=10, loc="upper left")
        self.ax.set_ylabel("累计收益 (%)")
        self.fig.tight_layout()
        self.canvas.draw()


class FactorHeatmap(ttk.Frame):
    """因子相关性热力图"""

    def __init__(self, parent):
        super().__init__(parent)
        self.fig, self.ax = plt.subplots(figsize=(5, 3.5), dpi=80)
        self.fig.set_facecolor("#f5f5f5")
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.ax.text(0.5, 0.5, "分析后显示因子相关性",
                     ha="center", va="center", transform=self.ax.transAxes,
                     fontsize=11, color="gray")
        self.canvas.draw()

    def update(self, factor_df, causal_factors):
        self.ax.clear()
        if factor_df is None:
            return

        names = [n for n, _ in causal_factors if n in factor_df.columns]
        if len(names) < 2:
            return

        data = factor_df[names].corr().values
        self.ax.imshow(data, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
        self.ax.set_xticks(range(len(names)))
        self.ax.set_yticks(range(len(names)))
        self.ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
        self.ax.set_yticklabels(names, fontsize=7)
        self.ax.set_title("因子相关性矩阵", fontsize=10)

        # 标注数值
        for i in range(len(names)):
            for j in range(len(names)):
                self.ax.text(j, i, f"{data[i, j]:.2f}",
                             ha="center", va="center", fontsize=6,
                             color="white" if abs(data[i, j]) > 0.5 else "black")

        self.fig.tight_layout()
        self.canvas.draw()
