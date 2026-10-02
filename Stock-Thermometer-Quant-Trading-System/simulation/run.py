#!/usr/bin/env python3
# simulation/run.py — 模拟实验入口
"""用法:
  python simulation/run.py init     # Day 1: 初始化 + 建仓
  python simulation/run.py daily    # Day 2-7: 每日盯市
  python simulation/run.py close    # Day 7: 平仓 + 总结
  python simulation/run.py report   # 查看当前报告
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import pandas as pd
from datetime import datetime
from simulation.engine import SimulationEngine, BUDGET_TIERS

# 复用 v4 管线
from data import CacheDB, Fetcher, Cleaner
from factors import FactorComputer, CausalSelector, Normalizer
from model import RegimeDetector, Scorer, BudgetAdapter


def _init_modules(config):
    cache_dir = config.get("data", {}).get("cache_dir", "cache")
    db_path = os.path.join(cache_dir, "stock_data.db")
    return {
        "db": CacheDB(db_path),
        "fetcher": Fetcher(config),
        "cleaner": Cleaner(config),
        "factor_comp": FactorComputer(config),
        "normalizer": Normalizer(),
        "causal": CausalSelector(config),
        "regime": RegimeDetector(config),
        "scorer": Scorer(config),
        "budget": BudgetAdapter(config),
    }


def _load_data(m, config):
    """加载全量数据"""
    print("📥 加载行情数据...")
    spot = m["fetcher"].get_spot()
    spot = m["cleaner"].filter_stocks(spot)

    daily = None
    try:
        daily = m["db"].load_daily(start="20240101")
        print(f"  日线: {len(daily)} 行 ({daily['code'].nunique()} 只)")
    except:
        pass

    return spot, daily


def _run_analysis(m, spot, daily, budget):
    """跑一次完整分析，返回 top5 推荐"""
    print(f"  🔍 分析中 (预算 ¥{budget:,})...")

    factor_df = m["factor_comp"].compute_all(daily, spot)
    if factor_df is None or len(factor_df) == 0:
        return []

    fc = [c for c in factor_df.columns
          if c.endswith(("_20d", "_60d", "_120d", "_inv", "_ratio"))
          or c in ("roe", "gross_margin") or c.startswith("rsi_") or c.startswith("pos_")]
    factor_df = m["normalizer"].normalize(factor_df, fc)

    causal_factors = m["causal"]._fallback_correlation(factor_df, daily)

    # 模型训练
    try:
        from model.predictor import ReturnPredictor, ICDecayAnalyzer
        ic = ICDecayAnalyzer(max_horizon=60)
        ic.fit(factor_df, daily, causal_factors)
        m["scorer"]._hold_days = ic.get_optimal_hold()
        pred = ReturnPredictor()
        pred.fit(factor_df, daily, causal_factors, hold_days=ic.get_optimal_hold())
        m["scorer"]._predictor = pred
    except Exception as e:
        print(f"  ⚠️ 模型训练跳过: {e}")

    scored = m["scorer"].score(factor_df, causal_factors, {"regime": 0})
    results = m["budget"].adapt(scored, spot, budget)
    top5 = m["budget"].allocate(results, budget, top_n=5)

    print(f"  ✅ 推荐 {len(top5)} 只")
    return top5


def cmd_init():
    """Day 1: 初始化实验，为所有预算档位建仓"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    engine = SimulationEngine()

    if engine.state.status == "running":
        print("⚠️ 实验已在运行中！先执行 close 或删除 simulation/state.json 重置")
        return

    m = _init_modules(config)
    spot, daily = _load_data(m, config)

    if daily is None or len(daily) == 0:
        print("❌ 日线数据加载失败，请先运行 preloader")
        return

    tier_results = {}
    for budget in BUDGET_TIERS:
        top5 = _run_analysis(m, spot, daily, budget)
        tier_results[budget] = top5

    engine.open_positions(tier_results, spot)
    print(f"\n✅ 建仓完成！{len(BUDGET_TIERS)} 个预算档位\n")

    # 打印建仓摘要
    for tier in sorted(engine.state.positions.keys()):
        positions = engine.state.positions[tier]
        cost = sum(p.cost for p in positions)
        print(f"  ¥{tier:,}: {len(positions)}只, 投入 ¥{cost:,.2f}")
        for p in positions:
            print(f"    {p.code} {p.name} ×{p.shares} @¥{p.entry_price}")


def cmd_daily():
    """每日盯市"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    engine = SimulationEngine()
    if engine.state.status != "running":
        print("⚠️ 实验未启动，先执行 init")
        return

    m = _init_modules(config)
    spot, _ = _load_data(m, config)

    snapshot = engine.mark_to_market(spot)
    report = engine.daily_report(snapshot)
    print(report)
    return report


def cmd_close():
    """Day 7: 平仓汇总"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    engine = SimulationEngine()
    if engine.state.status != "running":
        print("⚠️ 实验未在运行中")
        return

    m = _init_modules(config)
    spot, _ = _load_data(m, config)

    engine.close_all(spot)
    report = engine.final_report()
    print(report)
    return report


def cmd_report():
    """查看当前报告"""
    engine = SimulationEngine()
    if engine.state.status == "completed":
        print(engine.final_report())
    elif engine.state.status == "running" and engine.state.snapshots:
        last = engine.state.snapshots[-1]
        print(engine.daily_report(last))
    else:
        print("📭 暂无数据，先执行 init")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    {
        "init": cmd_init,
        "daily": cmd_daily,
        "close": cmd_close,
        "report": cmd_report,
    }.get(cmd, cmd_report)()
