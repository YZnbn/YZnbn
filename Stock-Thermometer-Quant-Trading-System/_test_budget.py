# Test BudgetAdapter standalone
import yaml, pandas as pd
from model.budget import BudgetAdapter

cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
b = BudgetAdapter(cfg)

r = pd.DataFrame([{"code":"600006","score":1.2,"direction":"long"}])
s = pd.DataFrame({"code":["600006"],"name":["test"],"price":[10.52]})
res = b.adapt(r, s, 5000)
print("Result:", res)
print("shares:", res[0]["shares"])
