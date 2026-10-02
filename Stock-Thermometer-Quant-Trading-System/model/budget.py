# model/budget.py — 资金适配

import math


class BudgetAdapter:
    """资金过滤 + 建议股数计算"""

    def __init__(self, config):
        self.lot_size = config["budget"]["lot_size"]
        self.etf_alternatives = config["budget"]["etf_alternatives"]

    def adapt(self, scored_df, spot_df, budget):
        """
        参数:
            scored_df: 打分结果 (code, score, direction)
            spot_df: 实时行情 (code, price, name)
            budget: 用户预算

        返回:
            list of dict: [{code, name, price, score, direction, shares, cost, etf_fallback}]
        """
        results = []

        for _, row in scored_df.iterrows():
            code = row["code"]
            spot_row = spot_df[spot_df["code"] == code]

            if len(spot_row) == 0:
                continue

            price = float(spot_row["price"].iloc[0])
            name = str(spot_row["name"].iloc[0])

            # 计算可买股数
            max_lots = int(budget / (price * self.lot_size))
            shares = max_lots * self.lot_size if max_lots > 0 else 0
            cost = shares * price

            fallback = None
            if shares == 0:
                # 买不起 → ETF 替代
                fallback = self.etf_alternatives[0] if self.etf_alternatives else None

            results.append({
                "code": code,
                "name": name,
                "price": round(price, 2),
                "score": round(row["score"], 1),
                "direction": row["direction"],
                "shares": shares,
                "cost": round(cost, 2),
                "etf_fallback": fallback,
                "pred_ret": round(row.get("pred_ret", 0.0), 1),
                "hold_days": int(row.get("hold_days", 0)),
            })

        return results

    def allocate(self, results, budget, top_n=5):
        """等权分配预算，不超总额，买不起的跳过"""
        affordable = [r for r in results if r["shares"] > 0]
        if not affordable:
            return []

        # 逐只尝试：每次买1手（100股），预算够就加，不够就跳过
        total_cost = 0
        valid = []
        for r in affordable:
            cost_1lot = r["price"] * self.lot_size
            if total_cost + cost_1lot <= budget:
                r["shares"] = self.lot_size
                r["cost"] = round(cost_1lot, 2)
                total_cost += cost_1lot
                valid.append(r)
            else:
                r["shares"] = 0
                r["cost"] = 0
            if len(valid) >= top_n:
                break

        return valid
