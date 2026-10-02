import os
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

import akshare as ak
df = ak.stock_zh_a_spot_em()
print(f"Loaded: {len(df)} stocks")
print(df[["代码", "名称", "最新价"]].head(5).to_string())
