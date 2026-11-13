# -*- coding: utf-8 -*-
"""report_kernel · layers —— 由 result(+dataset) 生成三层 contract。

输出兼容 core/report_renderer 的 contract schema，保持"唯一渲染器"。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MAX_RECORD_ROWS = 300  # 记录层表体上限；全量仍可在 store 查


def _num(v: float, nd: int = 2) -> str:
    return f"{v:,.{nd}f}"


def compute_fidelity(dataset: Optional[List[Dict[str, Any]]],
                     used_items: set[str],
                     claims: List[str]) -> Dict[str, Any]:
    """保留率 / 溯源率 / 弃置率。无观测集时返回 None（不伪造）。"""
    if not dataset:
        return {"retention": None, "trace": None, "discard": None,
                "obs_total": 0, "note": "无观测集（该角色不产出数据），保留率 N/A"}
    total = len(dataset)
    used = sum(1 for r in dataset if str(r.get("item")) in used_items)
    traced = sum(1 for c in claims if isinstance(c, dict) and c.get("obs_ids"))
    return {
        "obs_total": total,
        "retention": round(used / total, 4) if total else None,
        "trace": round(traced / len(claims), 4) if claims else None,
        "discard": round((total - used) / total, 4) if total else None,
        "note": "",
    }


def _method_note() -> str:
    return ("指标由观测集直接计算：首值为区间内最早一条、末值为最晚一条，"
            "变化率=(末值-首值)/首值；均值与极值按原始观测统计，未做插值、未做平滑。")


def _analysis_narrative(dataset) -> str:
    if not dataset:
        return "本节无结构化观测，判定依据为执行结果字段。"
    by_item = {}
    for r in dataset:
        try:
            by_item.setdefault(str(r["item"]), []).append(float(r["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    movers = []
    for item, vals in by_item.items():
        if len(vals) >= 2 and vals[0]:
            movers.append((item, (vals[-1] / vals[0] - 1) * 100, vals[0], vals[-1]))
    movers.sort(key=lambda x: -abs(x[1]))
    top = "；".join(f"{m[0]} {m[2]:.2f}→{m[3]:.2f}（{m[1]:+.2f}%）" for m in movers[:3]) or "样本不足以计算变化"
    return (f"本节覆盖 {len(by_item)} 个品类、{len(dataset)} 条观测。"
            f"变化最大的三项：{top}。"
            + _method_note()
            + "结论只对上述区间与口径成立。")


def _boundary_note() -> str:
    return ("范围：仅上述观测集与执行结果；未覆盖的品类、市场与时间段不在结论范围内。"
            "假设：单位换算与口径映射见记录层，缺口未做插值。"
            "降级：数据缺口存在时，结论仅作方向判断，不作数值承诺。")


_CN = {"ok": "通过", "dim": "维度", "msg": "说明", "conclusion": "结论", "summary": "摘要",
       "notes": "备注", "item": "品类", "value": "数值", "unit": "单位", "source": "来源",
       "date": "日期", "name": "名称", "title": "标题", "status": "状态", "reason": "原因",
       "action": "动作", "owner": "负责人", "due": "截止", "checks": "门禁", "gaps": "缺口",
       "next": "下一步", "verdict": "裁决", "score": "得分", "level": "等级",
       # 业务字段（首页指标带用：只放业务结论，不放执行元数据）
       "tam": "TAM", "sam": "SAM", "som": "SOM", "tam_top": "TAM（自上而下）",
       "tam_bottom": "TAM（自下而上）", "variance": "双口径方差", "cr3": "CR3", "cr5": "CR5",
       "hhi": "HHI", "revenue": "营收", "profit": "利润", "margin": "毛利",
       "margin_pct": "毛利率", "growth": "增速", "growth_pct": "增速",
       "count": "数量", "total": "合计", "aov": "客单价", "ltv": "LTV", "cac": "CAC",
       "conversion": "转化率", "retention": "留存率", "uplift": "提升", "lift": "Lift",
       "roi": "ROI", "cost": "成本", "price": "价格", "sample": "样本量", "n": "样本量"}

# 执行元数据：一律不进首页指标带（REPORT-STANDARD §八 R1）
META_KEYS = {
    "ok", "checks", "skill", "action", "type", "runtime_ms", "verdict", "status",
    "error", "note", "notes", "score", "grade", "gate_ok", "passed_gates",
    "report_html", "report_md", "figures_count", "sections_count", "slug",
    "task_id", "generated_at", "ts", "path", "out_dir", "provenance",
    "advice_authorized", "caveats", "contract_warnings", "raw", "next",
}

# 业务量优先展示（命中即前置，其余按 result 原顺序）
BUSINESS_PRIORITY = ("tam", "sam", "som", "tam_top", "tam_bottom", "variance",
                     "cr3", "cr5", "hhi", "roi", "revenue", "profit", "margin_pct",
                     "margin", "growth_pct", "growth", "lift", "uplift",
                     "conversion", "retention", "ltv", "cac", "aov", "count", "total")

PCT_HINTS = ("pct", "rate", "share", "ratio", "lift", "growth_gap")


def _fmt_metric(key: str, v: Any) -> Optional[str]:
    """把一个标量格式化成指标值；不像业务数字/短语的返回 None（不硬凑）。"""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        if any(h in key for h in PCT_HINTS) and abs(float(v)) <= 100:
            return f"{float(v):+.2f}%"
        if abs(float(v)) >= 1000:
            return f"{float(v):,.0f}" if float(v).is_integer() else f"{float(v):,.2f}"
        return f"{int(v)}" if float(v).is_integer() else f"{float(v):.2f}"
    if isinstance(v, str):
        s = v.strip()
        if s and len(s) <= 24 and "\n" not in s:
            return s
    return None


def _business_strip(result: Dict[str, Any],
                    dataset: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """首页指标带：只放业务结论（REPORT-STANDARD §八 R1）。

    取值顺序：result 里的业务标量（按 BUSINESS_PRIORITY 前置）→ 观测集区间变化
    → 结论摘录。**门禁/观测数/保留率等执行元数据一律不入选**；同值只留一次，
    派生键（x_top / x_bottom）在有基键时不重复占位。
    """
    keys = [k for k in result
            if k not in META_KEYS and not str(k).startswith("_") and k != "ok"]
    keys = [k for k in keys
            if not (str(k).endswith(("_top", "_bottom"))
                    and str(k).rsplit("_", 1)[0] in result)]
    keys.sort(key=lambda k: (BUSINESS_PRIORITY.index(k)
                             if k in BUSINESS_PRIORITY else len(BUSINESS_PRIORITY),
                             list(result).index(k)))
    strip: List[Dict[str, Any]] = []
    seen = set()
    for k in keys:
        val = _fmt_metric(str(k), result.get(k))
        if val is None or val in seen:
            continue
        seen.add(val)
        strip.append({"label": _cn(k), "value": val, "note": f"字段 {k}",
                      "status": "accent" if not strip else "none"})
        if len(strip) >= 5:
            break
    if strip:
        return strip

    # 无业务标量：用观测集自身的区间变化（仍是业务口径，不是执行元数据）
    head = _dataset_headline(dataset)
    if head:
        return [{"label": "区间变化", "value": head.split("；")[-1][:20],
                 "note": head[:60], "status": "accent"}]
    return [{"label": "结论", "value": _conclusion(result)[:20],
             "note": "本次执行结论摘录", "status": "none"}]



def _cn(k: str) -> str:
    return _CN.get(str(k), str(k))


def _table_from_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """把 result 里第一个 list[dict] 摊成表；没有则用标量做键值表。"""
    for k, v in result.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            cols = list(v[0].keys())[:6]
            rows = [[("是" if r.get(c) is True else "否" if r.get(c) is False else str(r.get(c, "")))[:40]
                     for c in cols] for r in v[:20]]
            return {"caption": _cn(k), "columns": [_cn(c) for c in cols], "rows": rows}
    kv = [[_cn(k), (str(v)[:60] if not isinstance(v, (dict, list)) else
                    (f"{type(v).__name__}（{len(v)} 项）" if isinstance(v, list) else "嵌套对象"))]
          for k, v in result.items() if k not in ("ok", "conclusion")]
    if kv:
        return {"caption": "执行结果字段", "columns": ["字段", "值"], "rows": kv[:12]}
    return {"caption": "执行结果字段", "columns": ["字段", "值"], "rows": [["—", "本次无结构化输出"]]}


def _result_narrative(result: Dict[str, Any]) -> str:
    return ("以下字段是本次判定的直接依据：逐项明细见表，未列出的字段视为未观测，不作推断；"
            "取值按原始记录，未插值、未平滑，可据表复算。")


def _metrics_table(dataset: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], set[str]]:
    by_item: Dict[str, List[float]] = {}
    for r in dataset:
        try:
            by_item.setdefault(str(r["item"]), []).append(float(r["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    rows, used = [], set()
    for item in sorted(by_item):
        vals = by_item[item]
        first, last = vals[0], vals[-1]
        mean = sum(vals) / len(vals)
        rows.append([item, _num(first), _num(last),
                     f"{(last / first - 1) * 100:+.2f}%" if first else "—",
                     _num(min(vals)), _num(max(vals)), _num(mean), str(len(vals))])
        used.add(item)
    table = {"caption": "指标汇总（由观测集计算）",
             "columns": ["品类", "首值", "末值", "变化", "最小", "最大", "均值", "样本"],
             "rows": rows}
    return table, used


def _record_table(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for r in dataset[:MAX_RECORD_ROWS]:
        rows.append([str(r.get("date", "")), str(r.get("item", "")),
                     _num(float(r.get("value", 0))), str(r.get("unit", "")),
                     str(r.get("source", ""))])
    note = "" if len(dataset) <= MAX_RECORD_ROWS else f"（仅示前 {MAX_RECORD_ROWS} 行，全量见 store）"
    return {"caption": f"全量观测{note}",
            "columns": ["日期", "品类", "数值", "单位", "来源"],
            "rows": rows}


def _dataset_headline(dataset) -> str:
    if not dataset:
        return ""
    by_item = {}
    for r in dataset:
        try:
            by_item.setdefault(str(r["item"]), []).append(float(r["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    movers = []
    for item, vals in by_item.items():
        if len(vals) >= 2 and vals[0]:
            movers.append((item, (vals[-1] / vals[0] - 1) * 100))
    if not movers:
        return ""
    movers.sort(key=lambda x: -abs(x[1]))
    up = [m for m in movers if m[1] > 0]
    down = [m for m in movers if m[1] < 0]
    parts = []
    if up:
        parts.append("涨幅最大 " + "、".join(f"{m[0]} {m[1]:+.2f}%" for m in up[:2]))
    if down:
        parts.append("跌幅最大 " + "、".join(f"{m[0]} {m[1]:+.2f}%" for m in down[:2]))
    return (f"本次覆盖 {len(by_item)} 个品类、{len(dataset)} 条观测；" + "；".join(parts) + "。")


def _conclusion(result: Dict[str, Any]) -> str:
    enums = {"PASS", "FAIL", "ok", "OK", "true", "false", "True", "False"}
    for k in ("conclusion", "summary", "finding", "verdict"):
        v = result.get(k)
        if isinstance(v, str) and len(v.strip()) > 8 and v.strip() not in enums:
            return v.strip()
    checks = [c for c in (result.get("checks") or []) if isinstance(c, dict)]
    # 结论先行：先念业务数字，再补门禁（门禁是过程，不是结论）
    biz: List[str] = []
    seen = set()
    for k in result:
        if k in META_KEYS or k == "ok":
            continue
        if str(k).endswith(("_top", "_bottom")) and str(k).rsplit("_", 1)[0] in result:
            continue
        val = _fmt_metric(str(k), result.get(k))
        if val is None or val in seen:
            continue
        seen.add(val)
        biz.append(f"{_cn(k)} {val}")
        if len(biz) >= 3:
            break
    if checks:
        passed = sum(1 for c in checks if c.get("ok"))
        tail = f"（门禁 {passed}/{len(checks)} 项通过）" if biz else ""
        if biz:
            return (f"本次测算：{'、'.join(biz)}{tail}；"
                    "结论仅对本次输入与口径成立。")
        first = (checks[0].get("msg") or checks[0].get("dim") or "")[:40]
        return (f"本次执行完成：门禁 {passed}/{len(checks)} 项通过；"
                f"首要证据：{first}。结论仅对本次输入与口径成立。")
    if "ok" in result:
        return (f"本次执行{'成功' if result.get('ok') else '未通过'}；"
                "结果字段与证据见分析层与记录层，口径与边界见末尾。")
    return "本次执行完成，详见分析层与记录层；未列出的字段视为本次未观测。"


def _run_adapter(role: str, spec: Dict[str, Any], result: Dict[str, Any], skill: str,
                 action: str, intent: str, data: Optional[Dict[str, Any]] = None):
    """调用角色目录下的 report_contract.py（adapter 唯一入口）。"""
    name = spec.get("adapter")
    if not name:
        return None
    import importlib.util
    role_dir = next((p for p in (Path(__file__).resolve().parent.parent.parent).glob(f"{role}-*")), None)
    if role_dir is None:
        return None
    f = role_dir / "report_contract.py"
    if not f.exists():
        return None
    mod_spec = importlib.util.spec_from_file_location(f"adapter_{role}", f)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    fn = getattr(mod, f"{name}_contract", None)
    if fn is None:
        return None
    for call in (
        lambda: fn(result, skill, action, intent, data),
        lambda: fn(result, skill, action, intent),
        lambda: fn(result, skill, action, intent, spec.get("doc_type", "角色报告")),
    ):
        try:
            got = call()
            if got:
                return got
        except TypeError:
            continue
        except Exception:
            return None
    return None


def _merge_fidelity(contract: Dict[str, Any], fid: Dict[str, Any], spec: Dict[str, Any],
                    dataset: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    sections = contract.setdefault("sections", [])
    for s in sections:
        if s.get("title") in ("记录层", "附录", "全量观测"):
            s["appendix"] = True
    if dataset and not any("记录层" in s.get("title", "") for s in sections):
        sections.append({"index": len(sections) + 1, "title": "记录层",
                         "question": "观测明细与口径是否可复核？",
                         "table": _record_table(dataset),
                         "reading": [{"text": _method_note()}], "appendix": True})
    sections.append(_fidelity_section(fid, spec, len(sections) + 1))
    return normalize_tables(contract)


def _fidelity_section(fid: Dict[str, Any], spec: Dict[str, Any], index: int) -> Dict[str, Any]:
    """报告最后一节：把所有自检分数集中放这里，首页不再出现。"""
    def _pct(v, nd=1):
        return f"{v * 100:.{nd}f}%" if v is not None else "N/A"

    rows = [
        ["观测数", f'{fid.get("obs_total", 0):,}', "本报告覆盖的观测条数"],
        ["保留率", _pct(fid.get("retention")), "报告中出现的观测占全部观测的比例"],
        ["溯源率", f'{_pct(fid.get("trace"), 0)}' if fid.get("trace") is not None else "N/A",
         "有观测锚点的结论占比"],
        ["弃置率", _pct(fid.get("discard")), "采集到但未进任何章节的观测比例"],
        ["规格", spec["extends"], f'{spec["role"]} · tier {spec["tier"]}'],
    ]
    return {
        "index": index,
        "title": "口径与分数",
        "question": "这份报告的数据够不够、每个数字回不回得去？",
        "table": {"caption": "自检分数", "columns": ["指标", "值", "说明"], "rows": rows},
        "reading": [
            {"text": "这几个数是报告的自检结果，放在最后：数据够不够、每个数字回不回得去。"},
            {"text": "分数由观测集与结论锚点计算，不做估算填充；若正文与分数冲突，以正文的观测明细为准。"},
        ],
    }


def _cell_text(c: Any) -> str:
    if isinstance(c, dict):
        return str(c.get("text", ""))
    return str(c)


def _num_or_none(s: Any):
    t = str(s).replace(",", "").replace("%", "").replace("+", "").replace("−", "-").strip()
    try:
        return float(t)
    except ValueError:
        return None


def _auto_chart(table: Any, title: str) -> Optional[Dict[str, Any]]:
    """表里有可解析的数值列时，自动配一张横向条形图；否则不画。"""
    if not table or len(table.get("rows", [])) < 3:
        return None
    cols = [_cell_text(c) for c in table.get("columns", [])]
    rows = table.get("rows", [])
    priority = ("变化", "同比", "环比", "占比", "金额", "数量", "增量", "得分", "效率")
    order = [i for i in range(1, min(len(cols), 5))
             if any(k in cols[i] for k in priority)] + \
            [i for i in range(1, min(len(cols), 5))
             if not any(k in cols[i] for k in priority)]
    best, best_hits = None, 0
    for ci in order:
        hits = sum(1 for r in rows if ci < len(r) and _num_or_none(_cell_text(r[ci])) is not None)
        if hits >= max(2, int(len(rows) * 0.6)):
            best, best_hits = ci, hits
            break
    if best is None or best_hits < max(2, int(len(rows) * 0.6)):
        return None
    bars = []
    for r in rows[:8]:
        if best >= len(r):
            continue
        v = _num_or_none(_cell_text(r[best]))
        if v is None:
            continue
        bars.append({"label": _cell_text(r[0])[:16], "value": v,
                     "value_label": _cell_text(r[best]), "weight": "context"})
    if len(bars) < 2:
        return None
    max(bars, key=lambda b: abs(b["value"]))["weight"] = "reference"
    unit = "单位：%" if ("%" in cols[best] or any("%" in b["value_label"] for b in bars)) else "单位：见表"
    return {"type": "hbar", "title": f"{cols[best]}对比",
            "unit_meta": unit, "source": "来源：本节证据表", "bars": bars}


_Q = {
    "summary": "这单结论是什么，依据是哪几条？",
    "analysis": "数据支持什么判断，变动最大的是谁？",
    "detail": "逐项明细里，哪几项决定了结论？",
    "boundary": "哪些结论不能推断，缺口在哪？",
    "record": "原始观测长什么样，能不能重建？",
    "evidence": "证据链闭合了吗？",
    "gates": "门禁过了哪几项，没过的为什么？",
    "checks": "门禁过了哪几项，没过的为什么？",
    "options": "备选方案怎么取舍？",
    "items": "交付项有哪些，验收标准是什么？",
    "spec": "规格与验收标准是什么？",
}


def build_contract(role: str, name: str, title: str, result: Dict[str, Any],
                   spec: Dict[str, Any], skill: str = "", action: str = "",
                   intent: str = "", dataset: Optional[List[Dict[str, Any]]] = None,
                   claims: Optional[List[Dict[str, Any]]] = None,
                   data: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    claims = claims or []
    dataset = dataset or []

    # 通用写作层：任何角色只要交出一份证据包（claims + sections），就走报告写作器，
    # 不需要为本角色写 adapter。写作器缺配置/缺证据时返回 None，继续走下面的通用映射。
    if isinstance(data, dict) and data.get("claims"):
        try:
            from shared.report_writer import build as _writer_build
            got = _writer_build(role, data, result, intent)
            if got:
                used_items = {str(r.get("item")) for r in dataset} if dataset else set()
                fid0 = compute_fidelity(dataset, used_items, claims)
                return _merge_fidelity(got, fid0, spec, dataset), fid0
        except Exception:  # noqa: BLE001  写作层失败不阻断，回落到通用映射
            pass

    if spec.get("adapter"):
        base = _run_adapter(role, spec, result, skill, action, intent, data)
        if base:
            used_items = {str(r.get("item")) for r in dataset} if dataset else set()
            fid0 = compute_fidelity(dataset, used_items, claims)
            return _merge_fidelity(base, fid0, spec, dataset), fid0

    analysis_tbl, used = _metrics_table(dataset) if dataset else (None, set())
    fid = compute_fidelity(dataset, used, claims)

    sections: List[Dict[str, Any]] = []
    idx = 0
    for sec in spec["sections"]:
        if sec.get("enabled") is False:
            continue
        idx += 1
        sid = sec["id"]
        out: Dict[str, Any] = {"index": idx, "title": sec["title"],
                               "question": _Q.get(sid, f"{sec['title']}的关键结论是什么？")}
        if sid == "summary":
            _keys = [k for k in result.keys() if k not in ("ok", "checks")][:8]
            headline = _dataset_headline(dataset)
            concl = _conclusion(result)
            # 有数据结论时，不再把"门禁 N/N 通过"当结论重复一遍
            keep_concl = bool(concl) and not (headline and concl.startswith("本次执行完成"))
            out["reading"] = ([{"strong": "数据结论：", "text": headline}] if headline else []) + [
                {"text": "本次覆盖字段：" + ("、".join(_cn(k) for k in _keys) if _keys else "无") +
                         f"（共 {len(result)} 项）；口径与边界见文末。"},
                {"text": _method_note()},
            ]
        elif sid in ("analysis", "detail", "options", "items", "spec"):
            if analysis_tbl:
                out["table"] = analysis_tbl
                out["reading"] = [{"text": _analysis_narrative(dataset)}]
            else:
                tbl = _table_from_result(result)
                if tbl:
                    out["table"] = tbl
                kv = [f"{_cn(k)}：{v}" for k, v in result.items()
                      if not isinstance(v, (dict, list)) and k not in ("ok", "conclusion")]
                reading = [{"text": s} for s in kv[:6]]
                reading.append({"text": _result_narrative(result)})
                if sid == "options":
                    reading.append({"text": "取舍依据：成本、影响面、可逆性三项中至少两项需可量化，"
                                            "否则应降级为假设并列入边界；量化项须写明阈值与来源。"})
                    reading.append({"text": "若本次未提供备选方案，本节只呈现已选方案及其依据；"
                                            "备选对比需在上游任务补齐，缺口已记入边界层。"})
                out["reading"] = reading
            if sid in ("analysis", "detail") and out.get("table"):
                ch = _auto_chart(out["table"], sec["title"])
                if ch:
                    out["chart"] = ch
        elif sid in ("record", "evidence", "gates", "checks"):
            out["appendix"] = True
            if dataset:
                out["table"] = _record_table(dataset)
                out["reading"] = [{"text": _method_note()}]
            else:
                checks = result.get("checks") or []
                rows = [[str(c.get("dim", "")), "PASS" if c.get("ok") else "FAIL",
                         str(c.get("msg", ""))[:60]] for c in checks if isinstance(c, dict)]
                out["table"] = {"caption": "门禁记录", "columns": ["维度", "结果", "说明"],
                                "rows": rows or [["—", "—", "无门禁输出"]]}
        else:  # boundary
            notes = result.get("notes") or result.get("gaps") or []
            reading = [{"text": str(n)} for n in notes[:6]]
            reading.append({"text": _boundary_note()})
            out["reading"] = reading
        sections.append(out)

    # 排布：业务章节 → 边界 → 附录（折叠）→ 口径与分数
    normal = [s for s in sections if not s.get("appendix")]
    apps = [s for s in sections if s.get("appendix")]
    sections[:] = normal + apps
    for i, s in enumerate(normal, 1):
        s["index"] = i
    for k, s in enumerate(apps, 1):
        s["index"] = f"A{k}"
    sections.append(_fidelity_section(fid, spec, len(normal) + 1))

    # 首页指标带只放业务信息：不进门禁/观测/规格（REPORT-STANDARD §八 R1）
    strip = _business_strip(result, dataset)

    concl = _conclusion(result)
    headline0 = _dataset_headline(dataset)
    stand = (headline0 or concl).strip()
    if len(stand) > 150:
        stand = stand[:148] + "……"
    title_lines = [title if not spec.get("title_prefix")
                   else (title if str(title).startswith(spec["title_prefix"])
                         else f'{spec["title_prefix"]}：{title}')]
    sub = str(intent or "").strip()
    if sub and sub.lower() not in ("none", "-"):
        title_lines.append(sub)

    contract = {
        "doc_type": f'{spec["doc_type"]} · {name}',
        "title_lines": title_lines,
        "standfirst": stand,
        "metric_strip": strip,
        "meta": [f"角色 {spec['role']}（{name}）", f"规格 {spec['extends']} · tier {spec['tier']}"],
        "summary": [
            {"label": "结论", "text": concl},
        ],
        "sections": sections,
        "notes": {"summary": "口径、来源与证据边界",
                  "items": [{"label": "规格：", "text": f'{spec["extends"]}（{spec["role"]}）'},
                            {"label": "内核：", "text": "core/report_kernel · 确定性渲染"},
                            {"label": "边界：", "text": "结论仅对本报告列出的观测与执行结果成立。"}]},
        "footer": [f'{spec["role"]} · {title}', "core/report_kernel + report_renderer"],
    }
    return normalize_tables(contract), fid


def normalize_tables(contract: Dict[str, Any]) -> Dict[str, Any]:
    """把表头/单元格从字符串规范成 [{"text": ...}]，适配渲染器。"""
    for s in contract.get("sections", []):
        tb = s.get("table")
        if not tb:
            continue
        cols = tb.get("columns") or []
        if cols and isinstance(cols[0], str):
            tb["columns"] = [{"text": str(c)} for c in cols]
        rows = tb.get("rows") or []
        if rows and rows[0] and isinstance(rows[0][0], str):
            tb["rows"] = [[{"text": str(c)} for c in r] for r in rows]
    return contract


def spec_compliance(contract: Dict[str, Any], spec: Dict[str, Any]) -> List[str]:
    """按 spec 检查 contract 是否达标（P1/P2 闸门用）。"""
    errs: List[str] = []
    have = {s["title"] for s in contract.get("sections", [])}
    for sec in spec["sections"]:
        if sec.get("enabled") is False:
            continue
        if sec["title"] not in have:
            errs.append(f"缺 section: {sec['title']}")
            continue
        got = next(s for s in contract["sections"] if s["title"] == sec["title"])
        chars = sum(len(r.get("text", "")) for r in got.get("reading", []))
        if chars < sec.get("min_chars", 0):
            errs.append(f"{sec['title']} 字数不足 {chars}/{sec.get('min_chars')}")
        if sec.get("min_tables", 0) and "table" not in got:
            errs.append(f"{sec['title']} 缺表格")
    return errs


# 公开别名：structure.py 复用同一份实现，避免第二份表格/分数节写法
fidelity_section = _fidelity_section
record_table = _record_table


def contract_hash(contract: Dict[str, Any]) -> str:
    payload = json.dumps(contract, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
