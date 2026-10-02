# gen_mock_data.py — 生成 Mock 数据，用于离线测试管线
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)
N = 200  # 模拟 200 只股票

# 1. Spot 数据（模拟 akshare stock_zh_a_spot_em 输出）
codes = [f"{600000 + i:06d}" for i in range(100)] + [f"{300000 + i:06d}" for i in range(100)]
names = [f"测试股_{i:03d}" for i in range(N)]
prices = np.random.uniform(5, 100, N)
pe = np.random.uniform(10, 80, N)
pb = np.random.uniform(0.5, 8, N)

spot = pd.DataFrame({
    "代码": codes, "名称": names,
    "最新价": prices, "涨跌幅": np.random.uniform(-5, 5, N),
    "市盈率-动态": pe, "市净率": pb,
    "换手率": np.random.uniform(0.1, 15, N),
    "成交量": np.random.randint(100000, 10000000, N),
    "成交额": np.random.randint(1000000, 500000000, N),
})
spot.to_csv("cache/spot_mock.csv", index=False)
print(f"[1] Spot: {len(spot)} stocks → cache/spot_mock.csv")

# 2. 指数日线
dates = pd.date_range("2024-01-01", datetime.now(), freq="B")
n_days = len(dates)
close = 3500 + np.cumsum(np.random.randn(n_days) * 30)
index_df = pd.DataFrame({
    "date": dates, "open": close * 0.99, "high": close * 1.02,
    "low": close * 0.98, "close": close,
    "volume": np.random.randint(10000000, 50000000, n_days),
})
index_df.to_csv("cache/index_mock.csv", index=False)
print(f"[2] Index: {len(index_df)} days → cache/index_mock.csv")

# 3. 个股日线
daily_rows = []
for code in codes[:100]:  # 先 100 只
    n = np.random.randint(80, 250)
    dates_i = pd.date_range("2024-01-01", periods=n, freq="B")
    c = np.random.uniform(3, 80)
    closes = c + np.cumsum(np.random.randn(n) * c * 0.02)
    for j in range(n):
        daily_rows.append({
            "code": code, "date": dates_i[j],
            "open": closes[j] * 0.995, "high": closes[j] * 1.01,
            "low": closes[j] * 0.99, "close": closes[j],
            "volume": np.random.randint(50000, 5000000),
            "amount": np.random.randint(100000, 50000000),
            "turnover": np.random.uniform(0.1, 10),
        })

daily_df = pd.DataFrame(daily_rows)
daily_df["date"] = pd.to_datetime(daily_df["date"])
daily_df.to_csv("cache/daily_mock.csv", index=False)
print(f"[3] Daily: {len(daily_df)} rows, {daily_df['code'].nunique()} stocks → cache/daily_mock.csv")
print("\n✅ Mock 数据生成完毕！")
