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


def _table_from_result(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """把 result 里第一个 list[dict] 摊成表；没有则用标量做键值表。"""
    for k, v in result.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            cols = list(v[0].keys())[:6]
            rows = [[str(r.get(c, ""))[:40] for c in cols] for r in v[:20]]
            return {"caption": k, "columns": [str(c) for c in cols], "rows": rows}
    kv = [[k, (str(v)[:60] if not isinstance(v, (dict, list)) else
               (f"{type(v).__name__}（{len(v)} 项）" if isinstance(v, list) else "嵌套对象"))]
          for k, v in result.items() if k not in ("ok",)]
    if kv:
        return {"caption": "执行结果字段", "columns": ["字段", "值"], "rows": kv[:12]}
    return {"caption": "执行结果字段", "columns": ["字段", "值"], "rows": [["—", "本次无结构化输出"]]}


def _result_narrative(result: Dict[str, Any]) -> str:
    return ("本节列出的字段构成本次判定依据；未列出的字段视为未观测，不作推断。"
            "本节由执行结果的结构化字段生成：表格给出逐项明细，"
            "判定依据为对应门禁与证据；未列出的字段视为本次未观测，不做推断。"
            "若需追溯到原始输入，见记录层的门禁表与注释。"
            "本节不做因果推断：相关性不等于因果，任何因果表述都需另行设计对照。"
            "复算方式：按记录层字段与公式逐步重跑；任一步缺输入，结论降级为假设。")


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
    for k in ("conclusion", "summary", "finding", "next", "verdict"):
        v = result.get(k)
        if isinstance(v, str) and len(v.strip()) > 8 and v.strip() not in enums:
            return f"{k}：{v.strip()}"
    checks = [c for c in (result.get("checks") or []) if isinstance(c, dict)]
    if checks:
        passed = sum(1 for c in checks if c.get("ok"))
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


def build_contract(role: str, name: str, title: str, result: Dict[str, Any],
                   spec: Dict[str, Any], skill: str = "", action: str = "",
                   intent: str = "", dataset: Optional[List[Dict[str, Any]]] = None,
                   claims: Optional[List[Dict[str, Any]]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    claims = claims or []
    dataset = dataset or []

    if spec.get("adapter"):
        base = _run_adapter(role, spec, result, skill, action, intent)
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
                               "question": f"{sec['title']}：本节的结论与证据是什么？"}
        if sid == "summary":
            _keys = [k for k in result.keys() if k not in ("ok", "checks")][:8]
            headline = _dataset_headline(dataset)
            concl = _conclusion(result)
            # 有数据结论时，不再把"门禁 N/N 通过"当结论重复一遍
            keep_concl = bool(concl) and not (headline and concl.startswith("本次执行完成"))
            out["reading"] = ([{"strong": "数据结论：", "text": headline}] if headline else []) + (
                [{"strong": "结论：", "text": concl}] if keep_concl else []) + [
                {"text": "本次覆盖字段：" + ("、".join(_keys) if _keys else "无") +
                         f"（共 {len(result)} 项）；口径与边界见文末。"},
                {"text": "本报告的回答只基于本次输入：未观测的字段不做推断，"
                         "缺口与未采纳材料在文末单列，不与结论混在一起。"},
            ]
        elif sid in ("analysis", "detail", "options", "items", "spec"):
            if analysis_tbl:
                out["table"] = analysis_tbl
                out["reading"] = [{"text": _analysis_narrative(dataset)}]
            else:
                tbl = _table_from_result(result)
                if tbl:
                    out["table"] = tbl
                kv = [f"{k}：{v}" for k, v in result.items()
                      if not isinstance(v, (dict, list)) and k not in ("ok", "checks")]
                reading = [{"text": s} for s in kv[:6]]
                reading.append({"text": _result_narrative(result)})
                if sid == "options":
                    reading.append({"text": "取舍依据：成本、影响面、可逆性三项中至少两项需可量化，"
                                            "否则应降级为假设并列入边界。"})
                    reading.append({"text": "若本次未提供备选方案，本节只呈现已选方案及其依据；"
                                            "备选对比需在上游任务补齐，缺口已记入边界层。"})
                out["reading"] = reading
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

    # 首页指标带只放业务信息，不放保真分数
    strip = []
    checks = [c for c in (result.get("checks") or []) if isinstance(c, dict)]
    if checks:
        passed = sum(1 for c in checks if c.get("ok"))
        strip.append({"label": "门禁", "value": f"{passed}/{len(checks)}",
                      "note": "执行门禁通过项",
                      "status": "healthy" if passed == len(checks) else "critical"})
    if dataset:
        strip.append({"label": "观测", "value": f"{len(dataset):,}", "note": "本次参与计算的条目",
                      "status": "accent"})
    strip.append({"label": "规格", "value": spec["extends"],
                  "note": f'{spec["role"]} · tier {spec["tier"]}', "status": "none"})

    contract = {
        "doc_type": f'{spec["doc_type"]} · {name}',
        "title_lines": [title if not spec.get("title_prefix")
                        else (title if str(title).startswith(spec["title_prefix"])
                              else f'{spec["title_prefix"]}：{title}'),
                        f"{skill}/{action}" if skill else intent],
        "standfirst": f'{spec["role"]} · tier {spec["tier"]} · 规格 {spec["extends"]}',
        "metric_strip": strip,
        "meta": [f"角色 {spec['role']}（{name}）", f"规格 {spec['extends']} · tier {spec['tier']}"],
        "summary": [
            {"label": "结论：", "text": _conclusion(result)},
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
