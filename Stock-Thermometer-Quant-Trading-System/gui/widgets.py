# gui/widgets.py — v4 仪表盘组件

import tkinter as tk
from tkinter import ttk


class Thermometer(ttk.Frame):
    """市场体温计 — 大号仪表盘"""

    def __init__(self, parent):
        super().__init__(parent, padding=15)
        self.columnconfigure(0, weight=1)

        # 标题
        ttk.Label(self, text="🌡️ 市场体温", font=("Microsoft YaHei", 16, "bold")).grid(
            row=0, column=0, pady=(0, 5))

        # 温度数值
        self.temp_label = ttk.Label(self, text="--°C", font=("Microsoft YaHei", 36, "bold"))
        self.temp_label.grid(row=1, column=0)

        # 温度条 (Canvas)
        self.canvas = tk.Canvas(self, width=200, height=24, bg="#e0e0e0",
                                highlightthickness=0)
        self.canvas.grid(row=2, column=0, pady=5)

        # 状态文字
        self.status_label = ttk.Label(self, text="等待数据...",
                                      font=("Microsoft YaHei", 11),
                                      foreground="gray")
        self.status_label.grid(row=3, column=0)

        # 操作建议
        self.advice_label = ttk.Label(self, text="",
                                      font=("Microsoft YaHei", 10, "italic"),
                                      foreground="#555", wraplength=220)
        self.advice_label.grid(row=4, column=0, pady=(5, 0))

    def update(self, regime):
        """regime: {"regime": 1/0/-1, "score": 0-100}"""
        if not regime:
            return

        score = regime.get("score", 50)
        regime_type = regime.get("regime", 0)
        temp = int(score)

        # 颜色
        if regime_type == 1:
            color, status, advice = "#e74c3c", "🟡 牛市 — 市场活跃", "建议进攻策略：动量因子 + 趋势追踪"
        elif regime_type == -1:
            color, status, advice = "#3498db", "🔵 熊市 — 市场低迷", "建议防守策略：价值因子 + 低波动"
        else:
            color, status, advice = "#95a5a6", "⚪ 震荡 — 方向不明", "建议混合策略：因子分散 + 控制仓位"

        self.temp_label.configure(text=f"{temp}°C", foreground=color)
        self.status_label.configure(text=status)

        # 画温度条
        self.canvas.delete("all")
        w = 200
        bar_w = int(w * temp / 100)
        self.canvas.create_rectangle(0, 0, bar_w, 24, fill=color, outline="")
        self.canvas.create_rectangle(0, 0, w, 24, outline="#999")
        # 刻度线
        for pct in [20, 40, 60, 80]:
            x = int(w * pct / 100)
            self.canvas.create_line(x, 16, x, 24, fill="#666")

        self.advice_label.configure(text=f"💡 {advice}")


class StrategySelector(ttk.LabelFrame):
    """策略模板选择器"""

    TEMPLATES = {
        "trend": {"name": "📈 趋势追踪", "desc": "RSI + 动量因子，适合牛市",
                  "factors": ["mom_20d", "mom_60d", "rsi_14", "vol_20d"]},
        "value": {"name": "💰 价值发现", "desc": "PE + ROE + 低波动，适合熊市",
                  "factors": ["pe_inv", "pb_inv", "roe", "vol_60d"]},
        "pcmci": {"name": "🧠 PCMCI因果", "desc": "自动因果检验筛选最优因子",
                  "factors": ["auto"]},
        "combo": {"name": "⚡ 综合评分", "desc": "全部因子加权，适应全市场",
                  "factors": ["all"]},
    }

    def __init__(self, parent, on_select=None):
        super().__init__(parent, text="策略模板", padding=10)
        self.on_select = on_select
        self.selected = tk.StringVar(value="pcmci")
        self.buttons = {}

        r = 0
        for key, tmpl in self.TEMPLATES.items():
            btn = ttk.Radiobutton(
                self, text=tmpl["name"], variable=self.selected,
                value=key, command=self._on_change)
            btn.grid(row=r, column=0, sticky="w", pady=2)
            ttk.Label(self, text=tmpl["desc"], font=("Microsoft YaHei", 8),
                      foreground="gray").grid(row=r, column=1, sticky="w", padx=5)
            self.buttons[key] = btn
            r += 1

    def _on_change(self):
        if self.on_select:
            self.on_select(self.selected.get())

    def get_selected(self):
        return self.TEMPLATES.get(self.selected.get(), self.TEMPLATES["pcmci"])


class FactorBar(ttk.Frame):
    """有效因子仪表盘 — 横向柱状图"""

    def __init__(self, parent):
        super().__init__(parent, padding=5)
        self.canvas = tk.Canvas(self, height=180, bg="white", highlightthickness=1,
                                highlightbackground="#ddd")
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def update(self, causal_factors, highlight=None):
        """causal_factors: [(name, mci), ...]"""
        self.canvas.delete("all")
        if not causal_factors:
            self.canvas.create_text(150, 90, text="暂无因子数据",
                                    font=("Microsoft YaHei", 12), fill="gray")
            return

        factors = [(n, abs(m)) for n, m in causal_factors if abs(m) > 0]
        if not factors:
            return

        factors.sort(key=lambda x: x[1], reverse=True)
        names = [f[0] for f in factors]
        values = [f[1] for f in factors]

        w, h = 280, 170
        bar_h = min(25, (h - 40) // len(factors))
        max_v = max(values) if values else 1

        for i, (name, val) in enumerate(factors):
            y = 20 + i * (bar_h + 4)
            bar_w = int((w - 100) * val / max_v)

            color = "#00b894" if name == highlight else "#4ecdc4"
            self.canvas.create_rectangle(90, y, 90 + bar_w, y + bar_h,
                                         fill=color, outline="")
            self.canvas.create_text(85, y + bar_h // 2, text=name,
                                    anchor="e", font=("Microsoft YaHei", 9))
            self.canvas.create_text(93 + bar_w, y + bar_h // 2,
                                    text=f"{val:.3f}", anchor="w",
                                    font=("Microsoft YaHei", 8), fill="#555")


class MetricCards(ttk.Frame):
    """关键指标卡片 — 结果页第二层"""

    def __init__(self, parent):
        super().__init__(parent, padding=5)
        self.cards = {}

        metrics = [
            ("annual_ret", "年化收益", "%", "#00b894"),
            ("sharpe", "夏普比率", "", "#4ecdc4"),
            ("max_dd", "最大回撤", "%", "#e74c3c"),
            ("win_rate", "胜率", "%", "#f39c12"),
        ]

        for i, (key, label, unit, color) in enumerate(metrics):
            frame = ttk.LabelFrame(self, text=label, padding=8)
            frame.grid(row=0, column=i, padx=5, sticky="nsew")
            self.columnconfigure(i, weight=1)

            val_label = ttk.Label(frame, text="--", font=("Microsoft YaHei", 18, "bold"),
                                  foreground=color)
            val_label.pack()
            unit_label = ttk.Label(frame, text=unit, font=("Microsoft YaHei", 9),
                                   foreground="gray")
            unit_label.pack()

            self.cards[key] = (val_label, unit_label)

    def update(self, bt_result):
        """bt_result: backtrader 回测结果 dict"""
        if not bt_result:
            return

        vals = {
            "annual_ret": bt_result.get("annual_return", 0),
            "sharpe": bt_result.get("sharpe_ratio", 0),
            "max_dd": bt_result.get("max_drawdown", 0),
            "win_rate": bt_result.get("win_rate", 0),
        }

        for key, (label, _) in self.cards.items():
            v = vals.get(key, 0)
            if isinstance(v, float):
                label.configure(text=f"{v:+.1f}" if "ret" in key or "dd" in key else f"{v:.2f}")
            else:
                label.configure(text=str(v))
