# -*- coding: utf-8 -*-
"""经营层：把价格与产业面换算成可决策的经营指标（data/经营指标.json）。

三条线
  ① 品类矩阵：批发价 / 零售代理价 / 加价倍率 / 9 周变化 / 波动 / 角色
  ② 链路成本卡：1 公斤苹果从赤峰到呼市货架的逐环节成本（A 实测 / B 文献 / C 假设）
  ③ 情景与投资回收：损耗 × 收购价 敏感性矩阵、预冷直发的投入产出
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent
M = json.loads((ROOT / "data" / "底稿指标.json").read_text(encoding="utf-8"))
L2, L4, L5, L6, L7 = M["L2_全国周度"], M["L4_呼市零售"], M["L5_期货"], M["L6_苹果分市场"], M["L7_产业面"]
X, SZ = M["跨层"], M["市场规模"]
OUT = ROOT / "data" / "经营指标.json"

# ---------------------------------------------------------------- ① 品类矩阵
RETAIL = {r["item"]: r for r in []}  # placeholder
retail_items = {k: v for k, v in L4["items"].items()}
last_week = L4["weeks"][-1]


def retail_price(name: str):
    """取该品种最近一个有值的周（柑橘/芒果不是每周都披露）。"""
    d = retail_items.get(name, {})
    if not d:
        return None
    weeks = sorted(d, key=lambda w: w[:10])
    for w in reversed(weeks):
        if d[w].get("price"):
            return d[w]["price"]
    return None


ROLE = {
    "富士苹果": ("价格锚 / 毛利主来源", "备货主力，做引流与礼盒双规格"),
    "鸭梨": ("稳定搭配", "与苹果同货架，走量不压货"),
    "巨峰葡萄": ("季末清货", "只做短保促销，12 月起不备货"),
    "香蕉": ("流量刚需", "低毛利高周转，按周补货"),
    "菠萝": ("场景搭配", "与礼盒组合，单量小"),
    "西瓜": ("反季高价", "少量精品，做果切与拼盘"),
}
MATRIX = []
for item, s in L2["item_summary"].items():
    # 波动率：周度序列标准差 / 均值
    weeks = [w for w in L2["weeks"] if w in L2["table"][item]]
    vals = [L2["table"][item][w]["this"] for w in weeks]
    vol = st.pstdev(vals) / st.mean(vals) * 100 if len(vals) > 1 else None
    rp = retail_price(item.replace("富士", ""))
    role, action = ROLE.get(item, ("—", "—"))
    MATRIX.append({
        "item": item, "wholesale": s["latest_price"], "change_pct": s["change_pct"],
        "volatility_pct": round(vol, 2) if vol is not None else None,
        "yoy_pct": s["latest_yoy"], "retail": rp,
        "multiplier": round(rp / s["latest_price"], 2) if rp else None,
        "role": role, "action": action,
    })
# 追加无全国批发序列、但有呼市零售的品种
for item, role, action in (("柑橘", "冬季主力 / 流量入口", "11—12 月主推，按 3 天补货"),
                           ("芒果", "精品线 / 高单价", "只做礼盒，不铺散装")):
    price = retail_price(item)
    if price:
        MATRIX.append({"item": item, "wholesale": None, "change_pct": None, "volatility_pct": None,
                       "yoy_pct": None, "retail": price, "multiplier": None,
                       "role": role, "action": action})

# ---------------------------------------------------------------- ② 链路成本卡
DIST_KM = 750          # 赤峰→呼市 公路里程（估算，±50 km）
TRUCK_RATE = 0.28      # 元/吨·公里（C，行业区间 0.25—0.40）
LOSS_PCT = 8.0         # 现状损耗（C，苹果冷链 5—10% 区间中值）
PACK = 0.55            # 分选包装 元/公斤（C）
PRECOOL = 0.12         # 产地预冷（C）
HANDLE = 0.08          # 装卸短驳（C）
WAREHOUSE = 0.22       # 销地仓储分拣（C）
CITY_DELIVERY = 0.18   # 城配（C）
COMMISSION = 0.03      # 档口佣金率（C）
PURCHASE = 4.60        # 产地收购价 元/公斤（C；赤峰产地市场 6.00 减 1.4 环节差）
WHOLESALE = L2["item_summary"]["富士苹果"]["latest_price"]  # 8.64（A）

freight = DIST_KM * TRUCK_RATE / 1000  # 元/公斤
base_cost = PURCHASE + PACK + PRECOOL + HANDLE + freight + WAREHOUSE + CITY_DELIVERY
landed_before_loss = base_cost / (1 - LOSS_PCT / 100)
landed = landed_before_loss
commission = WHOLESALE * COMMISSION
total_cost = landed + commission
margin = WHOLESALE - total_cost
COST_CARD = [
    {"node": "产地收购", "value": PURCHASE, "grade": "C", "note": "赤峰产地市场 6.00 元/公斤 − 1.4 环节差"},
    {"node": "分选包装", "value": PACK, "grade": "C", "note": "纸箱 + 人工 + 贴标"},
    {"node": "产地预冷", "value": PRECOOL, "grade": "C", "note": "差压预冷 8—12 小时"},
    {"node": "装卸短驳", "value": HANDLE, "grade": "C", "note": "产地仓 → 装车"},
    {"node": "冷链干线", "value": round(freight, 3), "grade": "C", "note": f"{DIST_KM} km × {TRUCK_RATE} 元/吨·公里"},
    {"node": "销地仓储分拣", "value": WAREHOUSE, "grade": "C", "note": "销地仓 + 分拣 + 暂存"},
    {"node": "城配", "value": CITY_DELIVERY, "grade": "C", "note": "销地仓 → 门店/档口"},
    {"node": "损耗摊销", "value": round(landed_before_loss - base_cost, 3), "grade": "C", "note": f"损耗 {LOSS_PCT}% 摊入"},
    {"node": "档口佣金", "value": round(commission, 3), "grade": "C", "note": f"批发价 × {int(COMMISSION * 100)}%"},
]
UNIT = {
    "purchase": PURCHASE, "freight": round(freight, 3), "base_cost": round(base_cost, 3),
    "loss_pct": LOSS_PCT, "landed": round(landed, 3), "commission": round(commission, 3),
    "total_cost": round(total_cost, 3), "wholesale": WHOLESALE, "margin": round(margin, 3),
    "margin_pct": round(margin / WHOLESALE * 100, 1),
    "retail": X["retail_apple_price"], "retail_margin": round(X["retail_apple_price"] - WHOLESALE, 3),
    "retail_margin_pct": round((X["retail_apple_price"] - WHOLESALE) / X["retail_apple_price"] * 100, 1),
    "premium_grade_wholesale": X["spread"]["呼市东瓦窑_元每公斤"],
    "premium_grade_margin": round(X["spread"]["呼市东瓦窑_元每公斤"] - total_cost, 3),
    "premium_grade_margin_pct": round((X["spread"]["呼市东瓦窑_元每公斤"] - total_cost) / X["spread"]["呼市东瓦窑_元每公斤"] * 100, 1),
}

# ---------------------------------------------------------------- ③ 情景与投资
def scenario(purchase: float, loss: float, wholesale: float = WHOLESALE) -> dict:
    bc = purchase + PACK + PRECOOL + HANDLE + freight + WAREHOUSE + CITY_DELIVERY
    ld = bc / (1 - loss / 100)
    tc = ld + wholesale * COMMISSION
    mg = wholesale - tc
    return {"purchase": purchase, "loss_pct": loss, "total_cost": round(tc, 3),
            "margin": round(mg, 3), "margin_pct": round(mg / wholesale * 100, 1)}


SCEN = {
    "乐观": scenario(4.30, 5.0),
    "基准": scenario(4.60, 8.0),
    "悲观": scenario(4.95, 12.0),
}
SENS = [[scenario(p, l) for l in (5.0, 8.0, 12.0)] for p in (4.30, 4.60, 4.95)]

# 直采 + 预冷改造：省一道批发（0.35）+ 损耗 8%→5%（约 0.22）+ 集拼（0.05）
SAVE_PER_KG = 0.35 + 0.22 + 0.05
INVEST = 700_000  # 预冷库 30 万 + 冷链车 25 万 + 分选线 15 万（C）
for vol in (1500, 3000):
    pass
ROI = {
    "invest": INVEST, "save_per_kg": round(SAVE_PER_KG, 3),
    "annual_save_1500t": round(SAVE_PER_KG * 1500 * 1000, 0),
    "annual_save_3000t": round(SAVE_PER_KG * 3000 * 1000, 0),
    "payback_years_1500t": round(INVEST / (SAVE_PER_KG * 1500 * 1000), 2),
    "payback_years_3000t": round(INVEST / (SAVE_PER_KG * 3000 * 1000), 2),
}

# 经营节奏（12 月—春节前）
CALENDAR = [
    {"month": "2026-11", "focus": "柑橘起量、苹果稳价", "stock": "苹果按周补、柑橘按 3 天补",
     "kpi": "柑橘动销率 ≥ 85%、苹果周转 ≤ 7 天"},
    {"month": "2026-12", "focus": "双旦礼盒、苹果分级", "stock": "礼盒备货 +30%，散装不压货",
     "kpi": "礼盒毛利率 ≥ 35%、损耗 ≤ 6%"},
    {"month": "2027-01", "focus": "春节前 20 天冲刺", "stock": "苹果锁量不锁价、分批点价",
     "kpi": "节前 20 天销量占全季 ≥ 40%"},
    {"month": "2027-02", "focus": "节后清库、止损", "stock": "葡萄/草莓清货，苹果转加工",
     "kpi": "节后库存 ≤ 5 天销量"},
]

SYSTEM = {
    "matrix": MATRIX, "cost_card": COST_CARD, "unit": UNIT, "scenarios": SCEN,
    "sensitivity": [{"purchase": p, "rows": r} for p, r in zip((4.30, 4.60, 4.95), SENS)],
    "roi": ROI, "calendar": CALENDAR,
    "assumptions": {
        "dist_km": DIST_KM, "truck_rate": TRUCK_RATE, "loss_pct": LOSS_PCT, "purchase": PURCHASE,
        "note": "标 C 的均为行业区间内假设，不来自本次观测；标 A 的来自 L2/L4/L6 实测。",
    },
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(SYSTEM, ensure_ascii=False, indent=1), encoding="utf-8")
    print("品类矩阵：")
    for r in MATRIX:
        print(f"  {r['item']:<6} 批发={r['wholesale']} 变化={r['change_pct']} 波动={r['volatility_pct']} "
              f"零售={r['retail']} 倍率={r['multiplier']} 角色={r['role']}")
    print("\n单位经济：", json.dumps(UNIT, ensure_ascii=False))
    print("\n情景：", json.dumps(SCEN, ensure_ascii=False))
    print("\nROI：", json.dumps(ROI, ensure_ascii=False))
