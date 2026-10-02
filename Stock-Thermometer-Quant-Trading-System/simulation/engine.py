# simulation/engine.py — 虚拟交易模拟引擎
"""
实战模拟：7天虚拟交易实验

预算梯度（7档）：
  500 | 1,000 | 5,000 | 10,000 | 50,000 | 100,000 | 500,000

流程：
  Day 1: 按软件推荐买入 → 记录买入价
  Day 2-7: 每日收盘后检查盈亏 → 报告
  Day 7: 卖出所有持仓 → 总结盈亏

状态文件: simulation/state.json
"""

import json, os, time
import pandas as pd
import numpy as np
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

BUDGET_TIERS = [500, 1000, 5000, 10000, 50000, 100000, 500000]

TRADING_DAYS = 5  # 一周实际交易日


@dataclass
class Position:
    code: str
    name: str
    shares: int
    entry_price: float
    entry_date: str
    budget_tier: int
    direction: str = ""

    @property
    def cost(self):
        return self.shares * self.entry_price


@dataclass
class Snapshot:
    date: str
    positions: List[Dict] = field(default_factory=list)
    total_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    market_temp: float = 50.0


@dataclass
class SimulationState:
    experiment_id: str = ""
    start_date: str = ""
    end_date: str = ""
    budget_tiers: List[int] = field(default_factory=lambda: BUDGET_TIERS)
    positions: Dict[int, List[Position]] = field(default_factory=dict)  # tier → positions
    snapshots: List[Snapshot] = field(default_factory=list)
    day: int = 0
    status: str = "init"  # init | running | completed
    summary: Dict = field(default_factory=dict)


class SimulationEngine:
    """模拟引擎"""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> SimulationState:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._from_dict(data)
        return SimulationState(
            experiment_id=datetime.now().strftime("%Y%m%d_%H%M"),
            start_date=datetime.now().strftime("%Y-%m-%d"),
        )

    def _save_state(self):
        data = self._to_dict()
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _to_dict(self) -> dict:
        return {
            "experiment_id": self.state.experiment_id,
            "start_date": self.state.start_date,
            "end_date": self.state.end_date,
            "budget_tiers": self.state.budget_tiers,
            "positions": {
                str(k): [asdict(p) for p in v]
                for k, v in self.state.positions.items()
            },
            "snapshots": [asdict(s) for s in self.state.snapshots],
            "day": self.state.day,
            "status": self.state.status,
            "summary": self.state.summary,
        }

    def _from_dict(self, data: dict) -> SimulationState:
        state = SimulationState(
            experiment_id=data.get("experiment_id", ""),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            budget_tiers=data.get("budget_tiers", BUDGET_TIERS),
            day=data.get("day", 0),
            status=data.get("status", "init"),
            summary=data.get("summary", {}),
        )
        for k, v in data.get("positions", {}).items():
            state.positions[int(k)] = [
                Position(**p) for p in v
            ]
        state.snapshots = [Snapshot(**s) for s in data.get("snapshots", [])]
        return state

    # ========== Day 1: 建仓 ==========

    def open_positions(self, tier_results: Dict[int, List[dict]], spot_df=None):
        """
        tier_results: {500: [{code, name, price, shares, ...}], ...}
        为每个预算档位记录买入
        """
        self.state.status = "running"
        self.state.day = 1
        self.state.positions = {}

        for tier, recs in tier_results.items():
            positions = []
            for r in recs:
                pos = Position(
                    code=r["code"],
                    name=r.get("name", ""),
                    shares=r["shares"],
                    entry_price=r["price"],
                    entry_date=datetime.now().strftime("%Y-%m-%d"),
                    budget_tier=tier,
                    direction=r.get("direction", ""),
                )
                positions.append(pos)
            self.state.positions[tier] = positions

        # 记录初始快照
        self._record_snapshot("建仓日")
        self._save_state()

    # ========== Day 2-7: 每日盯市 ==========

    def mark_to_market(self, spot_df):
        """
        用当日收盘价计算所有持仓的市值和盈亏
        spot_df: DataFrame with columns [code, price, name]
        """
        if not self.state.positions:
            return None

        price_map = {}
        for _, row in spot_df.iterrows():
            price_map[row["code"]] = row.get("price", 0)

        total_value = 0.0
        total_cost = 0.0
        current_positions = []

        for tier in sorted(self.state.positions.keys()):
            for pos in self.state.positions[tier]:
                cur_price = price_map.get(pos.code, pos.entry_price)
                cur_value = pos.shares * cur_price
                cur_cost = pos.shares * pos.entry_price
                pnl = cur_value - cur_cost
                pnl_pct = (pnl / cur_cost * 100) if cur_cost > 0 else 0

                total_value += cur_value
                total_cost += cur_cost

                current_positions.append({
                    "code": pos.code,
                    "name": pos.name,
                    "shares": pos.shares,
                    "entry": pos.entry_price,
                    "current": cur_price,
                    "cost": cur_cost,
                    "value": cur_value,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "tier": tier,
                })

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        snapshot = Snapshot(
            date=datetime.now().strftime("%Y-%m-%d"),
            positions=current_positions,
            total_value=round(total_value, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl_pct, 2),
        )
        self.state.snapshots.append(snapshot)
        self.state.day += 1
        self._save_state()

        return snapshot

    def _record_snapshot(self, label=""):
        """记录当前持仓快照（不含实时价格）"""
        pos_list = []
        total_cost = 0.0
        for tier in sorted(self.state.positions.keys()):
            for pos in self.state.positions[tier]:
                pos_list.append({
                    "code": pos.code, "name": pos.name,
                    "shares": pos.shares, "entry": pos.entry_price,
                    "cost": pos.cost, "tier": tier,
                })
                total_cost += pos.cost

        snapshot = Snapshot(
            date=f"{datetime.now().strftime('%Y-%m-%d')} ({label})",
            positions=pos_list,
            total_value=total_cost,
            total_pnl=0.0,
            total_pnl_pct=0.0,
        )
        self.state.snapshots.append(snapshot)

    # ========== Day 7: 平仓汇总 ==========

    def close_all(self, spot_df):
        """最后一天卖出所有持仓，计算总盈亏"""
        final = self.mark_to_market(spot_df)
        self.state.status = "completed"
        self.state.end_date = datetime.now().strftime("%Y-%m-%d")
        self.state.summary = self._generate_summary()
        self._save_state()
        return final

    def _generate_summary(self) -> dict:
        """生成实验总结"""
        if not self.state.snapshots:
            return {}

        # 按预算档位汇总
        tier_summary = {}
        for tier in sorted(self.state.positions.keys()):
            positions = self.state.positions[tier]
            total_cost = sum(p.cost for p in positions)

            # 从最近的 snapshot 获取市值
            tier_value = 0
            latest = self.state.snapshots[-1]
            for pos in latest.positions:
                if pos.get("tier") == tier:
                    tier_value += pos.get("value", 0)

            tier_pnl = tier_value - total_cost
            tier_pnl_pct = (tier_pnl / total_cost * 100) if total_cost > 0 else 0

            tier_summary[str(tier)] = {
                "budget": tier,
                "stocks": len(positions),
                "total_cost": round(total_cost, 2),
                "final_value": round(tier_value, 2),
                "pnl": round(tier_pnl, 2),
                "pnl_pct": round(tier_pnl_pct, 2),
            }

        # 全局
        all_costs = sum(
            sum(p.cost for p in self.state.positions[t])
            for t in self.state.positions
        )
        all_value = self.state.snapshots[-1].total_value if self.state.snapshots else 0

        return {
            "experiment_id": self.state.experiment_id,
            "start_date": self.state.start_date,
            "end_date": self.state.end_date,
            "total_days": self.state.day,
            "total_cost": round(all_costs, 2),
            "final_value": round(all_value, 2),
            "total_pnl": round(all_value - all_costs, 2),
            "total_pnl_pct": round((all_value - all_costs) / all_costs * 100, 2) if all_costs > 0 else 0,
            "tier_details": tier_summary,
        }

    # ========== 报告生成 ==========

    def daily_report(self, snapshot: Snapshot) -> str:
        """生成每日报告 — 按预算档位逐一列出盈亏"""
        lines = [
            f"📊 虚拟交易实验 — Day {self.state.day}",
            f"📅 {snapshot.date}",
            f"{'='*45}",
        ]

        if not snapshot.positions:
            lines.append("暂无持仓数据")
            return "\n".join(lines)

        # 按预算分组
        by_tier = {}
        for p in snapshot.positions:
            t = p.get("tier", 0)
            by_tier.setdefault(t, []).append(p)

        for tier in sorted(by_tier.keys()):
            positions = by_tier[tier]
            tier_cost = sum(p["cost"] for p in positions)
            tier_value = sum(p["value"] for p in positions)
            tier_pnl = tier_value - tier_cost
            tier_pnl_pct = (tier_pnl / tier_cost * 100) if tier_cost > 0 else 0
            emoji = "🟢" if tier_pnl >= 0 else "🔴"

            lines.append(f"\n💰 预算 ¥{tier:,} | 投入 ¥{tier_cost:,.0f} | {emoji} ¥{tier_pnl:+,.0f} ({tier_pnl_pct:+.1f}%)")
            lines.append(f"   {'─'*35}")

            # 逐只股票
            for p in positions:
                se = "🟢" if p["pnl"] >= 0 else "🔴"
                lines.append(
                    f"   {se} {p['code']} {p['name']:<6s} "
                    f"¥{p['entry']:.2f}→¥{p['current']:.2f} "
                    f"×{p['shares']}股 {p['pnl_pct']:+.1f}%"
                )

        # 全局汇总
        total_cost = sum(sum(p["cost"] for p in positions) for positions in by_tier.values())
        total_value = sum(sum(p["value"] for p in positions) for positions in by_tier.values())
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        emoji = "🟢" if total_pnl >= 0 else "🔴"

        lines.extend([
            f"\n{'='*45}",
            f"📈 总投入: ¥{total_cost:,.0f}  →  总市值: ¥{total_value:,.0f}",
            f"💵 总盈亏: {emoji} ¥{total_pnl:+,.0f} ({total_pnl_pct:+.1f}%)",
        ])

        return "\n".join(lines)

    def final_report(self) -> str:
        """生成最终实验报告"""
        s = self.state.summary
        if not s:
            return "无数据"

        lines = [
            f"🏁 实验结束 — 总结报告",
            f"📅 {s['start_date']} → {s['end_date']} ({s['total_days']}天)",
            f"{'='*50}\n",
        ]

        # 各档位
        for tier_str, detail in s.get("tier_details", {}).items():
            t = detail
            emoji = "🟢" if t["pnl"] >= 0 else "🔴"
            lines.append(
                f"💰 预算 ¥{t['budget']:,} | {t['stocks']}只 | "
                f"{emoji} ¥{t['pnl']:+,.2f} ({t['pnl_pct']:+.2f}%)"
            )

        # 全局
        emoji = "🟢" if s["total_pnl"] >= 0 else "🔴"
        lines.extend([
            f"\n{'='*50}",
            f"💵 总投入: ¥{s['total_cost']:,.2f}",
            f"💰 终值: ¥{s['final_value']:,.2f}",
            f"{'🎉' if s['total_pnl'] >= 0 else '💔'} 总盈亏: {emoji} ¥{s['total_pnl']:+,.2f} ({s['total_pnl_pct']:+.2f}%)",
            f"\n{'✅ 算法有效，推荐买入' if s['total_pnl'] > 0 else '⚠️ 算法需优化，总体亏损'}",
        ])

        return "\n".join(lines)
