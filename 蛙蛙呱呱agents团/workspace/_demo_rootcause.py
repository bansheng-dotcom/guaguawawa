# -*- coding: utf-8 -*-
"""演示：R06 蛙得清 · 抖音店铺销售额下跌根因分析（走一遍真实技能流程）。

流程 = 质量门禁 → 清洗 → 前后期切分 → 根因贡献分解 → 下钻帕累托。
仅用现有演示数据 orders_cleaned.csv，不接入任何外部系统。
"""
import argparse
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENTS = _REPO
_R06 = os.path.join(_AGENTS, "r06-wadeqing-analyst")
for _p in (_R06, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import s02_quality, s04_rootcause, _common as c  # noqa: E402

DATA = os.path.join(_AGENTS, "workspace", "artifacts", "orders_cleaned.csv")
OUT = os.path.join(_AGENTS, "workspace", "artifacts", "douyin_demo")
os.makedirs(OUT, exist_ok=True)


def ns(**kw):
    return argparse.Namespace(**kw)


def main():
    steps = {}

    # 1) 质量门禁（只报告，不删）
    rows = c.load_csv(DATA)
    audit = s02_quality.run(ns(action="audit", input=DATA, pk="order_id", date="date"))
    steps["quality_audit"] = audit
    c.write_json(os.path.join(OUT, "quality_audit.json"), audit)

    # 2) 清洗：剔除「缺失金额」与「99999 哨兵值」两处脏数据
    cleaned = []
    dropped = []
    for r in rows:
        amt = str(r.get("amount", "")).strip()
        if not amt:
            dropped.append((r["order_id"], "missing", r["date"]))
            continue
        try:
            if float(amt) >= 90000:
                dropped.append((r["order_id"], "sentinel_99999", r["date"]))
                continue
        except ValueError:
            dropped.append((r["order_id"], "non_numeric", r["date"]))
            continue
        cleaned.append(r)
    steps["cleaning"] = {"rows_before": len(rows), "rows_after": len(cleaned),
                         "dropped": dropped}

    # 3) 前后期切分：11-01~11-06 为 before，11-07~11-12 为 after
    for r in cleaned:
        r["period"] = "before" if int(r["date"][-2:]) <= 6 else "after"
    period_csv = os.path.join(OUT, "orders_period.csv")
    c.write_csv(period_csv, ["order_id", "date", "channel", "amount", "status",
                             "user_id", "period"], cleaned)

    # 4) 根因贡献分解：before→after 按渠道拆解
    decomp = s04_rootcause.run(ns(action="decompose", input=period_csv, dim="channel",
                                 value="amount", period="period",
                                 before="before", after="after"))
    steps["decompose_channel"] = decomp
    c.write_json(os.path.join(OUT, "decompose_channel.json"), decomp)

    # 5) 下钻 + 帕累托
    drill = s04_rootcause.run(ns(action="drilldown", input=period_csv, dim="channel",
                                 value="amount"))
    steps["drilldown_channel"] = drill
    c.write_json(os.path.join(OUT, "drilldown_channel.json"), drill)

    # 汇总 before/after 总量（清洗后），计算实际跌幅
    tot = {"before": 0.0, "after": 0.0}
    for r in cleaned:
        tot[r["period"]] += float(r["amount"])
    pct = (tot["after"] - tot["before"]) / tot["before"] * 100 if tot["before"] else 0.0
    steps["overall"] = {"before_total": round(tot["before"], 2),
                        "after_total": round(tot["after"], 2),
                        "change_pct": round(pct, 2)}

    c.write_json(os.path.join(OUT, "_demo_steps.json"), steps)
    c.emit({"out_dir": OUT, "overall": steps["overall"],
            "dropped": dropped,
            "decompose": decomp["segments"]})


if __name__ == "__main__":
    main()
