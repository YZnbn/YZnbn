# gui/app.py — v4 仪表盘 + 流水线向导
"""
布局:
┌─────────────────────────────────────────────────┐
│  🌡️ 体温计(大)  │  策略模板  │  预算 + 开始分析  │
├────────┬────────┴───────────┴──────────────────┤
│ 因子图  │        推荐股票表格                    │
│         │                                      │
├────────┴──────────────────────────────────────┤
│ [收益曲线大图] [指标卡片] [历史因子] [热力图]   │
└───────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yaml
import pandas as pd
import numpy as np

from data import CacheDB, Fetcher, Cleaner
from factors import FactorComputer, CausalSelector, Normalizer
from model import RegimeDetector, Scorer, BudgetAdapter
from gui.widgets import Thermometer, StrategySelector, FactorBar, MetricCards
from gui.charts import HistoryChart, ReturnChart, FactorHeatmap


class App:
    def __init__(self, root, config):
        self.root = root
        self.cfg = config
        self.root.title("Stock Thermometer v4 — 智能因子选股")
        self.root.geometry("1280x900")
        self.root.minsize(1000, 700)
        self.root.configure(bg="#f0f0f0")

        # === 初始化后端模块 ===
        import sys as _sys
        if getattr(_sys, 'frozen', False):
            db_path = os.path.join(config["data"]["cache_dir"], "stock_data.db")
        else:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   config["data"]["cache_dir"], "stock_data.db")
        self.db = CacheDB(db_path)
        self.fetcher = Fetcher(config)
        self.cleaner = Cleaner(config)
        self.factor_comp = FactorComputer(config)
        self.normalizer = Normalizer()
        self.causal = CausalSelector(config)
        self.regime_det = RegimeDetector(config)
        self.scorer = Scorer(config)
        self.budget_adapter = BudgetAdapter(config)

        # 数据缓存
        self.spot_df = None
        self.daily_df = None
        self.factor_df = None
        self.causal_factors = []
        self.regime = None
        self.scored_df = None
        self.index_df = None
        self._last_top5 = None

        self._setup_ui()
        self._init_data()

    # ========== UI 布局 ==========

    def _setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        # ── 顶部栏 ──
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        # 体温计（左）
        self.thermo = Thermometer(top)
        self.thermo.grid(row=0, column=0, rowspan=2, padx=(0, 15))

        # 策略模板（中）
        self.strategy_sel = StrategySelector(top, on_select=self._on_template_select)
        self.strategy_sel.grid(row=0, column=1, rowspan=2, padx=10, sticky="n")

        # 预算 + 按钮（右）
        ctrl = ttk.Frame(top)
        ctrl.grid(row=0, column=2, sticky="ne", padx=10)
        ttk.Label(ctrl, text="预算（元）", font=("Microsoft YaHei", 11)).pack(side=tk.LEFT)
        self.budget_entry = ttk.Entry(ctrl, width=12, font=("Microsoft YaHei", 12))
        self.budget_entry.insert(0, "5000")
        self.budget_entry.pack(side=tk.LEFT, padx=5)
        self.analyze_btn = ttk.Button(ctrl, text="🚀 开始分析",
                                      command=self._on_analyze, style="Accent.TButton")
        self.analyze_btn.pack(side=tk.LEFT, padx=5)
        self.analyze_btn.configure(state="disabled")

        # 状态栏
        self.status_label = ttk.Label(ctrl, text="初始化中...",
                                      font=("Microsoft YaHei", 9), foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # ── 中间区：因子图 + 推荐表 ──
        mid = ttk.Frame(self.root, padding=10)
        mid.pack(fill=tk.BOTH, expand=True)
        mid.columnconfigure(1, weight=1)

        # 因子柱状图（左）
        factor_panel = ttk.LabelFrame(mid, text="有效因子", padding=5)
        factor_panel.grid(row=0, column=0, sticky="ns", padx=(0, 5))
        self.factor_bar = FactorBar(factor_panel)
        self.factor_bar.pack()

        # 推荐表格（右）
        table_panel = ttk.LabelFrame(mid, text="推荐股票", padding=5)
        table_panel.grid(row=0, column=1, sticky="nsew")
        table_panel.rowconfigure(0, weight=1)
        table_panel.columnconfigure(0, weight=1)

        cols = ("code", "name", "score", "pred_ret", "hold_days", "direction", "price", "shares", "cost")
        self.tree = ttk.Treeview(table_panel, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree.heading(c, text={"code": "代码", "name": "名称", "score": "得分",
                                       "pred_ret": "预期收益", "hold_days": "持仓天",
                                       "direction": "方向", "price": "单价",
                                       "shares": "股数", "cost": "占用"}[c])
        self.tree.column("code", width=70)
        self.tree.column("name", width=75)
        self.tree.column("score", width=45)
        self.tree.column("pred_ret", width=60)
        self.tree.column("hold_days", width=50)
        self.tree.column("direction", width=45)
        self.tree.column("price", width=50)
        self.tree.column("shares", width=50)
        self.tree.column("cost", width=55)
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.summary_label = ttk.Label(table_panel, text="", font=("Microsoft YaHei", 9))
        self.summary_label.grid(row=1, column=0, pady=3)

        # ── 底部 Notebook ──
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 1: 收益曲线大图
        self.return_tab = ttk.Frame(nb)
        nb.add(self.return_tab, text="📊 收益曲线")
        self.return_chart = ReturnChart(self.return_tab)
        self.return_chart.pack(fill=tk.BOTH, expand=True)

        # Tab 2: 指标卡片
        self.metrics_tab = ttk.Frame(nb)
        nb.add(self.metrics_tab, text="📈 关键指标")
        self.metric_cards = MetricCards(self.metrics_tab)
        self.metric_cards.pack(fill=tk.X, pady=20)

        # Tab 3: 历史因子
        self.history_tab = ttk.Frame(nb)
        nb.add(self.history_tab, text="📅 历史因子")
        self.history_chart = HistoryChart(self.history_tab)
        self.history_chart.pack(fill=tk.BOTH, expand=True)

        # Tab 4: 因子热力图
        self.heatmap_tab = ttk.Frame(nb)
        nb.add(self.heatmap_tab, text="🔥 因子相关性")
        self.heatmap_chart = FactorHeatmap(self.heatmap_tab)
        self.heatmap_chart.pack(fill=tk.BOTH, expand=True)

    # ========== 数据加载 ==========

    def _init_data(self):
        def _load():
            try:
                self._set_status("⏳ 加载行情数据...")
                self.index_df = self.fetcher.get_index_daily()
                self.spot_df = self.fetcher.get_spot()
                self.spot_df = self.cleaner.filter_stocks(self.spot_df)

                if self.index_df is not None and len(self.index_df) > 0:
                    self.regime = self.regime_det.detect(self.index_df)
                    self.root.after(0, lambda: self.thermo.update(self.regime))

                cache_count = 0
                try:
                    cache_count = len(self.db.get_all_codes_with_data(min_days=60))
                except:
                    pass

                if cache_count >= 500:
                    self.daily_df = self.db.load_daily(start="20240101")
                    self._set_status(f"✅ 全量模式 · {cache_count} 只 · 点击开始分析")
                else:
                    self._set_status(f"⚠️ 缓存不足({cache_count}只) · 请先运行 preloader")

                self.root.after(0, lambda: self.analyze_btn.configure(state="normal"))
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
                    else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                with open(os.path.join(log_dir, "error.log"), "w", encoding="utf-8") as f:
                    f.write(err)
                self._set_status(f"❌ {err.strip().split(chr(10))[-1]}")

        threading.Thread(target=_load, daemon=True).start()

    # ========== 分析流程 ==========

    def _on_template_select(self, key):
        tmpl = self.strategy_sel.get_selected()
        self._set_status(f"📋 已选: {tmpl['name']} — {tmpl['desc']}")

    def _on_analyze(self):
        try:
            budget = float(self.budget_entry.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效预算")
            return
        if budget < 500:
            messagebox.showerror("错误", "预算至少 500 元")
            return
        if self.daily_df is None or len(self.daily_df) == 0:
            messagebox.showwarning("提示", "日线尚未加载完成")
            return

        self.analyze_btn.configure(state="disabled", text="分析中...")

        def _run():
            try:
                # 第1步：因子计算
                self._set_status("📊 Step 1/3: 计算因子...")
                if self.factor_df is None:
                    self.factor_df = self.factor_comp.compute_all(self.daily_df, self.spot_df)
                    if self.factor_df is not None and len(self.factor_df) > 0:
                        fc = [c for c in self.factor_df.columns
                              if c.endswith(("_20d", "_60d", "_120d", "_inv", "_ratio"))
                              or c in ("roe", "gross_margin") or c.startswith("rsi_") or c.startswith("pos_")]
                        self.factor_df = self.normalizer.normalize(self.factor_df, fc)

                # 第2步：因子筛选
                self._set_status("🔍 Step 2/3: 筛选有效因子...")
                tmpl = self.strategy_sel.get_selected()
                self.causal_factors = self.causal._fallback_correlation(self.factor_df, self.daily_df)

                self.root.after(0, lambda: self.factor_bar.update(self.causal_factors))
                self.root.after(0, lambda: self.history_chart.update(self.causal_factors))
                self.root.after(0, lambda: self.heatmap_chart.update(self.factor_df, self.causal_factors))

                # 模型训练
                self._fit_models()

                # 第3步：打分 + 推荐
                self._set_status("🎯 Step 3/3: 生成推荐...")
                self.scored_df = self.scorer.score(
                    self.factor_df, self.causal_factors, self.regime or {"regime": 0})
                results = self.budget_adapter.adapt(self.scored_df, self.spot_df, budget)
                top5 = self.budget_adapter.allocate(results, budget, top_n=5)
                self._last_top5 = top5

                top_codes = [r["code"] for r in top5]
                self.root.after(0, lambda: self._update_table(top5))
                self.root.after(0, lambda: self._update_charts(top_codes))

                n = len(self.causal_factors)
                self._set_status(f"✅ 完成 · {n}个有效因子 · 推荐{len(top5)}只 · 预算¥{budget}")

            except Exception as e:
                import traceback
                err = traceback.format_exc()
                print(f"[App] {err}", flush=True)
                self._set_status(f"❌ {e}")
            finally:
                self.root.after(0, lambda: self.analyze_btn.configure(
                    state="normal", text="🚀 开始分析"))

        threading.Thread(target=_run, daemon=True).start()

    def _fit_models(self):
        try:
            from model.predictor import ReturnPredictor, ICDecayAnalyzer
            ic_analyzer = ICDecayAnalyzer(max_horizon=60)
            ic_analyzer.fit(self.factor_df, self.daily_df, self.causal_factors)
            hold_days = ic_analyzer.get_optimal_hold()
            self.scorer._hold_days = hold_days

            predictor = ReturnPredictor()
            predictor.fit(self.factor_df, self.daily_df, self.causal_factors,
                          hold_days=hold_days)
            self.scorer._predictor = predictor

            self._set_status(f"🧠 模型训练完成 · 最优持仓{hold_days}天 · R²={predictor.r2}")
        except Exception as e:
            print(f"[ModelFit] {e}", flush=True)
            self.scorer._hold_days = 10

    # ========== 结果更新 ==========

    def _update_table(self, results):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in results:
            self.tree.insert("", "end", values=(
                r["code"], r["name"], r["score"],
                f'{r.get("pred_ret", 0):+.1f}%',
                r.get("hold_days", 0),
                r["direction"],
                r["price"], r["shares"], r["cost"],
            ))
        short = sum(1 for r in results if r["direction"] == "短线")
        long = sum(1 for r in results if r["direction"] == "长线")
        self.summary_label.configure(text=f"短线: {short} | 长线: {long}")

    def _update_charts(self, top_codes):
        # 收益曲线
        budget = 5000
        try:
            budget = float(self.budget_entry.get())
        except:
            pass
        from backtest.engine import run_backtest
        bt = run_backtest(self.daily_df, top_codes, budget=budget)
        self.return_chart.update(self.daily_df, self.index_df, top_codes, bt)
        self.metric_cards.update(bt)

    def _set_status(self, text):
        self.root.after(0, lambda: self.status_label.configure(text=text))
