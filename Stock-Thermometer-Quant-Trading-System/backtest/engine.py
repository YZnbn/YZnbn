# backtest/engine.py — backtrader 回测引擎 ★ 接真实 A 股数据

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime


class EqualWeightStrategy(bt.Strategy):
    """等权买入 Top N 股票，每月调仓"""

    params = (
        ("lookback", 120),
        ("rebalance_freq", 20),
        ("top_n", 5),
        ("budget", 5000),
    )

    def __init__(self):
        self.day_count = 0

    def next(self):
        self.day_count += 1
        if self.day_count % self.params.rebalance_freq != 0:
            return

        # 清仓
        for data in self.datas:
            pos = self.getposition(data)
            if pos.size > 0:
                self.close(data)

        # 等权买入所有数据（已预筛选为 Top N）
        n = len(self.datas)
        if n == 0:
            return
        per_stock = self.params.budget / n
        for data in self.datas:
            price = data.close[0]
            if price > 0:
                size = int(per_stock / price)
                if size > 0:
                    self.buy(data, size=size)

    def notify_order(self, order):
        pass  # 不回显


def run_backtest(daily_df, top_codes, budget=5000, start_date="2024-01-01"):
    """
    参数:
        daily_df: DataFrame with columns [code, date, open, high, low, close, volume]
        top_codes: list of stock codes (e.g. ['sh600027', 'sz000001'])
        budget: total capital in CNY
        start_date: backtest start date (YYYY-MM-DD)

    返回:
        dict: {total_return, annual_return, sharpe, max_drawdown, final_value, total_trades}
    """
    if daily_df is None or len(daily_df) == 0:
        return None
    if not top_codes:
        return None

    cerebro = bt.Cerebro()

    # 为每只推荐股票创建数据 feed
    valid_codes = []
    for code in top_codes:
        stock = daily_df[daily_df["code"] == code].copy()
        if len(stock) < 60:
            continue
        stock = stock.sort_values("date")
        stock["date"] = pd.to_datetime(stock["date"])
        stock = stock.set_index("date")
        # 截取回测起始日期之后
        stock = stock[stock.index >= start_date]
        if len(stock) < 30:
            continue

        # backtrader 要求的列: datetime, open, high, low, close, volume, openinterest
        data = bt.feeds.PandasData(
            dataname=stock[["open", "high", "low", "close", "volume"]],
            open="open", high="high", low="low", close="close", volume="volume",
            openinterest=-1,
        )
        cerebro.adddata(data, name=code)
        valid_codes.append(code)

    if not valid_codes:
        return None

    # 策略
    cerebro.addstrategy(
        EqualWeightStrategy,
        lookback=120,
        rebalance_freq=20,
        top_n=len(valid_codes),
        budget=budget,
    )

    # 初始资金
    cerebro.broker.setcash(budget)
    cerebro.broker.setcommission(commission=0.0003)  # 万三佣金

    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe",
                         riskfreerate=0.03, annualize=True)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    try:
        results = cerebro.run()
        strat = results[0]
    except Exception as e:
        print(f"[Backtest] cerebro.run 失败: {e}")
        return None

    # 提取指标
    sharpe_a = strat.analyzers.sharpe.get_analysis()
    dd = strat.analyzers.drawdown.get_analysis()
    ret = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()

    sharpe_val = sharpe_a.get("sharperatio", 0)
    if sharpe_val is None:
        sharpe_val = 0

    max_dd = dd.get("max", {}).get("drawdown", 0) or 0
    total_ret = round(ret.get("rtot", 0) * 100, 2) if ret.get("rtot") else 0
    annual_ret = round(ret.get("rnorm100", 0), 2) if ret.get("rnorm100") else 0

    return {
        "final_value": round(cerebro.broker.getvalue(), 2),
        "total_return": total_ret,
        "annual_return": annual_ret,
        "sharpe_ratio": round(sharpe_val, 3),
        "max_drawdown": round(max_dd, 2),
        "total_trades": trades.get("total", {}).get("total", 0),
        "valid_codes": valid_codes,
    }


# ── 离线测试 ──
if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data.fetcher import Fetcher

    f = Fetcher({"data": {"cache_dir": "cache"}})
    daily = f.get_stock_daily("sh600519", start="20240101")
    if daily is not None:
        result = run_backtest(daily, ["sh600519"], budget=10000)
        print(result)
