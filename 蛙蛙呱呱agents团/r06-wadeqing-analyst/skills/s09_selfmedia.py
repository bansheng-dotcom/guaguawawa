# -*- coding: utf-8 -*-
"""S09 自媒体数据运营 —— 能力域 9。

整合自 专项包《自媒体工作台》的 `normalize-self-media-dashboard.py` +
`check-self-media-dashboard-contract.py` + `daily_pipeline.py`。

主张：**快照不求和、增长按时段求和；新鲜度与准确率是日报的门禁**。
本技能把「多平台归一 → KPI 校验 → 日报(ready/partial/failed)」做成纯标准库链路。
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List

from . import _common as c

NAME = "selfmedia"
DESC = "自媒体数据运营：normalize / dashboard / report"

PLATFORMS = ["小红书", "抖音", "知乎", "B站", "公众号"]
PLATFORM_ALIASES = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "zhihu": "知乎",
    "bilibili": "B站",
    "b站": "B站",
    "wechat": "公众号",
    "gzh": "公众号",
    "公众号": "公众号",
    "抖音": "抖音",
    "小红书": "小红书",
    "知乎": "知乎",
}
# 统一字段 schema（对齐工作台 DAILY_FIELDS / SNAPSHOT_FIELDS）
UNIFIED_FIELDS = ["platform", "date", "fans", "new_fans", "revenue", "posts"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    n = act.add_parser("normalize", help="多平台原始数据归一")
    n.add_argument("--input", required=True, help="原始 JSON（platforms 对象）")
    n.add_argument("--output", default="normalized.json")

    d = act.add_parser("dashboard", help="KPI 汇总 + 新鲜度校验 + 看板状态")
    d.add_argument("--input", required=True, help="归一后 JSON")
    d.add_argument("--today", default=None, help="对账日期，缺省今天")
    d.add_argument("--output", default=None, help="可选：落盘 dashboard JSON，供 report 链式读取")

    r = act.add_parser("report", help="生成日报文本（ready/partial/failed）")
    r.add_argument("--input", required=True, help="dashboard JSON")
    r.add_argument("--output", default="daily_report.md")


def run(args) -> Dict[str, Any]:
    if args.action == "normalize":
        return _normalize(c.load_json(args.input), args.output)
    if args.action == "dashboard":
        return _dashboard(c.load_json(args.input), args.today, args.output)
    if args.action == "report":
        return _report(c.load_json(args.input), args.output)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _normalize(raw: Any, out: str) -> Dict[str, Any]:
    platforms = raw.get("platforms", {}) if isinstance(raw, dict) else {}
    records: List[Dict[str, Any]] = []

    norm_inputs: Dict[str, Any] = {}
    for k, v in platforms.items():
        std_k = PLATFORM_ALIASES.get(k.lower(), k)
        norm_inputs[std_k] = v

    for p in PLATFORMS:
        if p not in norm_inputs:
            continue
        src = norm_inputs[p] or {}
        upd = str(src.get("updated_at") or src.get("last_update") or src.get("date") or "")
        records.append({
            "platform": p,
            "date": str(src.get("date", upd[:10])),
            "fans": float(src.get("fans", 0) or 0),          # 快照，取最新
            "new_fans": float(src.get("new_fans", 0) or 0),  # 增长，求和
            "revenue": float(src.get("revenue", 0) or 0),
            "posts": int(src.get("posts", 0) or 0),
            "updated_at": upd,
        })
    c.write_json(out, {"normalized_at": _ts(), "records": records})
    return {"normalized_path": out, "platform_count": len(records),
            "fields": UNIFIED_FIELDS, "records": records}


def _dashboard(norm: Any, today: str, out: str = None) -> Dict[str, Any]:
    t = c.load_thresholds()["selfmedia"]
    records = norm.get("records", []) if isinstance(norm, dict) else []
    total_fans = sum(r["fans"] for r in records)
    total_new = sum(r["new_fans"] for r in records)
    total_rev = sum(r["revenue"] for r in records)
    total_posts = sum(r["posts"] for r in records)
    # HHI 集中度
    hhi = sum((r["fans"] / total_fans) ** 2 for r in records) if total_fans else 0.0
    tdate = _dt.date.fromisoformat(str(today)[:10]) if today else _dt.date.today()
    by_platform = []
    stale = 0
    for r in records:
        try:
            upd = _dt.date.fromisoformat(r["updated_at"][:10])
            gap = (tdate - upd).days
        except (ValueError, KeyError, TypeError):
            gap = 999
        status = "fresh" if gap <= t["fresh_days"] else (
            "stale" if gap <= t["stale_days"] else "missing")
        if status != "fresh":
            stale += 1
        by_platform.append({"platform": r["platform"], "fans": r["fans"],
                            "new_fans": r["new_fans"], "revenue": r["revenue"],
                            "posts": r["posts"], "updated_at": r["updated_at"],
                            "age_days": gap, "status": status})
    covered = len(records)
    overall = "ready" if covered == len(PLATFORMS) and stale == 0 else (
        "partial" if covered > 0 else "failed")
    result = {"total_fans": round(total_fans, 2), "total_new_fans": round(total_new, 2),
              "total_revenue": round(total_rev, 2), "total_posts": total_posts,
              "hhi": round(hhi, 4), "hhi_grade": _hhi_grade(hhi),
              "platform_count": covered, "stale_count": stale, "status": overall,
              "by_platform": by_platform, "check_date": str(tdate)}
    if out:
        c.write_json(out, result)
    return result


def _report(dash: Dict[str, Any], out: str) -> Dict[str, Any]:
    lines = ["# 自媒体数据日报", "",
             f"状态：`{dash.get('status')}` · 对账日期 {dash.get('check_date')}", ""]
    lines += ["## 核心指标", "",
              f"- 总粉丝 {dash.get('total_fans')}（快照，不求和）",
              f"- 新增粉丝 {dash.get('total_new_fans')}（时段求和）",
              f"- 收入 {dash.get('total_revenue')}",
              f"- 发布数 {dash.get('total_posts')}",
              f"- 集中度 HHI {dash.get('hhi')} → {dash.get('hhi_grade')}", ""]
    lines += ["## 平台明细", "", "| 平台 | 粉丝 | 新增 | 收入 | 发布 | 状态 |",
              "|---|---|---|---|---|---|"]
    for p in dash.get("by_platform", []):
        lines.append(f"| {p['platform']} | {p['fans']} | {p['new_fans']} | "
                     f"{p['revenue']} | {p['posts']} | {p['status']} |")
    lines += ["", "## 结论", "",
              "- 数据归一 + 新鲜度校验完成；`ready`=全平台新鲜，`partial`=部分过期，"
              "`failed`=无数据。",
              "- 新鲜度门禁：updated_at 距今 >1 天标 stale、>7 天标 missing。", ""]
    c.write_text(out, "\n".join(lines))
    return {
        "report_path": out,
        "status": dash.get("status"),
        "platform_count": len(dash.get("by_platform", [])),
        "total_fans": dash.get("total_fans", 0),
        "total_revenue": dash.get("total_revenue", 0),
    }


def _hhi_grade(hhi: float) -> str:
    t = c.load_thresholds()["selfmedia"]
    if hhi > t["hhi_extreme"]:
        return "极端集中"
    if hhi >= t["hhi_high"]:
        return "高度集中"
    return "健康"


def _ts() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())