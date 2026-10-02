# test_run.py — 无 GUI 管线测试
import sys, os, yaml, time
sys.path.insert(0, ".")

with open("config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

from data import Fetcher, Cleaner, CacheDB
from factors import FactorComputer, Normalizer, CausalSelector
from model import RegimeDetector, Scorer, BudgetAdapter
import pandas as pd

print("=" * 50)
print("Stock Thermometer v3 — 管线测试")
print("=" * 50)

# 1. 数据
print("\n[1/5] 拉取数据...")
fetcher = Fetcher(cfg)
spot = None
for attempt in range(3):
    try:
        spot = fetcher.get_spot()
        break
    except Exception as e:
        print(f"  spot 拉取失败 (尝试 {attempt+1}/3): {e}")
        time.sleep(5)

cleaner = Cleaner(cfg)
if spot is None:
    print("  ❌ spot 数据拉取失败，退出")
    sys.exit(1)
spot = cleaner.filter_stocks(spot)
print(f"  全A股: {len(spot)} 只 (过滤后)")

# 2. 指数判市
print("\n[2/5] 判市...")
index_df = fetcher.get_index_daily()
regime_det = RegimeDetector(cfg)
regime = regime_det.detect(index_df)
print(f"  体温: {regime['temperature']}°C  {regime['label']}")

# 3. 拉取样本日线 + 计算因子（带 SQLite 缓存）
N_SAMPLE = 50
print(f"\n[3/5] 计算因子 (采样 {N_SAMPLE} 只，含缓存)...")
cache = CacheDB()
sample_codes = spot[spot["code"].str.match(r"^(sh|sz)")]["code"].head(N_SAMPLE).tolist()

daily_frames = []
for i, code in enumerate(sample_codes):
    # 先查缓存
    cached = cache.load_daily(code=code, start="20240101")
    if len(cached) > 60:
        daily_frames.append(cached)
    else:
        df = fetcher.get_stock_daily(code, start="20240101")
        if df is not None and len(df) > 60:
            cache.save_daily(df)
            daily_frames.append(df)
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{N_SAMPLE}...")

daily_df = pd.concat(daily_frames, ignore_index=True)
cache.close()
print(f"  日线: {len(daily_df)} 条, {daily_df['code'].nunique()} 只")

factor_comp = FactorComputer(cfg)
factor_df = factor_comp.compute_all(daily_df, spot)
print(f"  因子: {len(factor_df)} 只")

if len(factor_df) == 0:
    print("  ❌ 无有效因子，退出")
    sys.exit(1)

normalizer = Normalizer()
factor_cols = [c for c in factor_df.columns if c.endswith("_20d") or c.endswith("_60d") or c.endswith("_120d")
               or c.endswith("_inv") or c in ["roe","gross_margin"] or c.endswith("_ratio")
               or c.startswith("rsi_") or c.startswith("pos_")]
factor_df = normalizer.normalize(factor_df, [c for c in factor_cols if not c.endswith("_z")])

# 4. Rank IC 因子筛选
print("\n[4/5] Rank IC 因果筛选...")
causal = CausalSelector(cfg)
causal_factors = causal.select(daily_df, factor_df, spot)
print(f"  有效因子: {len(causal_factors)} 个")
for name, mci in causal_factors:
    print(f"    {name}: {mci:.4f}")

# 5. 打分 + 资金适配
print("\n[5/5] 打分 + 资金适配...")
scorer = Scorer(cfg)
scored = scorer.score(factor_df, causal_factors, regime)
adapter = BudgetAdapter(cfg)
results = adapter.adapt(scored, spot, budget=5000)
top5 = adapter.allocate(results, 5000, top_n=5)

print(f"\n{'='*50}")
print(f"推荐 Top {len(top5)} (预算 5000):")
print(f"{'代码':<12}{'名称':<12}{'得分':<8}{'方向':<6}{'单价':<8}{'股数':<6}{'占用'}")
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
        print(f"{code:<12}{name:<12}{score:<8.2f}{direction:<6}{price:<8}ETF → {etf['name']}")
    else:
        print(f"{code:<12}{name:<12}{score:<8.2f}{direction:<6}{price:<8}{shares:<6}{cost}")
print("=" * 50)
print("\n✅ 管线测试完成")
