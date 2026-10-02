# test_run.py — Pipeline test (Mock)
import sys, os, yaml, io
sys.path.insert(0, ".")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open("config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

import pandas as pd
from data import Cleaner
from factors import FactorComputer, Normalizer, CausalSelector
from model import RegimeDetector, Scorer, BudgetAdapter

print("=" * 50)
print("Stock Thermometer v3 — 管线测试 (Mock)")
print("=" * 50)

# 1. 数据（从 mock CSV 读取）
print("\n[1/5] 加载 mock 数据...")
spot = pd.read_csv("cache/spot_mock.csv")
spot = spot.rename(columns={"代码": "code", "名称": "name", "最新价": "price",
                             "涨跌幅": "pct_chg", "市盈率-动态": "pe", "市净率": "pb",
                             "换手率": "turnover", "成交量": "volume", "成交额": "amount"})
cleaner = Cleaner(cfg)
spot = cleaner.filter_stocks(spot)
print(f"  全A股: {len(spot)} 只 (过滤后)")

# 2. 指数判市
print("\n[2/5] 判市...")
index_df = pd.read_csv("cache/index_mock.csv")
regime_det = RegimeDetector(cfg)
regime = regime_det.detect(index_df)
print(f"  体温: {regime['temperature']}°C  {regime['label']}")

# 3. 因子
print("\n[3/5] 计算因子 (采样 100 只)...")
daily_df = pd.read_csv("cache/daily_mock.csv")
daily_df["date"] = pd.to_datetime(daily_df["date"])
print(f"  日线: {len(daily_df)} 条, {daily_df['code'].nunique()} 只")

factor_comp = FactorComputer(cfg)
factor_df = factor_comp.compute_all(daily_df, spot)
print(f"  因子: {len(factor_df)} 只")

normalizer = Normalizer()
factor_cols = [c for c in factor_df.columns if c.endswith("_20d") or c.endswith("_60d") or c.endswith("_120d")
               or c.endswith("_inv") or c in ["roe","gross_margin"] or c.endswith("_ratio")
               or c.startswith("rsi_") or c.startswith("pos_")]
factor_df = normalizer.normalize(factor_df, [c for c in factor_cols if not c.endswith("_z")])

# 4. PCMCI
print("\n[4/5] PCMCI 因果筛选...")
causal = CausalSelector(cfg)
causal_factors = causal.select(daily_df, factor_df, spot)
print(f"  有效因子: {len(causal_factors)} 个")
for name, mci in causal_factors:
    print(f"    {name}: {mci:.4f}")

# 5. 打分 + 资金
print("\n[5/5] 打分 + 资金适配...")
scorer = Scorer(cfg)
scored = scorer.score(factor_df, causal_factors, regime)
adapter = BudgetAdapter(cfg)
results = adapter.adapt(scored, spot, budget=5000)
top5 = adapter.allocate(results, 5000, top_n=5)

print(f"\n{'='*50}")
print(f"推荐 Top {len(top5)} (预算 5000):")
print(f"{'代码':<10}{'名称':<12}{'得分':<6}{'方向':<6}{'单价':<8}{'股数':<6}{'占用'}")
print("-" * 60)
for r in top5:
    code = r.get("code","?")
    name = r.get("name","?")
    score = r.get("score",0)
    direction = r.get("direction","?")
    price = r.get("price",0)
    shares = r.get("shares",0)
    cost = r.get("cost",0)
    etf = r.get("etf_fallback")
    if etf:
        print(f"{code:<10}{name:<12}{score:<6}{direction:<6}{price:<8}ETF → {etf['name']}")
    else:
        print(f"{code:<10}{name:<12}{score:<6}{direction:<6}{price:<8}{shares:<6}{cost}")
print("=" * 50)
print("\n✅ 管线测试完成")
